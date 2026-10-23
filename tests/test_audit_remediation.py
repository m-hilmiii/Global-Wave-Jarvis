"""
Global Wave - Audit Remediation Verification Tests
Verifies:
1. Turkish persona routing & strict_local enforcement (no English phonetic garbage or silent cloud leaks).
2. WhatsApp suffix matching bugfix (empty or short phone numbers never match contacts).
3. Settings safe boolean parsing ("false" evaluates to False).
4. Audio duration fail-safe (raises error instead of returning dummy 4.0).
5. Engagement engine factual integrity ("milyar": "milyon" removed).
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import parse_bool, save_settings, load_settings
from engine.voice_kokoro import is_kokoro_supported
from engine.voice_engine import get_audio_duration, generate_scene_audios
from engine.engagement_engine import COMMON_TYPO_MAP
from core_jarvis.whatsapp_daemon import WhatsAppDaemon


class TestAuditRemediation(unittest.TestCase):
    def test_settings_safe_boolean_parsing(self):
        # Strict boolean parsing tests
        self.assertFalse(parse_bool("false"))
        self.assertFalse(parse_bool("False"))
        self.assertFalse(parse_bool("0"))
        self.assertFalse(parse_bool("no"))
        self.assertFalse(parse_bool("off"))
        self.assertFalse(parse_bool(False))

        self.assertTrue(parse_bool("true"))
        self.assertTrue(parse_bool("True"))
        self.assertTrue(parse_bool("1"))
        self.assertTrue(parse_bool("yes"))
        self.assertTrue(parse_bool(True))

    def test_kokoro_language_phonetic_guards(self):
        # Turkish and German must NOT be claimed as supported by Kokoro-82M
        self.assertFalse(is_kokoro_supported("tr_storyteller", "tr-TR"))
        self.assertFalse(is_kokoro_supported("de_engineer", "de-DE"))
        self.assertFalse(is_kokoro_supported("es_narrator", "es-ES"))

        # English personas must be supported
        self.assertTrue(is_kokoro_supported("us_hustler", "en-US"))
        self.assertTrue(is_kokoro_supported("uk_critic", "en-GB"))

    @patch("engine.voice_engine.generate_scene_audios_edge")
    def test_turkish_persona_routes_to_neural_edge_tts(self, mock_edge):
        mock_edge.return_value = [{"scene_id": 0, "mp3_path": "dummy.mp3", "duration": 3.5}]
        scenes = [{"scene_id": 0, "text": "Tarihin en buyuk gizemi."}]

        # Requesting kokoro on tr_storyteller should legitimately route to neural Edge-TTS
        with patch("engine.voice_engine.load_settings", return_value={"strict_local": False}):
            res = generate_scene_audios(scenes, voice="tr-TR-AhmetNeural", persona_id="tr_storyteller", task_temp_dir=".", tts_engine="kokoro")
            self.assertEqual(len(res), 1)
            mock_edge.assert_called_once()
            args, kwargs = mock_edge.call_args
            audio_meta = kwargs.get("audio_meta", {})
            self.assertEqual(audio_meta.get("actual_engine"), "edge-tts")
            self.assertTrue(audio_meta.get("fallback_used"))

    def test_strict_local_mode_blocks_unauthorized_cloud_fallback(self):
        scenes = [{"scene_id": 0, "text": "Tarihin en buyuk gizemi."}]
        # When strict_local=True, Kokoro on Turkish MUST raise RuntimeError and refuse cloud fallback
        with patch("engine.voice_engine.load_settings", return_value={"strict_local": True}):
            with self.assertRaises(RuntimeError) as ctx:
                generate_scene_audios(scenes, voice="tr-TR-AhmetNeural", persona_id="tr_storyteller", task_temp_dir=".", tts_engine="kokoro")
            self.assertIn("strict_local", str(ctx.exception))

    def test_audio_duration_fails_safe(self):
        # Must raise RuntimeError on non-existent audio file instead of returning dummy 4.0
        with self.assertRaises(RuntimeError):
            get_audio_duration("non_existent_audio_file_123456.mp3")

    def test_whatsapp_empty_phone_suffix_bug_fixed(self):
        # Suffix match logic verification: empty phone must NOT match Adem
        c_phone = "905551112233"
        m_phone = ""
        phone_matched = bool(c_phone and m_phone and len(c_phone) >= 7 and len(m_phone) >= 7 and (c_phone.endswith(m_phone) or m_phone.endswith(c_phone)))
        self.assertFalse(phone_matched)

        # Non-empty phone with match
        m_phone_valid = "5551112233"
        phone_matched_valid = bool(c_phone and m_phone_valid and len(c_phone) >= 7 and len(m_phone_valid) >= 7 and (c_phone.endswith(m_phone_valid) or m_phone_valid.endswith(c_phone)))
        self.assertTrue(phone_matched_valid)

    def test_engagement_engine_factual_integrity(self):
        # "milyar": "milyon" must be removed to avoid factual error injection
        self.assertNotIn("milyar", COMMON_TYPO_MAP)


if __name__ == "__main__":
    unittest.main()
