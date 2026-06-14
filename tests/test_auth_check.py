from unittest.mock import patch, MagicMock
from mcp_antigravity.auth_check import check_auth_files

@patch("mcp_antigravity.auth_check.get_home_dir")
def test_check_auth_files_success(mock_get_home):
    mock_home = MagicMock()
    mock_get_home.return_value = mock_home
    
    mock_agy_dir = MagicMock()
    mock_agy_dir.is_dir.return_value = True
    mock_agy_dir.glob.return_value = [MagicMock()] # Found JSON
    
    mock_gemini_creds = MagicMock()
    mock_gemini_creds.is_file.return_value = True
    
    def side_effect(arg):
        if arg == ".antigravitycli":
            return mock_agy_dir
        if arg == ".gemini":
            mock_gemini_dir = MagicMock()
            mock_gemini_dir.__truediv__.return_value = mock_gemini_creds
            return mock_gemini_dir
        return MagicMock()
        
    mock_home.__truediv__.side_effect = side_effect
    
    ok, err = check_auth_files()
    assert ok is True
    assert err == ""

@patch("mcp_antigravity.auth_check.get_home_dir")
def test_check_auth_files_missing_agy_dir(mock_get_home):
    mock_home = MagicMock()
    mock_get_home.return_value = mock_home
    
    mock_agy_dir = MagicMock()
    mock_agy_dir.is_dir.return_value = False
    
    def side_effect(arg):
        if arg == ".antigravitycli":
            return mock_agy_dir
        return MagicMock()
        
    mock_home.__truediv__.side_effect = side_effect
    
    ok, err = check_auth_files()
    assert ok is False
    assert "not found" in err
