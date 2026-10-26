"""
Global Wave - Audit Remediation Comprehensive Verification Tests
Verifies:
1. Strict local mode enforcement: Blocks ElevenLabs, Edge-TTS, and Kokoro fallbacks before any network call.
2. Closed whitelist for Kokoro: Both persona and language must be supported; fr-FR, tr-TR, de-DE, es-ES, None are rejected.
3. Real WhatsApp get_chats_overview and get_chat_history calls: Empty phones and broadcasts never attach to contacts.
4. Settings schema: parse_bool raises ValueError on invalid values; load_settings validates ollama_host safety.
5. SSE Single-Use Stream Ticket: Query tokens are rejected; tickets are single-use with TTL.
"""

import unittest
import sys
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import config.settings as settings_mod
from config.settings import parse_bool, save_settings, load_settings, validate_ollama_host
from engine.voice_kokoro import is_kokoro_supported
from engine.voice_engine import get_audio_duration, generate_scene_audios
from engine.engagement_engine import COMMON_TYPO_MAP
from core_jarvis.whatsapp_daemon import WhatsAppDaemon
from web.server import app, LOCAL_SESSION_TOKEN, STREAM_TICKETS, STREAM_TICKETS_LOCK
from fastapi.testclient import TestClient


class TestAuditRemediation(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    # =========================================================================
    # 1. SETTINGS & SCHEMA VALIDATION TESTS
    # =========================================================================
    def test_settings_strict_boolean_parsing(self):
        # Valid booleans
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

        # Invalid/ambiguous booleans must raise ValueError (not silently convert to False)
        with self.assertRaises(ValueError):
            parse_bool("maybe")
        with self.assertRaises(ValueError):
            parse_bool("disabled")
        with self.assertRaises(ValueError):
            parse_bool("2")
        with self.assertRaises(ValueError):
            parse_bool("undefined")

    def test_load_settings_enforces_ollama_host_validation(self):
        # Even if a remote host was pre-saved in tokens.json, load_settings must reject it when allow_remote=False
        fake_tokens = {
            "ollama_host": "http://malicious-external-host.com:11434",
            "allow_remote_ollama": False
        }
        with patch.object(Path, "exists", return_value=True), \
             patch("builtins.open", unittest.mock.mock_open(read_data=json.dumps(fake_tokens))):
            loaded = load_settings()
            # Must have fallen back to localhost
            self.assertEqual(loaded["ollama_host"], "http://127.0.0.1:11434")

    # =========================================================================
    # 2. STRICT LOCAL MODE TTS TESTS
    # =========================================================================
    @patch("engine.voice_engine.synthesize_chunk_elevenlabs")
    def test_strict_local_blocks_elevenlabs(self, mock_eleven):
        scenes = [{"scene_id": 0, "text": "Hello world"}]
        with patch("engine.voice_engine.load_settings", return_value={"strict_local": True}):
            with self.assertRaises(ValueError) as ctx:
                generate_scene_audios(scenes, voice="en-US-GuyNeural", persona_id="us_hustler", task_temp_dir=".", tts_engine="elevenlabs")
            self.assertIn("strict_local", str(ctx.exception))
            mock_eleven.assert_not_called()

    @patch("engine.voice_engine.generate_scene_audios_edge")
    def test_strict_local_blocks_edge_tts(self, mock_edge):
        scenes = [{"scene_id": 0, "text": "Hello world"}]
        with patch("engine.voice_engine.load_settings", return_value={"strict_local": True}):
            with self.assertRaises(ValueError) as ctx:
                generate_scene_audios(scenes, voice="en-US-GuyNeural", persona_id="us_hustler", task_temp_dir=".", tts_engine="edge-tts")
            self.assertIn("strict_local", str(ctx.exception))
            mock_edge.assert_not_called()

    @patch("engine.voice_engine.generate_scene_audios_kokoro", side_effect=RuntimeError("Kokoro model missing"))
    @patch("engine.voice_engine.generate_scene_audios_edge")
    def test_strict_local_blocks_failed_kokoro_cloud_fallback(self, mock_edge, mock_kokoro):
        scenes = [{"scene_id": 0, "text": "Hello world"}]
        with patch("engine.voice_engine.load_settings", return_value={"strict_local": True}):
            with self.assertRaises(RuntimeError) as ctx:
                generate_scene_audios(scenes, voice="en-US-GuyNeural", persona_id="us_hustler", task_temp_dir=".", tts_engine="kokoro")
            self.assertIn("Bulut fallback engellendi", str(ctx.exception))
            mock_edge.assert_not_called()

    # =========================================================================
    # 3. KOKORO CLOSED WHITELIST LANGUAGE TESTS
    # =========================================================================
    def test_kokoro_closed_whitelist_languages(self):
        # Supported English personas with explicit supported languages
        self.assertTrue(is_kokoro_supported("us_hustler", "en-US"))
        self.assertTrue(is_kokoro_supported("uk_critic", "en-GB"))

        # Explicitly unsupported or foreign languages MUST return False
        self.assertFalse(is_kokoro_supported("us_hustler", "fr-FR"))
        self.assertFalse(is_kokoro_supported("us_hustler", "tr-TR"))
        self.assertFalse(is_kokoro_supported("us_hustler", "de-DE"))
        self.assertFalse(is_kokoro_supported("us_hustler", "es-ES"))
        self.assertFalse(is_kokoro_supported("us_hustler", "pt-BR"))
        self.assertFalse(is_kokoro_supported("us_hustler", None))

        # Unsupported personas
        self.assertFalse(is_kokoro_supported("tr_storyteller", "tr-TR"))
        self.assertFalse(is_kokoro_supported("de_engineer", "de-DE"))

    # =========================================================================
    # 4. REAL WHATSAPP OVERVIEW & HISTORY MATCHING TESTS
    # =========================================================================
    def test_whatsapp_overview_and_history_real_matching(self):
        daemon = WhatsAppDaemon()

        fake_contacts = [
            {"id": "adem", "name": "Adem", "full_name": "Adem", "phone": "05551112233", "relationship": "Arkadaş"},
            {"id": "babam", "name": "Babam", "full_name": "Babam", "phone": "05559998877", "relationship": "Aile"}
        ]
        fake_inbox = [
            # Message 1: Empty phone and group JID (MUST NOT MATCH ANY CONTACT)
            {"id": "m1", "phone": "", "sender_name": "Borsa Duyuru Grubu", "text": "Halka arz duyurusu", "chat_jid": "group99@g.us", "sender_jid": "anon@s.whatsapp.net", "timestamp": 100},
            # Message 2: Adem's legitimate message
            {"id": "m2", "phone": "05551112233", "sender_name": "Adem", "text": "Selam nasılsın?", "chat_jid": "905551112233@s.whatsapp.net", "sender_jid": "905551112233@s.whatsapp.net", "timestamp": 200},
            # Message 3: Unknown spammer
            {"id": "m3", "phone": "05550000000", "sender_name": "Spam", "text": "Kredi kazandınız", "chat_jid": "905550000000@s.whatsapp.net", "timestamp": 300}
        ]

        def fake_file_reader(filepath, *args, **kwargs):
            if "contacts.json" in str(filepath):
                return unittest.mock.mock_open(read_data=json.dumps({"contacts": fake_contacts}))()
            if "whatsapp_inbox.json" in str(filepath):
                return unittest.mock.mock_open(read_data=json.dumps(fake_inbox))()
            return unittest.mock.mock_open(read_data="{}")()

        with patch.object(Path, "exists", return_value=True), \
             patch("builtins.open", side_effect=fake_file_reader):
            # 1. Test get_chats_overview
            overview = daemon.get_chats_overview()
            adem_card = next((c for c in overview if c["short_name"] == "Adem"), None)
            babam_card = next((c for c in overview if c["short_name"] == "Babam"), None)

            self.assertIsNotNone(adem_card)
            self.assertIsNotNone(babam_card)

            # Adem's latest message must be "Selam nasılsın?"
            self.assertEqual(adem_card["last_text"], "Selam nasılsın?")
            # Babam must have NO messages (the empty-phone broadcast was NOT attached!)
            self.assertEqual(babam_card["last_text"], "Henüz mesaj yok")

            # 2. Test get_chat_history
            adem_history = daemon.get_chat_history("Adem")
            babam_history = daemon.get_chat_history("Babam")

            self.assertEqual(len(adem_history), 1)
            self.assertEqual(adem_history[0]["text"], "Selam nasılsın?")

            self.assertEqual(len(babam_history), 0)

    # =========================================================================
    # 5. SSE STREAM TICKET TESTS
    # =========================================================================
    def test_sse_query_token_rejected_and_ticket_lifecycle(self):
        # 1. Long-lived session token in query params MUST BE REJECTED
        res = self.client.get(f"/api/events/task_123?token={LOCAL_SESSION_TOKEN}")
        self.assertEqual(res.status_code, 401)
        self.assertIn("stream ticket", res.json().get("message", "").lower())

        # 2. Requesting a ticket without auth header must be rejected
        res = self.client.post("/api/stream/ticket")
        self.assertEqual(res.status_code, 401)

        # 3. Requesting a ticket with valid X-Local-Token succeeds
        res = self.client.post("/api/stream/ticket", headers={"X-Local-Token": LOCAL_SESSION_TOKEN})
        self.assertEqual(res.status_code, 200)
        ticket = res.json().get("ticket")
        self.assertTrue(bool(ticket))

        # 4. Valid single-use ticket connects successfully to SSE endpoint
        from web.server import TASKS
        TASKS["task_test"] = {"status": "completed", "percent": 100}
        with self.client.stream("GET", f"/api/events/task_test?ticket={ticket}") as sse_stream:
            self.assertEqual(sse_stream.status_code, 200)
            for line in sse_stream.iter_lines():
                break

        # 5. Attempting to reuse the same ticket MUST FAIL (single-use consumed)
        res_reuse = self.client.get(f"/api/events/task_test?ticket={ticket}")
        self.assertEqual(res_reuse.status_code, 401)

        # 6. Expired ticket MUST FAIL
        with STREAM_TICKETS_LOCK:
            STREAM_TICKETS["expired-ticket-test"] = time.time() - 10
        res_exp = self.client.get("/api/events/task_test?ticket=expired-ticket-test")
        self.assertEqual(res_exp.status_code, 401)

    # =========================================================================
    # 6. AUDIO & ENGAGEMENT INTEGRITY
    # =========================================================================
    def test_audio_duration_fails_safe(self):
        with self.assertRaises(RuntimeError):
            get_audio_duration("non_existent_audio_file_123456.mp3")

    def test_engagement_engine_factual_integrity(self):
        self.assertNotIn("milyar", COMMON_TYPO_MAP)

    # =========================================================================
    # 7. DEEP AUDIT P1/P2 SECURITY REMEDIATIONS
    # =========================================================================
    def test_auto_dispatch_whatsapp_string_boolean_parsed_strictly(self):
        """P1: 'False' string must parse as boolean False, never activating auto-dispatch."""
        from config.settings import parse_bool, load_settings, save_settings
        self.assertFalse(parse_bool("False"))
        self.assertFalse(parse_bool("false"))
        self.assertFalse(parse_bool("0"))
        self.assertTrue(parse_bool("True"))
        self.assertTrue(parse_bool("1"))

        # Test settings persistence
        s = load_settings()
        s["auto_dispatch_whatsapp"] = "False"
        saved = save_settings(s)
        self.assertIs(saved["auto_dispatch_whatsapp"], False)
        reloaded = load_settings()
        self.assertIs(reloaded["auto_dispatch_whatsapp"], False)

    def test_path_traversal_blocked_in_summarize_and_snapshot(self):
        """P1: Traversal out of workspace in summarize_document and create_snapshot must be blocked."""
        from core_jarvis.tools.knowledge_indexer import knowledge_indexer
        from core_jarvis.tools.system_tool import system_tool

        # 1. Traversal in document summarize
        res_doc = knowledge_indexer.summarize_document("../../Windows/System32/drivers/etc/hosts")
        self.assertFalse(res_doc["success"])
        self.assertIn("Güvenlik engeli", res_doc["error"])

        # 2. Sensitive pattern blocking
        res_secret = knowledge_indexer.summarize_document("config/tokens.json")
        self.assertFalse(res_secret["success"])
        self.assertIn("Güvenlik engeli", res_secret["error"])

        # 3. Traversal in create_snapshot
        res_snap = system_tool.create_snapshot("../../../etc/passwd")
        self.assertFalse(res_snap["success"])
        self.assertIn("engellendi", res_snap["error"].lower())

    def test_powershell_true_allowlist_enforcement(self):
        """P1: Arbitrary PowerShell execution without allowlist membership must be blocked."""
        from core_jarvis.tools.system_tool import system_tool

        # Command not on allowlist
        res = system_tool.run_safe_powershell("Invoke-Expression 'Get-Host'")
        self.assertFalse(res["allowed"])
        self.assertIn("GÜVENLİK", res["error"])

        # Command chaining attempt
        res_chain = system_tool.run_safe_powershell("Get-Process; whoami")
        self.assertFalse(res_chain["allowed"])
        self.assertIn("GÜVENLİK İHLALİ", res_chain["error"])

    def test_ssrf_blocked_on_private_and_loopback_ips(self):
        """P2: SSRF attempts against loopback, private IPs or non-http schemes must be rejected."""
        from core_jarvis.tools.browser_research_tool import browser_research_tool

        safe1, reason1 = browser_research_tool.is_safe_public_url("http://127.0.0.1:8000/api")
        self.assertFalse(safe1)
        self.assertIn("engellendi", reason1.lower())

        safe2, reason2 = browser_research_tool.is_safe_public_url("http://localhost:5000/admin")
        self.assertFalse(safe2)
        self.assertIn("engellendi", reason2.lower())

        safe3, reason3 = browser_research_tool.is_safe_public_url("file:///etc/passwd")
        self.assertFalse(safe3)
        self.assertIn("http/https", reason3)

    def test_wol_requires_server_side_confirmation(self):
        """P1: WOL endpoint requires confirmed=True and valid MAC."""
        # 1. Missing confirmation -> 403
        res = self.client.post(
            "/api/jarvis/wol/wake",
            json={"mac_address": "9C:6B:00:B2:A2:0F", "confirmed": False},
            headers={"X-Local-Token": LOCAL_SESSION_TOKEN}
        )
        self.assertEqual(res.status_code, 403)

        # 2. Invalid MAC -> 400
        res_bad = self.client.post(
            "/api/jarvis/wol/wake",
            json={"mac_address": "INVALID_MAC_ADDR", "confirmed": True},
            headers={"X-Local-Token": LOCAL_SESSION_TOKEN}
        )
        self.assertEqual(res_bad.status_code, 400)


if __name__ == "__main__":
    unittest.main()
