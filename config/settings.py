"""
Global Wave - Configuration & Token Manager
Handles API keys, paths, and system discovery without requiring manual code edits.
"""
import os
import json
import shutil
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
TOKENS_FILE = CONFIG_DIR / "tokens.json"
ASSETS_DIR = BASE_DIR / "assets"
OUTPUT_DIR = BASE_DIR / "output"

# Isolated Workspace outside OneDrive to prevent WinError 32 lock
TEMP_WORKSPACE = Path(tempfile.gettempdir()) / "global_wave_workspace"
TEMP_WORKSPACE.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_CONFIG = {
    "pexels_api_key": "gcL9CKTL3CQw8XmOr8gnis0glhcTBvfLmBUX1VsmEN0uks6KZDxysbd0",
    "ollama_host": "http://127.0.0.1:11434",
    "default_model": "qwen3:14b",
    "fast_model": "qwen3:8b",
    "german_model": "mistral-nemo:12b",
    # Optional services for Phase 2 / Phase 3
    "elevenlabs_api_key": "",
    "replicate_api_key": "",
    "supabase_url": "",
    "supabase_key": "",
    "adspower_port": 50325,
    # Video & Render Defaults
    "fps": 30,
    "width": 1080,
    "height": 1920,
    "bgm_volume": 0.15,
    "enable_bgm": True,
    "font_name": "Arial",
}

def get_ffmpeg_bin() -> str:
    """Resolve ffmpeg binary across WinGet, PATH, or system locations."""
    winget_link = Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe"))
    if winget_link.exists():
        return str(winget_link)
    found = shutil.which("ffmpeg")
    if found:
        return found
    return "ffmpeg"

def get_ffprobe_bin() -> str:
    """Resolve ffprobe binary."""
    winget_link = Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffprobe.exe"))
    if winget_link.exists():
        return str(winget_link)
    found = shutil.which("ffprobe")
    if found:
        return found
    return "ffprobe"

def load_settings() -> dict:
    """Load settings from tokens.json or create with defaults."""
    if not TOKENS_FILE.exists():
        save_settings(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            merged.update(data)
            return merged
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_settings(new_settings: dict) -> dict:
    """Save new settings to tokens.json securely."""
    current = load_settings() if TOKENS_FILE.exists() else DEFAULT_CONFIG.copy()
    current.update(new_settings)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2, ensure_ascii=False)
    return current

def is_setup_complete() -> bool:
    """Check if mandatory tokens are configured."""
    settings = load_settings()
    pexels_key = settings.get("pexels_api_key", "").strip()
    return bool(pexels_key)
