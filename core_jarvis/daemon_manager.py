"""
JARVIS Daemon & Windows Lifecycle Manager
Handles starting, stopping, monitoring, desktop shortcuts, and Windows auto-startup on boot.
Designed for 100% local, silent background execution on Windows 11 with zero external pip dependencies.
"""

import os
import sys
import time
import json
import socket
import subprocess
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional, List

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = WORKSPACE_ROOT / ".jarvis_cache"
PID_FILE = CACHE_DIR / "jarvis_daemon.pid"
PORT = 7860
HOST = "127.0.0.1"


def pid_exists(pid: int) -> bool:
    """Check if process ID is currently running on the system."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def get_process_info(pid: int) -> Optional[Dict[str, Any]]:
    """Gather process name and memory usage via PowerShell."""
    if not pid_exists(pid):
        return None
    try:
        ps_cmd = (
            f"$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue; "
            f"if ($p) {{ [PSCustomObject]@{{ Name = $p.ProcessName; WorkingSet = [math]::Round($p.WorkingSet64 / 1MB, 1); CPU = [math]::Round($p.CPU, 1) }} | ConvertTo-Json -Compress }}"
        )
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=3)
        if res.stdout.strip():
            d = json.loads(res.stdout.strip())
            return {
                "pid": pid,
                "name": d.get("Name", "python"),
                "memory_mb": d.get("WorkingSet", 0.0),
                "cpu_time_s": d.get("CPU", 0.0)
            }
    except Exception:
        pass
    return {"pid": pid, "name": "python", "memory_mb": 0.0}


class JarvisDaemonManager:
    """Manages the background lifecycle, Windows desktop shortcuts, and Windows startup registrations."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or WORKSPACE_ROOT
        self.cache_dir = self.workspace_root / ".jarvis_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.pid_file = self.cache_dir / "jarvis_daemon.pid"

    # -------------------------------------------------------------------------
    # Path & Environment Resolution
    # -------------------------------------------------------------------------
    def get_python_exe(self, silent: bool = False) -> str:
        """Return python.exe or pythonw.exe (windowless)."""
        current_exe = Path(sys.executable)
        if silent:
            pythonw = current_exe.parent / "pythonw.exe"
            if pythonw.exists():
                return str(pythonw)
        return str(current_exe)

    def get_desktop_dir(self) -> Path:
        """Resolve Windows Desktop path (handling OneDrive / Turkish Masaüstü)."""
        user_profile = Path(os.environ.get("USERPROFILE", Path.home()))
        candidates = [
            user_profile / "OneDrive" / "Masaüstü",
            user_profile / "Desktop",
            user_profile / "Masaüstü",
            user_profile / "OneDrive" / "Desktop",
        ]
        for c in candidates:
            if c.exists():
                return c
        return user_profile / "Desktop"

    def get_windows_startup_dir(self) -> Path:
        """Resolve Windows Startup folder (shell:startup)."""
        app_data = os.environ.get("APPDATA")
        if app_data:
            startup_path = Path(app_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            if startup_path.exists():
                return startup_path
        fallback = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback

    # -------------------------------------------------------------------------
    # Process & Port Inspection
    # -------------------------------------------------------------------------
    def is_port_in_use(self, port: int = PORT, host: str = HOST) -> bool:
        """Check if TCP port 7860 is bound and accepting connections."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.6)
            return s.connect_ex((host, port)) == 0

    def is_http_ready(self, port: int = PORT, host: str = HOST, timeout: float = 1.0) -> bool:
        """Check if FastAPI responds with HTTP 200 on /api/config or root."""
        url = f"http://{host}:{port}/api/config"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "JarvisDaemon/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status in (200, 307, 401)
        except Exception:
            return False

    def find_pids_on_port(self, port: int = PORT) -> List[int]:
        """Find any process IDs listening on the specified port using netstat."""
        pids = []
        try:
            res = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, timeout=3)
            for line in res.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.strip().split()
                    if parts:
                        try:
                            pid = int(parts[-1])
                            if pid > 0 and pid not in pids:
                                pids.append(pid)
                        except ValueError:
                            pass
        except Exception:
            pass
        return pids

    def read_saved_pid(self) -> Optional[int]:
        """Read saved PID from .jarvis_cache/jarvis_daemon.pid."""
        if self.pid_file.exists():
            try:
                pid = int(self.pid_file.read_text(encoding="utf-8").strip())
                if pid_exists(pid):
                    return pid
            except Exception:
                pass
        return None

    def save_pid(self, pid: int) -> None:
        """Persist process ID to file."""
        self.pid_file.write_text(str(pid), encoding="utf-8")

    def clear_saved_pid(self) -> None:
        """Remove saved PID file."""
        if self.pid_file.exists():
            try:
                self.pid_file.unlink()
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Lifecycle Operations (Start, Stop, Restart, Status)
    # -------------------------------------------------------------------------
    def get_status(self) -> Dict[str, Any]:
        """Return comprehensive status of the daemon and supporting services."""
        port_alive = self.is_port_in_use()
        http_ready = self.is_http_ready() if port_alive else False
        saved_pid = self.read_saved_pid()
        active_pids = self.find_pids_on_port()

        proc_info = None
        target_pid = saved_pid or (active_pids[0] if active_pids else None)
        if target_pid and pid_exists(target_pid):
            proc_info = get_process_info(target_pid)

        # Check Ollama
        ollama_ready = False
        try:
            with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=0.8) as r:
                ollama_ready = r.status == 200
        except Exception:
            pass

        return {
            "running": bool(port_alive and (http_ready or proc_info)),
            "port_in_use": port_alive,
            "http_ready": http_ready,
            "url": f"http://{HOST}:{PORT}",
            "pid": target_pid,
            "process": proc_info,
            "ollama_ready": ollama_ready,
            "desktop_shortcut_exists": self.is_desktop_shortcut_present(),
            "startup_installed": self.is_startup_installed()
        }

    def start(self, background: bool = True, open_browser: bool = True, wait_seconds: int = 10) -> Dict[str, Any]:
        """Start JARVIS server in background or console mode."""
        st = self.get_status()
        if st["running"]:
            return {
                "success": True,
                "message": "JARVIS zaten çalışıyor efendim.",
                "status": st
            }

        py_exe = self.get_python_exe(silent=background)
        launcher_script = str(self.workspace_root / "run_global_wave.py")

        creation_flags = 0
        if background and sys.platform == "win32":
            # DETACHED_PROCESS + CREATE_NO_WINDOW
            creation_flags = 0x00000008 | 0x08000000

        try:
            kwargs: Dict[str, Any] = {
                "cwd": str(self.workspace_root),
                "creationflags": creation_flags
            }
            if background:
                kwargs["stdout"] = subprocess.DEVNULL
                kwargs["stderr"] = subprocess.DEVNULL
                kwargs["stdin"] = subprocess.DEVNULL

            proc = subprocess.Popen([py_exe, launcher_script], **kwargs)
            self.save_pid(proc.pid)

            # Wait for server to become responsive
            started = False
            for _ in range(wait_seconds * 2):
                time.sleep(0.5)
                if self.is_http_ready():
                    started = True
                    break

            if started and open_browser:
                try:
                    import webbrowser
                    webbrowser.open(f"http://{HOST}:{PORT}")
                except Exception:
                    pass

            return {
                "success": started,
                "pid": proc.pid,
                "background": background,
                "url": f"http://{HOST}:{PORT}",
                "message": "JARVIS başlatıldı ve hazır efendim." if started else "JARVIS işlemi tetiklendi, başlatılıyor..."
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"JARVIS başlatılırken hata oluştu: {e}"
            }

    def stop(self) -> Dict[str, Any]:
        """Gracefully terminate JARVIS background processes using taskkill."""
        stopped_pids = []
        pids_to_kill = set()

        saved_pid = self.read_saved_pid()
        if saved_pid:
            pids_to_kill.add(saved_pid)

        # Also find any other python processes bound to port 7860
        for p in self.find_pids_on_port():
            pids_to_kill.add(p)

        if not pids_to_kill:
            self.clear_saved_pid()
            return {
                "success": True,
                "message": "Çalışan aktif bir JARVIS süreci bulunamadı.",
                "stopped_pids": []
            }

        for pid in pids_to_kill:
            if not pid_exists(pid):
                continue
            try:
                # Forcefully kill process tree
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, timeout=4)
                stopped_pids.append(pid)
            except Exception:
                pass

        self.clear_saved_pid()
        return {
            "success": True,
            "message": f"JARVIS süreci başarıyla sonlandırıldı (PID: {stopped_pids}).",
            "stopped_pids": stopped_pids
        }

    def restart(self, background: bool = True) -> Dict[str, Any]:
        """Stop and restart the JARVIS server."""
        self.stop()
        time.sleep(1.2)
        return self.start(background=background)

    # -------------------------------------------------------------------------
    # Windows Desktop Shortcut & Boot Startup Registration
    # -------------------------------------------------------------------------
    def is_desktop_shortcut_present(self) -> bool:
        """Check if desktop shortcut exists."""
        desktop = self.get_desktop_dir()
        lnk_path = desktop / "JARVIS AI Operating System.lnk"
        return lnk_path.exists()

    def _run_powershell(self, ps_script: str, timeout: int = 8) -> subprocess.CompletedProcess:
        """Run PowerShell script safely using base64 utf-16le encoded command to prevent Unicode corruption."""
        import base64
        b64 = base64.b64encode(ps_script.encode("utf-16le")).decode("ascii")
        return subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", b64],
            capture_output=True,
            timeout=timeout
        )

    def create_desktop_shortcut(self) -> Dict[str, Any]:
        """Create a beautiful Windows Desktop shortcut using PowerShell."""
        desktop = self.get_desktop_dir()
        lnk_path = desktop / "JARVIS AI Operating System.lnk"
        bat_target = self.workspace_root / "start_jarvis.bat"

        ps_script = f"""
        $WshShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut('{str(lnk_path)}')
        $Shortcut.TargetPath = '{str(bat_target)}'
        $Shortcut.WorkingDirectory = '{str(self.workspace_root)}'
        $Shortcut.Description = 'JARVIS AI Operating System - Sayin Hilmi'
        $Shortcut.IconLocation = 'shell32.dll,15'
        $Shortcut.Save()
        """
        try:
            res = self._run_powershell(ps_script)
            created = lnk_path.exists()
            return {
                "success": created,
                "path": str(lnk_path),
                "message": "Masaüstü kısayolu oluşturuldu efendim." if created else f"Kısayol oluşturulamadı: {res.stderr}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def is_startup_installed(self) -> bool:
        """Check if Windows boot startup shortcut exists."""
        startup_dir = self.get_windows_startup_dir()
        lnk_path = startup_dir / "JARVIS_Background_Service.lnk"
        return lnk_path.exists()

    def install_windows_startup(self) -> Dict[str, Any]:
        """Add silent background runner to Windows Startup folder."""
        startup_dir = self.get_windows_startup_dir()
        lnk_path = startup_dir / "JARVIS_Background_Service.lnk"
        vbs_target = self.workspace_root / "start_silent.vbs"

        # Re-generate start_silent.vbs dynamically
        self.create_silent_vbs()

        ps_script = f"""
        $WshShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut('{str(lnk_path)}')
        $Shortcut.TargetPath = 'wscript.exe'
        $Shortcut.Arguments = '"{str(vbs_target)}"'
        $Shortcut.WorkingDirectory = '{str(self.workspace_root)}'
        $Shortcut.Description = 'JARVIS AI OS Silent Background Daemon'
        $Shortcut.Save()
        """
        try:
            res = self._run_powershell(ps_script)
            created = lnk_path.exists()
            return {
                "success": created,
                "path": str(lnk_path),
                "message": "JARVIS Windows açılışına (Startup) başarıyla eklendi efendim." if created else f"Hata: {res.stderr}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def uninstall_windows_startup(self) -> Dict[str, Any]:
        """Remove JARVIS from Windows Startup folder."""
        startup_dir = self.get_windows_startup_dir()
        lnk_path = startup_dir / "JARVIS_Background_Service.lnk"
        if lnk_path.exists():
            try:
                lnk_path.unlink()
                return {"success": True, "message": "JARVIS Windows başlangıcından kaldırıldı."}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": True, "message": "Windows başlangıcında kayıtlı JARVIS bulunamadı."}

    def create_silent_vbs(self) -> Path:
        """Create start_silent.vbs in workspace root for zero-window background execution."""
        vbs_path = self.workspace_root / "start_silent.vbs"
        py_exe = self.get_python_exe(silent=True)

        # Uses pure ASCII and resolves directory dynamically via WScript.ScriptFullName so
        # paths with Turkish characters (e.g. Masaüstü) never cause VBScript encoding crashes.
        content = (
            'Set WshShell = CreateObject("WScript.Shell")\r\n'
            'Set fso = CreateObject("Scripting.FileSystemObject")\r\n'
            'currentDir = fso.GetParentFolderName(WScript.ScriptFullName)\r\n'
            'WshShell.CurrentDirectory = currentDir\r\n'
            f'WshShell.Run """{py_exe}"" """ & currentDir & "\\run_global_wave.py""", 0, False\r\n'
        )
        vbs_path.write_text(content, encoding="ascii")
        return vbs_path


daemon_manager = JarvisDaemonManager()
