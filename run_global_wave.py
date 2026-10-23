"""
Global Wave - Main Launcher
Checks environment, auto-starts Ollama if needed, starts FastAPI server, and launches default browser.
"""
import os
import sys
import time
import urllib.request
import subprocess
import webbrowser
import uvicorn
from pathlib import Path

# Ensure UTF-8 stdout on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import get_ffmpeg_bin, load_settings, is_setup_complete

def ensure_ollama_running():
    """Ensure Ollama local server is responding, auto-launch if not."""
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
        print("[1/4] Ollama Service: Active and Ready")
    except Exception:
        print("[1/4] Ollama Service: Starting in background...")
        try:
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)
            print("      Ollama started successfully!")
        except Exception as e:
            print(f"      Warning: Could not auto-launch Ollama: {e}")

def main():
    print("=" * 60)
    print("   [+] GLOBAL WAVE v3.1 - AUTONOMOUS VIDEO ENGINE HUD")
    print("   $0 Cost Local Architecture | RX 9060 XT 16GB Ready")
    print("=" * 60)
    
    ensure_ollama_running()
    
    ffmpeg_bin = get_ffmpeg_bin()
    print(f"[2/4] FFmpeg Binary: {ffmpeg_bin}")
    
    settings = load_settings()
    configured = is_setup_complete()
    print(f"[3/4] Setup Status: {'Ready' if configured else 'Requires Token Setup via HUD'}")
    
    host = "127.0.0.1"
    port = 7860
    url = f"http://{host}:{port}"
    print(f"[4/4] Starting Web HUD on {url}")
    print("=" * 60)
    
    try:
        webbrowser.open(url)
    except Exception:
        pass
        
    uvicorn.run("web.server:app", host=host, port=port, log_level="info")

if __name__ == "__main__":
    main()
