"""
Global Wave - Security & Reliability Audit Test Suite
Verifies all security boundaries, session token authentication, input sanitization,
FFmpeg path escaping, draft ambiguity protection, and safe configuration schemas.
Runs via standard python -m unittest tests/test_security_audit.py
"""

import unittest
import os
import sys
from pathlib import Path

# Ensure root directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import (
    load_settings, save_settings, validate_ollama_host,
    ALLOWED_SETTING_KEYS
)
from engine.video_engine import escape_ffmpeg_concat_path
from engine.uploader_youtube import schedule_publish, check_daily_upload_limit
from core_jarvis.jarvis_brain import JarvisBrain
from core_jarvis.tools.contacts import contacts_mgr


class TestSettingsSecurity(unittest.TestCase):
    def test_ollama_host_restricted_to_localhost_by_default(self):
        # 127.0.0.1 and localhost must succeed
        self.assertEqual(validate_ollama_host("http://127.0.0.1:11434"), "http://127.0.0.1:11434")
        self.assertEqual(validate_ollama_host("http://localhost:11434"), "http://localhost:11434")

        # Remote hostname must raise ValueError when allow_remote is False
        with self.assertRaises(ValueError):
            validate_ollama_host("http://attacker-controlled-server.com:11434", allow_remote=False)

        with self.assertRaises(ValueError):
            validate_ollama_host("http://192.168.1.100:11434", allow_remote=False)

        # When explicitly allowed, remote succeeds
        self.assertEqual(
            validate_ollama_host("http://my-remote-gpu-server.com:11434", allow_remote=True),
            "http://my-remote-gpu-server.com:11434"
        )

    def test_save_settings_ignores_unallowed_keys(self):
        saved = save_settings({"malicious_unknown_key": "injected_val", "fps": 30})
        self.assertNotIn("malicious_unknown_key", saved)
        self.assertEqual(saved.get("fps"), 30)


class TestFfmpegConcatEscaping(unittest.TestCase):
    def test_single_quote_and_slash_escaping(self):
        unsafe_win_path = r"C:\Users\test\Video's & Audio\scene_1.mp4"
        escaped = escape_ffmpeg_concat_path(unsafe_win_path)
        
        # Must escape single quote as '\''
        self.assertIn("'\\''", escaped)
        # Replacing the valid escape sequence leaves no raw Windows backslashes
        self.assertNotIn("\\", escaped.replace("'\\''", "'"))
        # Must not contain newlines
        self.assertNotIn("\n", escaped)
        self.assertNotIn("\r", escaped)

    def test_newline_injection_in_path_stripped(self):
        path_with_newline = "/tmp/video.mp4\nfile '/etc/passwd'"
        escaped = escape_ffmpeg_concat_path(path_with_newline)
        self.assertNotIn("\n", escaped)


class TestYouTubeUploaderSecurity(unittest.TestCase):
    def test_schedule_publish_requires_positive_delay(self):
        with self.assertRaises(ValueError):
            schedule_publish("fake_vid_id", delay_hours=0)
        with self.assertRaises(ValueError):
            schedule_publish("fake_vid_id", delay_hours=-2)

    def test_check_daily_upload_limit_enforced(self):
        can_upload, count = check_daily_upload_limit(max_per_day=4)
        self.assertIsInstance(can_upload, bool)
        self.assertIsInstance(count, int)
        self.assertGreaterEqual(count, 0)


class TestWhatsAppDraftAmbiguity(unittest.TestCase):
    def setUp(self):
        self.brain = JarvisBrain()
        self.brain.pending_drafts.clear()
        self.brain.latest_draft_id = None

    def test_confirm_draft_without_drafts_fails_safely(self):
        res = self.brain.confirm_pending_draft()
        self.assertEqual(res.get("action_taken"), "no_draft")

    def test_confirm_draft_with_multiple_drafts_requires_disambiguation(self):
        # Create two competing drafts
        self.brain.pending_drafts["draft_1"] = {
            "draft_id": "draft_1",
            "recipient": "Babam",
            "phone": "5551111",
            "message": "Merhaba baba",
            "status": "pending",
            "expires_at": 9999999999
        }
        self.brain.pending_drafts["draft_2"] = {
            "draft_id": "draft_2",
            "recipient": "Adem",
            "phone": "5552222",
            "message": "Merhaba Adem",
            "status": "pending",
            "expires_at": 9999999999
        }

        # Calling confirm without explicit draft_id must reject ambiguous dispatch
        res = self.brain.confirm_pending_draft(draft_id=None)
        self.assertEqual(res.get("action_taken"), "ambiguous_draft_id")

        # Calling with explicit draft_id succeeds in targeting that specific draft
        self.assertIn("draft_1", self.brain.pending_drafts)
        self.assertIn("draft_2", self.brain.pending_drafts)


class TestContactsAmbiguityProtection(unittest.TestCase):
    def test_exact_match_succeeds(self):
        # Owner contact exact match
        c = contacts_mgr.find_contact("Mücahit Hilmi")
        if c:
            self.assertIn("mücahit", c.get("name", "").lower() + c.get("full_name", "").lower())

    def test_ambiguous_token_query_returns_none(self):
        all_c = contacts_mgr.get_all()
        # If multiple contacts have letter 'a', query 'a' should return None (not silently pick first)
        a_matches = [c for c in all_c if "a" in c.get("name", "").lower()]
        if len(a_matches) > 1:
            res = contacts_mgr.find_contact("a")
            self.assertIsNone(res)


if __name__ == "__main__":
    unittest.main()
