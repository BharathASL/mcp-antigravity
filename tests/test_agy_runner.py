import subprocess
from unittest.mock import patch
import pytest
from mcp_antigravity.agy_runner import run_agy_command, find_agy_binary

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
    assert kwargs["stdin"] is None
    assert kwargs["stdout"] == subprocess.PIPE
    assert kwargs["stderr"] == subprocess.PIPE
    assert kwargs["timeout"] == 10.0

@patch("mcp_antigravity.agy_runner.find_agy_binary")
@patch("mcp_antigravity.agy_runner.subprocess.run")
def test_run_agy_command_error(mock_run, mock_find):
    mock_find.return_value = "/mock/agy"
    mock_run.return_value.returncode = 1
    mock_run.return_value.stderr = "mock error"
    
    with pytest.raises(RuntimeError, match="agy exited with code 1.*mock error"):
        run_agy_command(["--print", "test"], 10.0)
