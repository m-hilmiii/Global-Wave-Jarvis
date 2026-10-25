"""
Unit test suite verifying Global Wave & LTX-2 Studio Bridge:
- Decoupled folder resolution (Jarvis / Global Wawe / LTX-2-main)
- Zero-VRAM Evacuation protocol
- LTX-2 status tracking and prompt dispatch
- Shorts ideas fetching
"""

import unittest
from unittest.mock import patch, MagicMock
from core_jarvis.tools.studio_bridge import studio_bridge
from core_jarvis.jarvis_brain import jarvis_brain


class TestStudioBridgeAndVRAMEvacuation(unittest.TestCase):

    def test_studio_paths_resolution(self):
        """Verifies that studio bridge identifies the decoupled workspace directories."""
        paths = studio_bridge.get_studio_paths()
        self.assertIn("jarvis_core_dir", paths)
        self.assertIn("global_wave_dir", paths)
        self.assertIn("ltx_factory_dir", paths)
        self.assertIn("ltx_models_ready", paths)
        self.assertIsInstance(paths["ltx_models_ready"], bool)

    def test_fetch_shorts_ideas(self):
        """Verifies viral Shorts ideas generation with transkript guidance."""
        ideas_data = studio_bridge.fetch_shorts_ideas()
        self.assertIn("ideas", ideas_data)
        self.assertGreaterEqual(len(ideas_data["ideas"]), 3)
        self.assertIn("rag_tip", ideas_data)

    def test_ltx_status_summary_when_idle(self):
        """Verifies status output when no render is in progress."""
        status = studio_bridge.get_ltx_status_summary()
        self.assertIn("boşta", status)
        self.assertFalse(studio_bridge.is_ltx_rendering())

    def test_jarvis_brain_ltx_status_fast_path(self):
        """Verifies that 'ltx durumu' is handled as an instant fast-path."""
        res = jarvis_brain.process_message("Jarvis, video render durumu ne alemde?")
        self.assertEqual(res.get("action_taken"), "ltx_status")
        self.assertIn("LTX-2", res.get("reply", ""))

    @patch("subprocess.Popen")
    def test_trigger_ltx_video_evacuates_vram(self, mock_popen):
        """Verifies that launching LTX-2 triggers VRAM evacuation."""
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.communicate.return_value = ("Success", "")
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        with patch("core_jarvis.tools.model_manager.model_manager.prepare_vram_for_model") as mock_vram:
            res = studio_bridge.trigger_ltx_video("A futuristic cyber city", frames=17)
            self.assertTrue(res.get("success"))
            self.assertIn("LTX-2.5 video üretimi başlatıldı", res.get("message"))
            mock_vram.assert_called_with("__NONE__")


if __name__ == "__main__":
    unittest.main()
