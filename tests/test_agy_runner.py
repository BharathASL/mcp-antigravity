import os
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from mcp_antigravity.agy_runner import (
    _render_terminal,
    _run_via_conpty,
    _run_via_pty,
    _run_via_subprocess,
    run_agy_command,
)

# Force the plain-pipe runner so these tests are platform-independent.
_force_subprocess = patch(
    "mcp_antigravity.agy_runner._select_capture", new=lambda: _run_via_subprocess
)


@_force_subprocess
@patch("mcp_antigravity.agy_runner.find_agy_binary")
@patch("mcp_antigravity.agy_runner.subprocess.run")
def test_run_agy_command_success(mock_run, mock_find):
    mock_find.return_value = "/mock/agy"
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "mock output"

    result = run_agy_command(["--print", "test"], 10.0)

    assert result == "mock output"
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    assert args[0] == ["/mock/agy", "--print", "test"]
    # stdin must be DEVNULL so agy never blocks reading the inherited MCP stdio pipe.
    assert kwargs["stdin"] == subprocess.DEVNULL
    assert kwargs["stdout"] == subprocess.PIPE
    assert kwargs["stderr"] == subprocess.PIPE
    assert kwargs["timeout"] == 10.0


@_force_subprocess
@patch("mcp_antigravity.agy_runner.find_agy_binary")
@patch("mcp_antigravity.agy_runner.subprocess.run")
def test_run_agy_command_error(mock_run, mock_find):
    mock_find.return_value = "/mock/agy"
    mock_run.return_value.returncode = 1
    mock_run.return_value.stdout = ""
    mock_run.return_value.stderr = "mock error"

    with pytest.raises(RuntimeError, match="(?s)agy exited with code 1.*mock error"):
        run_agy_command(["--print", "test"], 10.0)


@_force_subprocess
@patch("mcp_antigravity.agy_runner.find_agy_binary")
@patch("mcp_antigravity.agy_runner.subprocess.run")
def test_run_agy_command_empty_response(mock_run, mock_find):
    mock_find.return_value = "/mock/agy"
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "   \n"
    mock_run.return_value.stderr = ""

    with pytest.raises(RuntimeError, match="wrote nothing to stdout"):
        run_agy_command(["--print", "test"], 10.0)


@_force_subprocess
@patch("mcp_antigravity.agy_runner.find_agy_binary")
@patch("mcp_antigravity.agy_runner.subprocess.run")
def test_run_agy_command_reuses_supplied_binary(mock_run, mock_find):
    # When a binary is supplied, run_agy_command must not perform another PATH scan.
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "ok"
    mock_run.return_value.stderr = ""

    result = run_agy_command(["--version"], 10.0, binary="/known/agy")

    assert result == "ok"
    mock_find.assert_not_called()
    args, _ = mock_run.call_args
    assert args[0] == ["/known/agy", "--version"]


@patch("mcp_antigravity.agy_runner.find_agy_binary")
def test_run_agy_command_missing_binary(mock_find):
    mock_find.return_value = None
    with pytest.raises(RuntimeError, match="binary not found"):
        run_agy_command(["--print", "test"], 10.0)


def test_render_terminal_strips_escapes():
    # Terminal capability queries agy emits at startup plus CRLF line endings.
    raw = "\x1b[1t\x1b[c\x1b[?1004h\x1b[?9001hHello\r\nWorld\r\n"
    assert _render_terminal(raw) == "Hello\nWorld"


def test_render_terminal_collapses_spinner():
    # A progress spinner overwrites one line via \r, then \r\x1b[K clears it
    # before the real output (mirrors `agy models`).
    raw = (
        "\r- working...\r\\ working...\r| working..."
        "\r\x1b[KModel A\r\nModel B\r\n"
    )
    assert _render_terminal(raw) == "Model A\nModel B"


@pytest.mark.skipif(sys.platform != "win32", reason="ConPTY path is Windows-only")
@patch("mcp_antigravity.agy_runner._select_capture", new=lambda: _run_via_conpty)
@patch("mcp_antigravity.agy_runner.find_agy_binary", return_value="C:/mock/agy.exe")
def test_run_agy_command_conpty_captures_and_strips(mock_find):
    import winpty

    reads = ["\x1b[?1004hSMOKE", " OK\r\n"]

    fake = MagicMock()
    fake.read.side_effect = lambda *_: reads.pop(0) if reads else _raise_eof()
    fake.isalive.return_value = False
    fake.wait.return_value = 0

    with patch.object(winpty, "PtyProcess") as pty:
        pty.spawn.return_value = fake
        result = run_agy_command(["--print", "hi"], 10.0)

    pty.spawn.assert_called_once()
    assert result == "SMOKE OK"


@pytest.mark.skipif(os.name != "posix", reason="pty path is POSIX-only")
def test_run_via_pty_real_echo():
    # Runs a real command through the pty on POSIX CI runners (Linux/macOS),
    # genuinely exercising the openpty/Popen/select/read loop.
    out, code, _ = _run_via_pty(["/bin/echo", "hello pty"], os.environ.copy(), 10.0)
    assert code == 0
    assert "hello pty" in out


@pytest.mark.skipif(os.name != "posix", reason="pty path is POSIX-only")
def test_run_agy_command_pty_real_dispatch():
    # End-to-end through the public API on POSIX, using /bin/echo as a stand-in
    # binary so the pty capture path is validated without agy installed.
    result = run_agy_command(["pty dispatch works"], 10.0, binary="/bin/echo")
    assert "pty dispatch works" in result


def _raise_eof():
    raise EOFError
