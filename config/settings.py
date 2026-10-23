"""
Global Wave - Configuration & Token Manager
Handles API keys, paths, and system discovery without hardcoded credentials.
Strict schema validation, thread-safe writes, and safe boolean parsing.
"""
import os
import json
import shutil
import tempfile
import threading
from urllib.parse import urlparse
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

SETTINGS_LOCK = threading.RLock()

DEFAULT_CONFIG = {
    # Credentials are loaded from tokens.json or environment variables, NEVER hardcoded in source
    "pexels_api_key": os.environ.get("PEXELS_API_KEY", ""),
    "ollama_host": os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"),
    "default_model": "qwen3:14b",
    "fast_model": "qwen3:8b",
    "german_model": "mistral-nemo:12b",
    # Optional services
    "elevenlabs_api_key": os.environ.get("ELEVENLABS_API_KEY", ""),
    "replicate_api_key": os.environ.get("REPLICATE_API_KEY", ""),
    "supabase_url": os.environ.get("SUPABASE_URL", ""),
    "supabase_key": os.environ.get("SUPABASE_KEY", ""),
    "adspower_port": 50325,
    # Video & Render Defaults
    "fps": 30,
    "width": 1080,
    "height": 1920,
    "bgm_volume": 0.15,
    "enable_bgm": True,
    "font_name": "Arial",
    "allow_remote_ollama": False,
    "strict_local": False
}

ALLOWED_SETTING_KEYS = {
    "pexels_api_key",
    "pixabay_api_key",
    "ollama_host",
    "default_model",
    "fast_model",
    "german_model",
    "elevenlabs_api_key",
    "replicate_api_key",
    "supabase_url",
    "supabase_key",
    "adspower_port",
    "fps",
    "width",
    "height",
    "bgm_volume",
    "enable_bgm",
    "font_name",
    "allow_remote_ollama",
    "strict_local"
}

def parse_bool(v) -> bool:
    """Safely parse boolean values without string 'false' evaluating to True."""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        clean = v.strip().lower()
        if clean in ("true", "1", "yes", "on"):
            return True
        if clean in ("false", "0", "no", "off", ""):
            return False
    if isinstance(v, (int, float)):
        return bool(v)
    return False

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

def validate_ollama_host(host_url: str, allow_remote: bool = False) -> str:
    """Validate that ollama_host is safe and restricted to localhost unless remote is explicitly allowed."""
    if not host_url or not isinstance(host_url, str):
        return "http://127.0.0.1:11434"
    clean = host_url.strip().rstrip("/")
    if not (clean.startswith("http://") or clean.startswith("https://")):
        clean = "http://" + clean
    parsed = urlparse(clean)
    hostname = parsed.hostname or ""
    if not allow_remote and hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError(f"Güvenlik kısıtlaması: ollama_host varsayılan olarak yalnızca yerel makineye (127.0.0.1/localhost) yönlendirilebilir. Uzak sunucu ({hostname}) için 'allow_remote_ollama: true' belirtilmelidir.")
    return clean

def load_settings() -> dict:
    """Load settings from tokens.json or create with defaults with strict schema validation."""
    with SETTINGS_LOCK:
        if not TOKENS_FILE.exists():
            save_settings(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
        try:
            with open(TOKENS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                merged = DEFAULT_CONFIG.copy()
                for k, v in data.items():
                    if k not in ALLOWED_SETTING_KEYS:
                        continue
                    if k in ["enable_bgm", "allow_remote_ollama", "strict_local"]:
                        merged[k] = parse_bool(v)
                    elif k in ["fps", "width", "height", "adspower_port"]:
                        try:
                            merged[k] = int(v)
                        except (ValueError, TypeError):
                            pass
                    elif k == "bgm_volume":
                        try:
                            merged[k] = float(v)
                        except (ValueError, TypeError):
                            pass
                    else:
                        merged[k] = v
                return merged
        except Exception:
            return DEFAULT_CONFIG.copy()

def save_settings(new_settings: dict) -> dict:
    """Save new settings to tokens.json with strict schema validation and atomic write."""
    with SETTINGS_LOCK:
        current = load_settings() if TOKENS_FILE.exists() else DEFAULT_CONFIG.copy()
        allow_remote = parse_bool(new_settings.get("allow_remote_ollama", current.get("allow_remote_ollama", False)))

        for k, v in new_settings.items():
            if k not in ALLOWED_SETTING_KEYS:
                continue
            if isinstance(v, str) and ("*" in v or v.startswith("****") or v.endswith("****")):
                continue
                
            if k == "ollama_host":
                current[k] = validate_ollama_host(str(v), allow_remote=allow_remote)
            elif k in ["fps", "width", "height", "adspower_port"]:
                try:
                    val = int(v)
                    if k == "fps" and not (15 <= val <= 60):
                        continue
                    if k in ["width", "height"] and not (240 <= val <= 3840):
                        continue
                    current[k] = val
                except (ValueError, TypeError):
                    continue
            elif k == "bgm_volume":
                try:
                    val = float(v)
                    current[k] = max(0.0, min(1.0, val))
                except (ValueError, TypeError):
                    continue
            elif k in ["enable_bgm", "allow_remote_ollama", "strict_local"]:
                current[k] = parse_bool(v)
            else:
                current[k] = str(v).strip()

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        tmp_file = TOKENS_FILE.with_suffix(".tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, ensure_ascii=False)
        tmp_file.replace(TOKENS_FILE)
        return current

def is_setup_complete() -> bool:
    """Check if mandatory tokens are configured."""
    settings = load_settings()
    pexels_key = settings.get("pexels_api_key", "").strip()
    return bool(pexels_key)
