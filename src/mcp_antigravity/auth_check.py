import os
from pathlib import Path

def get_home_dir() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("USERPROFILE", "~")).expanduser()
    return Path("~").expanduser()

def check_auth_files() -> tuple[bool, str]:
    home = get_home_dir()
    
    agy_dir = home / ".antigravitycli"
    if agy_dir.is_dir():
        json_files = list(agy_dir.glob("*.json"))
        if not json_files:
            return False, f"No JSON auth files found in {agy_dir}"
    else:
        return False, f"Antigravity CLI config directory {agy_dir} not found"
        
    gemini_creds = home / ".gemini" / "oauth_creds.json"
    if not gemini_creds.is_file():
        return False, f"Gemini oauth credentials not found at {gemini_creds}"
        
    return True, ""
