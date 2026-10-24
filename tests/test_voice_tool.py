"""
Unit Tests for JARVIS Voice Interaction, Wake-Word & Kokoro TTS Engine (Stage 3)
Verifies:
1. Wake-word detection and directive extraction
2. Text cleaning and phonetic normalization for natural speech
3. Local studio neural TTS synthesis via Kokoro-82M ONNX
4. End-to-end voice command processing via Orchestrator
5. Orchestrator intent routing for voice actions
6. FastAPI REST endpoints (/api/jarvis/voice/*)
"""

import os
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from core_jarvis.tools.voice_tool import (
    voice_tool, clean_text_for_speech, JarvisVoiceTool
)
from core_jarvis.orchestrator import orchestrator
from web.server import app, LOCAL_SESSION_TOKEN


class TestJarvisVoiceEngine(unittest.TestCase):

    def setUp(self):
        self.tool = JarvisVoiceTool()

    def test_wake_word_parsing(self):
        samples = [
            ("Hey Jarvis, bugün ne yapmam gerekiyor?", True, "bugün ne yapmam gerekiyor?"),
            ("Jarvis: testleri çalıştır", True, "testleri çalıştır"),
            ("Dinle Jarvis nasılsın?", True, "nasılsın?"),
            ("Tamam Jarvis, video motoru durumuna bak", True, "video motoru durumuna bak"),
            ("Normal bir sohbet cümlesi", False, "Normal bir sohbet cümlesi")
        ]
        for raw, expected_detected, expected_cmd in samples:
            detected, cmd = self.tool.parse_wake_word(raw)
            self.assertEqual(detected, expected_detected, f"Wake word failed for: {raw}")
            self.assertEqual(cmd, expected_cmd, f"Command clean failed for: {raw}")

    def test_text_cleaning_for_speech(self):
        raw = """
        # Sistem Durumu Raporu
        **Sayın Hilmi**, sistem şu anda %100 kararlılıkla çalışıyor! 🚀
        ```python
        def foo():
            pass
        ```
        Ayrıca [GitHub](https://github.com) bağlantısı ve [ENGELLENEN TALİMAT] kaldırılmalıdır.
        """
        cleaned = clean_text_for_speech(raw)
        self.assertNotIn("#", cleaned)
        self.assertNotIn("**", cleaned)
        self.assertNotIn("def foo():", cleaned)
        self.assertNotIn("https://github.com", cleaned)
        self.assertNotIn("[ENGELLENEN TALİMAT]", cleaned)
        self.assertIn("Sayın Hilmi", cleaned)
        self.assertIn("sistem şu anda", cleaned)

    def test_kokoro_speech_synthesis(self):
        res = self.tool.synthesize_speech(
            text="Hello Mr. Hilmi, JARVIS systems are online and fully operational.",
            voice_name="am_adam",
            speed=1.05
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["engine"], "kokoro-82m-onnx")
        self.assertGreater(res["duration_seconds"], 0.5)
        self.assertTrue(os.path.exists(res["file_path"]))
        self.assertTrue(res["audio_url"].startswith("/output/jarvis_voices/"))

    def test_process_voice_command(self):
        res = self.tool.process_voice_command(
            user_input="Hey Jarvis, bugün ne yapmam gerekiyor?",
            auto_synthesize=True
        )
        self.assertTrue(res["success"])
        self.assertTrue(res["wake_word_detected"])
        self.assertEqual(res["specialist"], "AssistantSpecialist")
        self.assertIn("Sayın Hilmi", res["speak_text"])
        self.assertIsNotNone(res["audio_url"])

    def test_orchestrator_voice_intents(self):
        # 1. Synthesize Speech intent
        speak_intent = orchestrator.handle_intent("seslendir: Sistemler aktif efendim.")
        self.assertEqual(speak_intent["specialist"], "VoiceSpecialist")
        self.assertEqual(speak_intent["intent"], "synthesize_speech")
        self.assertTrue(speak_intent["result"]["success"])

        # 2. Voice Status intent
        status_intent = orchestrator.handle_intent("ses sistemi durumu")
        self.assertEqual(status_intent["specialist"], "VoiceSpecialist")
        self.assertEqual(status_intent["intent"], "voice_status")
        self.assertIn("Kokoro-82M", status_intent["speak_text"])

    def test_fastapi_voice_endpoints(self):
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {LOCAL_SESSION_TOKEN}"}

        # 1. GET /api/jarvis/voice/status
        st_resp = client.get("/api/jarvis/voice/status", headers=headers)
        self.assertEqual(st_resp.status_code, 200)
        st_data = st_resp.json()
        self.assertEqual(st_data["status"], "success")
        self.assertEqual(st_data["voice_status"]["status"], "ready")

        # 2. POST /api/jarvis/voice/speak
        sp_resp = client.post(
            "/api/jarvis/voice/speak",
            json={"text": "Test speech synthesis", "voice": "am_adam"},
            headers=headers
        )
        self.assertEqual(sp_resp.status_code, 200)
        sp_data = sp_resp.json()
        self.assertEqual(sp_data["status"], "success")
        self.assertTrue(sp_data["speech"]["audio_url"].startswith("/output/jarvis_voices/"))

        # 3. POST /api/jarvis/voice/command
        cmd_resp = client.post(
            "/api/jarvis/voice/command",
            json={"text": "Hey Jarvis, bilgisayarım neden yavaşladı?"},
            headers=headers
        )
        self.assertEqual(cmd_resp.status_code, 200)
        cmd_data = cmd_resp.json()
        self.assertEqual(cmd_data["status"], "success")
        self.assertTrue(cmd_data["voice_response"]["wake_word_detected"])


if __name__ == "__main__":
    unittest.main()
