import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

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

def run_agy_command(
    args: list[str], timeout_s: float, binary: Optional[str] = None
) -> str:
    if binary is None:
        binary = find_agy_binary()
    if not binary:
        raise RuntimeError("Antigravity CLI (agy) binary not found. Please install it and ensure it's in your PATH.")

    cmd = [binary] + args
    env = os.environ.copy()
    
    try:
        result = subprocess.run(
            cmd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_s,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"agy exited with code {result.returncode}\nStderr:\n{result.stderr}")
            
        stdout_str = result.stdout.strip()
        if not stdout_str:
            raise RuntimeError(
                "agy exited successfully but wrote nothing to stdout. Common causes:\n"
                "  - The Antigravity CLI auth token has expired (run `agy` interactively "
                "to log in again).\n"
                "  - The agy version renders its response straight to the terminal instead "
                "of stdout, so it is lost when run non-interactively (known limitation on "
                "some platforms/versions). Run `agy_health` to confirm the binary and auth, "
                "and try upgrading the CLI with `agy update`."
            )
            
        return result.stdout
        
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Command exceeded {timeout_s} seconds timeout")
