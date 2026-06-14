import asyncio
from unittest.mock import patch

import pytest

from mcp_antigravity.server import agy_health, mcp, parse_timeout


def test_server_lists_all_tools():
    # Regression test: the server must import and register its tools. A previous
    # version decorated the low-level Server with @server.tool(), which does not
    # exist and crashed on import (so any MCP client would hang on startup).
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert names == {"agy_print", "agy_continue", "agy_health"}


@pytest.mark.parametrize(
    "value,expected",
    [
        ("5m", 300.0),
        ("30s", 30.0),
        ("90", 90.0),
        (" 2M ", 120.0),
    ],
)
def test_parse_timeout(value, expected):
    assert parse_timeout(value) == expected


@patch("mcp_antigravity.server.check_auth_files", return_value=(True, ""))
@patch("mcp_antigravity.server.run_agy_command", return_value="agy 1.2.3")
@patch("mcp_antigravity.server.find_agy_binary", return_value="/mock/agy")
def test_agy_health_resolves_binary_once(mock_find, mock_run, mock_auth):
    # agy_health previously resolved the binary twice (once directly, once inside
    # run_agy_command). It should now resolve it exactly once and pass it down.
    result = agy_health()

    assert mock_find.call_count == 1
    mock_run.assert_called_once()
    _, kwargs = mock_run.call_args
    assert kwargs.get("binary") == "/mock/agy"

    assert result["binary_found"] is True
    assert result["agy_path"] == "/mock/agy"
    assert result["version"] == "agy 1.2.3"
    assert result["auth_present"] is True


@patch("mcp_antigravity.server.check_auth_files", return_value=(False, "no auth"))
@patch("mcp_antigravity.server.find_agy_binary", return_value=None)
def test_agy_health_no_binary(mock_find, mock_auth):
    result = agy_health()
    assert result["binary_found"] is False
    assert result["agy_path"] == ""
    assert result["auth_present"] is False
