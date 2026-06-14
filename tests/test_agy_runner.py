import subprocess
from unittest.mock import patch
import pytest
from mcp_antigravity.agy_runner import run_agy_command

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

@patch("mcp_antigravity.agy_runner.find_agy_binary")
@patch("mcp_antigravity.agy_runner.subprocess.run")
def test_run_agy_command_error(mock_run, mock_find):
    mock_find.return_value = "/mock/agy"
    mock_run.return_value.returncode = 1
    mock_run.return_value.stderr = "mock error"

    with pytest.raises(RuntimeError, match="(?s)agy exited with code 1.*mock error"):
        run_agy_command(["--print", "test"], 10.0)

@patch("mcp_antigravity.agy_runner.find_agy_binary")
@patch("mcp_antigravity.agy_runner.subprocess.run")
def test_run_agy_command_empty_response(mock_run, mock_find):
    mock_find.return_value = "/mock/agy"
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "   \n"

    with pytest.raises(RuntimeError, match="wrote nothing to stdout"):
        run_agy_command(["--print", "test"], 10.0)

@patch("mcp_antigravity.agy_runner.find_agy_binary")
@patch("mcp_antigravity.agy_runner.subprocess.run")
def test_run_agy_command_reuses_supplied_binary(mock_run, mock_find):
    # When a binary is supplied, run_agy_command must not perform another PATH scan.
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "ok"

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
