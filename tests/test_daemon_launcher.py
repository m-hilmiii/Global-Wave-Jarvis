"""
Unit tests for JARVIS Daemon Manager & Windows Desktop Launcher
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core_jarvis.daemon_manager import JarvisDaemonManager, daemon_manager
from fastapi.testclient import TestClient
from web.server import app


class TestJarvisDaemonLauncher(unittest.TestCase):

    def setUp(self):
        self.temp_cache = BASE_DIR / ".jarvis_cache"
        self.temp_cache.mkdir(parents=True, exist_ok=True)
        self.client = TestClient(app)

    def test_daemon_manager_initialization(self):
        dm = JarvisDaemonManager(workspace_root=BASE_DIR)
        self.assertEqual(dm.workspace_root, BASE_DIR)
        self.assertTrue(dm.cache_dir.exists())
        self.assertEqual(dm.pid_file.name, "jarvis_daemon.pid")

    def test_get_python_exe(self):
        py_exe = daemon_manager.get_python_exe(silent=False)
        self.assertTrue(py_exe.lower().endswith("python.exe") or "python" in py_exe.lower())

        pyw_exe = daemon_manager.get_python_exe(silent=True)
        self.assertTrue(pyw_exe.lower().endswith("pythonw.exe") or "python" in pyw_exe.lower())

    def test_get_desktop_and_startup_dirs(self):
        desktop = daemon_manager.get_desktop_dir()
        self.assertTrue(desktop.exists(), f"Desktop dir does not exist: {desktop}")

        startup = daemon_manager.get_windows_startup_dir()
        self.assertTrue(startup.exists(), f"Startup dir does not exist: {startup}")

    def test_pid_persistence(self):
        dm = JarvisDaemonManager(workspace_root=BASE_DIR)
        test_pid = 999999
        dm.save_pid(test_pid)
        self.assertTrue(dm.pid_file.exists())

        # If PID does not exist on system, read_saved_pid returns None safely
        current_pid = os.getpid()
        dm.save_pid(current_pid)
        self.assertEqual(dm.read_saved_pid(), current_pid)

        dm.clear_saved_pid()
        self.assertFalse(dm.pid_file.exists())

    def test_port_inspection(self):
        # Local random unused port check
        unused_port = 59876
        self.assertFalse(daemon_manager.is_port_in_use(port=unused_port))

    def test_get_status_structure(self):
        st = daemon_manager.get_status()
        self.assertIn("running", st)
        self.assertIn("port_in_use", st)
        self.assertIn("url", st)
        self.assertIn("ollama_ready", st)
        self.assertIn("desktop_shortcut_exists", st)
        self.assertIn("startup_installed", st)

    def test_silent_vbs_creation(self):
        vbs_path = daemon_manager.create_silent_vbs()
        self.assertTrue(vbs_path.exists())
        content = vbs_path.read_text(encoding="utf-8")
        self.assertIn("WScript.Shell", content)
        self.assertIn("run_global_wave.py", content)

    def test_desktop_shortcut_creation(self):
        res = daemon_manager.create_desktop_shortcut()
        self.assertTrue(res["success"])
        self.assertTrue(daemon_manager.is_desktop_shortcut_present())

    def test_windows_startup_install_and_uninstall(self):
        # Install
        inst_res = daemon_manager.install_windows_startup()
        self.assertTrue(inst_res["success"])
        self.assertTrue(daemon_manager.is_startup_installed())

        # Uninstall
        uninst_res = daemon_manager.uninstall_windows_startup()
        self.assertTrue(uninst_res["success"])
        self.assertFalse(daemon_manager.is_startup_installed())

    def test_api_daemon_status(self):
        resp = self.client.get("/api/jarvis/daemon/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("daemon", data)

    def test_api_daemon_shortcut(self):
        resp = self.client.post("/api/jarvis/daemon/shortcut")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")

    def test_api_daemon_startup_lifecycle(self):
        # Enable startup
        resp1 = self.client.post("/api/jarvis/daemon/startup", json={"enabled": True})
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp1.json()["status"], "success")

        # Disable startup
        resp2 = self.client.post("/api/jarvis/daemon/startup", json={"enabled": False})
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.json()["status"], "success")


if __name__ == "__main__":
    unittest.main()
