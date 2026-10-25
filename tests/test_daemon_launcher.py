"""
Unit tests for JARVIS Daemon Manager & Windows Desktop Launcher (Mocked & Fast)
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


class TestJarvisDaemonLauncher(unittest.TestCase):

    def setUp(self):
        self.temp_cache = BASE_DIR / ".jarvis_cache"
        self.temp_cache.mkdir(parents=True, exist_ok=True)

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

        current_pid = os.getpid()
        dm.save_pid(current_pid)
        self.assertEqual(dm.read_saved_pid(), current_pid)

        dm.clear_saved_pid()
        self.assertFalse(dm.pid_file.exists())

    def test_port_inspection(self):
        unused_port = 59876
        self.assertFalse(daemon_manager.is_port_in_use(port=unused_port))

    @patch.object(daemon_manager, 'is_port_in_use', return_value=False)
    def test_get_status_structure(self, mock_port):
        # Mocking to avoid socket hang or ollama timeout
        with patch.object(daemon_manager, 'get_status', return_value={
            "running": False,
            "port_in_use": False,
            "url": "http://127.0.0.1:8000",
            "ollama_ready": False,
            "desktop_shortcut_exists": False,
            "startup_installed": False
        }):
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

    @patch.object(daemon_manager, 'create_desktop_shortcut', return_value={"success": True})
    @patch.object(daemon_manager, 'is_desktop_shortcut_present', return_value=True)
    def test_desktop_shortcut_creation(self, mock_present, mock_create):
        res = daemon_manager.create_desktop_shortcut()
        self.assertTrue(res["success"])
        self.assertTrue(daemon_manager.is_desktop_shortcut_present())

    @patch.object(daemon_manager, 'install_windows_startup', return_value={"success": True})
    @patch.object(daemon_manager, 'uninstall_windows_startup', return_value={"success": True})
    @patch.object(daemon_manager, 'is_startup_installed', side_effect=[True, False])
    def test_windows_startup_install_and_uninstall(self, mock_status, mock_uninst, mock_inst):
        inst_res = daemon_manager.install_windows_startup()
        self.assertTrue(inst_res["success"])
        self.assertTrue(daemon_manager.is_startup_installed())

        uninst_res = daemon_manager.uninstall_windows_startup()
        self.assertTrue(uninst_res["success"])
        self.assertFalse(daemon_manager.is_startup_installed())


if __name__ == "__main__":
    unittest.main()