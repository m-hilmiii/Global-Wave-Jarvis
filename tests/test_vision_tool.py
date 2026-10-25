"""
Unit tests for JARVIS Vision & Screen Awareness Tool and Telegram Hotline (Stage 1)
"""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from core_jarvis.tools.vision_tool import VisionTool, vision_tool
from core_jarvis.tools.telegram_tool import TelegramTool
from core_jarvis.orchestrator import JarvisOrchestrator


class TestJarvisVisionAndHotline(unittest.TestCase):

    def setUp(self):
        self.vt = VisionTool(ollama_url="http://127.0.0.1:11434")

    def test_screen_capture_returns_valid_structure(self):
        res = self.vt.capture_screen()
        self.assertTrue(res.get("success"))
        self.assertIn("file_path", res)
        self.assertIn("width", res)
        self.assertIn("height", res)
        self.assertIn("base64", res)
        self.assertGreater(len(res["base64"]), 50)

    @patch("requests.get")
    def test_detect_vision_model(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [{"name": "qwen3:8b"}, {"name": "llava:latest"}]
        }
        mock_get.return_value = mock_resp

        detected = self.vt.detect_vision_model()
        self.assertEqual(detected, "llava:latest")

    @patch.object(vision_tool, "capture_screen")
    def test_analyze_screen_diagnostic_fallback(self, mock_capture):
        mock_capture.return_value = {
            "success": True,
            "width": 1280,
            "height": 720,
            "base64": "dummy_b64",
            "file_path": "/tmp/dummy.jpg"
        }
        res = self.vt.analyze_screen(user_prompt="Hata var mı bak", mode="error_check")
        self.assertTrue(res.get("success"))
        self.assertIn("analysis", res)
        self.assertEqual(res.get("mode"), "error_check")

    def test_orchestrator_routes_vision_intent(self):
        orch = JarvisOrchestrator()
        with patch.object(orch.vision, "inspect_screen", return_value={"analysis": "Ekran temiz efendim."}) as mock_vis:
            res = orch.handle_intent("Jarvis ekranıma bak, kodda hata var mı?")
            self.assertEqual(res["specialist"], "VisionSpecialist")
            self.assertEqual(res["intent"], "inspect_screen")
            self.assertIn("Ekran temiz", res["speak_text"])
            mock_vis.assert_called_once()

    @patch.object(TelegramTool, "is_configured", return_value=True)
    @patch.object(TelegramTool, "get_incoming_messages")
    @patch.object(TelegramTool, "send_message")
    def test_telegram_hotline_turn(self, mock_send, mock_in, mock_conf):
        tt = TelegramTool(token="test_tok", chat_id="12345")
        mock_in.return_value = [{"text": "Video hazır mı?", "message_id": 1}]
        mock_send.return_value = {"success": True}

        def mock_callback(text):
            return {"speak_text": "Video render tamamlandı efendim."}

        turns = tt.process_hotline_turn(orchestrator_callback=mock_callback)
        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0]["input"], "Video hazır mı?")
        self.assertEqual(turns[0]["reply"], "Video render tamamlandı efendim.")
        mock_send.assert_called_once_with("Video render tamamlandı efendim.")


if __name__ == "__main__":
    unittest.main()
