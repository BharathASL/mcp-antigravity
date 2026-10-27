from unittest.mock import patch

from mcp_antigravity.auth_check import check_auth_files


@patch("mcp_antigravity.auth_check.get_home_dir")
def test_new_layout_oauth_token(mock_get_home, tmp_path):
    cli_dir = tmp_path / ".gemini" / "antigravity-cli"
    cli_dir.mkdir(parents=True)
    (cli_dir / "antigravity-oauth-token").write_text('{"token": {}}')
    mock_get_home.return_value = tmp_path

    ok, err = check_auth_files()
    assert ok is True
    assert err == ""


@patch("mcp_antigravity.auth_check.get_home_dir")
def test_legacy_layout(mock_get_home, tmp_path):
    (tmp_path / ".gemini").mkdir()
    (tmp_path / ".antigravitycli").mkdir()
    (tmp_path / ".antigravitycli" / "auth.json").write_text("{}")
    (tmp_path / ".gemini" / "oauth_creds.json").write_text('{"token": {}}')
    mock_get_home.return_value = tmp_path

    ok, err = check_auth_files()
    assert ok is True
    assert err == ""


@patch("mcp_antigravity.auth_check.get_home_dir")
def test_no_auth_at_all(mock_get_home, tmp_path):
    (tmp_path / ".gemini").mkdir()
    mock_get_home.return_value = tmp_path

    ok, _err = check_auth_files()
    assert ok is False
    assert "not found" in _err


@patch("mcp_antigravity.auth_check.get_home_dir")
def test_legacy_agy_dir_without_json(mock_get_home, tmp_path):
    (tmp_path / ".gemini").mkdir()
    (tmp_path / ".antigravitycli").mkdir()
    mock_get_home.return_value = tmp_path

    ok, _err = check_auth_files()
    assert ok is False
