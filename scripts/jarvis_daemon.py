"""
JARVIS Daemon CLI Interface
Usage:
  python scripts/jarvis_daemon.py start [--foreground] [--no-browser]
  python scripts/jarvis_daemon.py stop
  python scripts/jarvis_daemon.py restart
  python scripts/jarvis_daemon.py status
  python scripts/jarvis_daemon.py shortcut
  python scripts/jarvis_daemon.py startup-install
  python scripts/jarvis_daemon.py startup-uninstall
"""

import sys
import argparse
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from core_jarvis.daemon_manager import daemon_manager


def main():
    parser = argparse.ArgumentParser(description="JARVIS AI Operating System - Daemon & Lifecycle Manager")
    parser.add_argument("command", choices=[
        "start", "stop", "restart", "status",
        "shortcut", "startup-install", "startup-uninstall"
    ], help="Operation to perform")
    parser.add_argument("--foreground", action="store_true", help="Run in foreground instead of detached background daemon")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser upon start")

    args = parser.parse_args()

    if args.command == "status":
        st = daemon_manager.get_status()
        print("\n" + "=" * 55)
        print("   JARVIS AI OPERATING SYSTEM - TELEMETRİ & DURUM")
        print("=" * 55)
        print(f" Durum:            {'ÇALIŞIYOR (ONLINE)' if st['running'] else 'KAPALI (OFFLINE)'}")
        print(f" Port (7860):      {'Dinleniyor' if st['port_in_use'] else 'Boşta'}")
        print(f" HTTP Erişimi:     {'Sağlıklı (200 OK)' if st['http_ready'] else 'Yanıt Yok'}")
        print(f" Yerel Adres:      {st['url']}")
        print(f" PID:              {st['pid'] or 'Yok'}")
        if st.get("process"):
            p = st["process"]
            print(f" Süreç Adı:        {p['name']}")
            print(f" CPU Kullanımı:    %{p['cpu_percent']}")
            print(f" Bellek (RAM):     {p['memory_mb']} MB")
        print(f" Ollama Motoru:    {'Hazır' if st['ollama_ready'] else 'Beklemede'}")
        print(f" Masaüstü Kısayol: {'Mevcut' if st['desktop_shortcut_exists'] else 'Yok'}")
        print(f" Windows Açılış:   {'Aktif (Auto-start)' if st['startup_installed'] else 'Pasif'}")
        print("=" * 55 + "\n")

    elif args.command == "start":
        print("[JARVIS] Başlatılıyor...")
        bg = not args.foreground
        res = daemon_manager.start(background=bg, open_browser=not args.no_browser)
        print(res.get("message", res))

    elif args.command == "stop":
        print("[JARVIS] Durduruluyor...")
        res = daemon_manager.stop()
        print(res.get("message", res))

    elif args.command == "restart":
        print("[JARVIS] Yeniden başlatılıyor...")
        res = daemon_manager.restart(background=not args.foreground)
        print(res.get("message", res))

    elif args.command == "shortcut":
        res = daemon_manager.create_desktop_shortcut()
        print(res.get("message", res))

    elif args.command == "startup-install":
        res = daemon_manager.install_windows_startup()
        print(res.get("message", res))

    elif args.command == "startup-uninstall":
        res = daemon_manager.uninstall_windows_startup()
        print(res.get("message", res))


if __name__ == "__main__":
    main()
