import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

# Matches a single ANSI/VT escape sequence (CSI, OSC, or two-byte escape).
_ESC_RE = re.compile(
    r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\))"
)


def _render_terminal(text: str) -> str:
    """Render pseudo-console output to plain text.

    A ConPTY capture contains the raw byte stream a terminal would draw,
    including carriage returns and erase-line sequences used for progress
    spinners. Emulating a single cursor line collapses those overwrites (so a
    spinner becomes its final state) and drops styling/mode escapes.
    """
    lines: list[str] = []
    line: list[str] = []
    cursor = 0
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "\x1b":
            m = _ESC_RE.match(text, i)
            if not m:
                i += 1
                continue
            seq = m.group()
            i = m.end()
            if seq.startswith("\x1b[") and seq.endswith("K"):  # erase in line
                param = seq[2:-1]
                if param in ("", "0"):
                    del line[cursor:]
                elif param == "1":
                    for j in range(min(cursor, len(line))):
                        line[j] = " "
                elif param == "2":
                    line = []
            continue
        if ch == "\r":
            cursor = 0
        elif ch == "\n":
            lines.append("".join(line))
            line, cursor = [], 0
        elif cursor < len(line):
            line[cursor] = ch
            cursor += 1
        else:
            line.append(ch)
            cursor += 1
        i += 1
    if line:
        lines.append("".join(line))
    return "\n".join(lines)


def find_agy_binary() -> Optional[str]:
    if "AGY_BINARY_PATH" in os.environ:
        path = os.environ["AGY_BINARY_PATH"]
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    agy_path = shutil.which("agy")
    if agy_path:
        return agy_path

    if os.name == "nt":
        localappdata = os.environ.get("LOCALAPPDATA", "")
        if localappdata:
            fallback = Path(localappdata) / "agy" / "bin" / "agy.exe"
            if fallback.is_file():
                return str(fallback)
    else:
        home = Path("~").expanduser()
        fallback = home / ".agy" / "bin" / "agy"
        if fallback.is_file():
            return str(fallback)

    return None


def _run_via_subprocess(
    cmd: list[str], env: dict, timeout_s: float
) -> tuple[str, int, str]:
    try:
        result = subprocess.run(
            cmd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_s,
            text=True,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Command exceeded {timeout_s} seconds timeout")
    return result.stdout, result.returncode, result.stderr or ""


def _run_via_conpty(
    cmd: list[str], env: dict, timeout_s: float
) -> tuple[str, int, str]:
    from winpty import PtyProcess  # lazy import; Windows-only dependency

    proc = PtyProcess.spawn(cmd, env=env)
    chunks: list[str] = []

    def _drain() -> None:
        while True:
            try:
                data = proc.read(65536)
            except EOFError:
                break
            if data:
                chunks.append(data)
            elif not proc.isalive():
                break

    reader = threading.Thread(target=_drain, daemon=True)
    reader.start()
    reader.join(timeout_s)
    if reader.is_alive():
        try:
            proc.terminate(force=True)
        except Exception:
            pass
        reader.join(2.0)
        raise RuntimeError(f"Command exceeded {timeout_s} seconds timeout")

    try:
        exit_code = proc.wait()
    except Exception:
        exit_code = proc.exitstatus if proc.exitstatus is not None else 0

    output = _render_terminal("".join(chunks))
    # ConPTY merges stdout and stderr, so the captured text doubles as stderr.
    return output, (exit_code or 0), output


def _run_via_pty(
    cmd: list[str], env: dict, timeout_s: float
) -> tuple[str, int, str]:
    # POSIX counterpart of the ConPTY path: agy may render to its controlling
    # terminal rather than stdout, so give it a real pty and capture that.
    import errno
    import pty
    import select

    master, slave = pty.openpty()
    proc = subprocess.Popen(
        cmd, env=env, stdin=slave, stdout=slave, stderr=slave, close_fds=True
    )
    os.close(slave)

    chunks: list[bytes] = []
    deadline = time.monotonic() + timeout_s
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                proc.kill()
                raise RuntimeError(f"Command exceeded {timeout_s} seconds timeout")
            rlist, _, _ = select.select([master], [], [], min(remaining, 0.5))
            if master in rlist:
                try:
                    data = os.read(master, 65536)
                except OSError as exc:
                    if exc.errno == errno.EIO:  # slave closed -> EOF (Linux)
                        break
                    raise
                if not data:  # EOF (macOS/BSD)
                    break
                chunks.append(data)
            elif proc.poll() is not None:
                break
    finally:
        os.close(master)

    returncode = proc.wait()
    output = _render_terminal(b"".join(chunks).decode("utf-8", errors="replace"))
    # A pty merges stdout and stderr, so the captured text doubles as stderr.
    return output, returncode, output


def _select_capture():
    """Pick how to run agy. agy renders to its terminal rather than stdout, so a
    pseudo-terminal is needed to capture output: ConPTY on Windows, a pty on
    POSIX. Anything else falls back to a plain stdout pipe."""
    if sys.platform == "win32":
        return _run_via_conpty
    if os.name == "posix":
        return _run_via_pty
    return _run_via_subprocess


def run_agy_command(
    args: list[str], timeout_s: float, binary: Optional[str] = None
) -> str:
    if binary is None:
        binary = find_agy_binary()
    if not binary:
        raise RuntimeError("Antigravity CLI (agy) binary not found. Please install it and ensure it's in your PATH.")

    cmd = [binary] + args
    env = os.environ.copy()

    stdout, returncode, stderr = _select_capture()(cmd, env, timeout_s)

    if returncode != 0:
        raise RuntimeError(f"agy exited with code {returncode}\nStderr:\n{stderr}")

    if not stdout.strip():
        raise RuntimeError(
            "agy exited successfully but wrote nothing to stdout. Common causes:\n"
            "  - The Antigravity CLI auth token has expired (run `agy` interactively "
            "to log in again).\n"
            "  - The agy version renders its response straight to the terminal instead "
            "of stdout, so it is lost when run non-interactively (known limitation on "
            "some platforms/versions). Run `agy_health` to confirm the binary and auth, "
            "and try upgrading the CLI with `agy update`."
        )

    return stdout
