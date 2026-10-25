"""
Tests for:
1. WhatsApp chat overview timestamp normalization, relative time formatting, and recent chat priority.
2. Contacts deduplication and consolidation.
3. User profile and hardware dossier integration into JARVIS memory graph and persona prompt.
"""

import unittest
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

from core_jarvis.whatsapp_daemon import whatsapp_daemon
from core_jarvis.memory_graph import memory_graph
from core_jarvis.jarvis_brain import JARVIS_PERSONA_PROMPT


class TestUserPersonaAndChatSorting(unittest.TestCase):

    def test_timestamp_normalization(self):
        """Tests that timestamps in seconds, milliseconds, or string are properly normalized to seconds."""
        # Standard seconds float
        ts_sec = 1792949062.0
        self.assertEqual(whatsapp_daemon._normalize_timestamp(ts_sec), 1792949062.0)

        # Milliseconds (13 digits > 1e11)
        ts_ms = 1792949062000.0
        self.assertAlmostEqual(whatsapp_daemon._normalize_timestamp(ts_ms), 1792949062.0, places=3)

        # String millisecond
        self.assertAlmostEqual(whatsapp_daemon._normalize_timestamp("1792949062000"), 1792949062.0, places=3)

        # None or invalid
        self.assertEqual(whatsapp_daemon._normalize_timestamp(None), 0.0)
        self.assertEqual(whatsapp_daemon._normalize_timestamp("invalid"), 0.0)

    def test_format_chat_time_relative_display(self):
        """Tests relative time display: Today (HH:MM), Yesterday (Dün), Weekday name, Older (DD.MM.YYYY)."""
        now = datetime(2026, 10, 25, 20, 30, 0)

        # Today at 20:24
        ts_today = datetime(2026, 10, 25, 20, 24, 0).timestamp()
        self.assertEqual(whatsapp_daemon.format_chat_time(ts_today, now_dt=now), "20:24")

        # Yesterday
        ts_yesterday = datetime(2026, 10, 24, 22, 13, 0).timestamp()
        self.assertEqual(whatsapp_daemon.format_chat_time(ts_yesterday, now_dt=now), "Dün")

        # 3 days ago (Thursday - Perşembe)
        ts_3days = datetime(2026, 10, 22, 16, 2, 0).timestamp()
        self.assertEqual(whatsapp_daemon.format_chat_time(ts_3days, now_dt=now), "Perşembe")

        # 10 days ago (Older than a week -> DD.MM.YYYY)
        ts_10days = datetime(2026, 10, 15, 11, 0, 0).timestamp()
        self.assertEqual(whatsapp_daemon.format_chat_time(ts_10days, now_dt=now), "15.10.2026")

    def test_chats_overview_sorting_and_deduplication(self):
        """Tests that get_chats_overview puts recent chats at the top and has no duplicate contacts."""
        overview = whatsapp_daemon.get_chats_overview()
        self.assertTrue(len(overview) > 0)

        # Verify that list is sorted in descending chronological order
        timestamps = [c.get("timestamp", 0) for c in overview if c.get("timestamp", 0) > 0]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))

        # Check top contacts
        top_ids = [c["id"] for c in overview[:5]]
        self.assertIn("c_owner", top_ids)

        # Verify that duplicates are not present in overview
        all_ids = [c["id"] for c in overview]
        self.assertNotIn("c_359", all_ids)  # Ödemeli Annem was removed/merged
        self.assertNotIn("c_317", all_ids)  # Mücahit Hilmi Ünal was merged into c_owner

        # Verify that c_owner is unique
        owner_entries = [c for c in overview if c["id"] == "c_owner"]
        self.assertEqual(len(owner_entries), 1)

    def test_user_profile_json_structure(self):
        """Verifies that config/user_profile.json contains all required baseline sections."""
        prof_file = Path("config/user_profile.json")
        self.assertTrue(prof_file.exists())

        with open(prof_file, "r", encoding="utf-8") as f:
            prof = json.load(f)

        # Check identity
        ident = prof.get("identity", {})
        self.assertEqual(ident.get("full_name"), "Mücahit Hilmi Ünal")
        self.assertIn("Mücon", ident.get("nicknames", []))
        self.assertIn("Hilmi", ident.get("nicknames", []))
        self.assertEqual(ident.get("birth_date"), "20.03.2005")
        self.assertIn("Eskişehir", ident.get("location", ""))

        # Check hardware
        hw = prof.get("hardware_baseline", {})
        self.assertIn("14400F", hw.get("cpu", ""))
        self.assertIn("RX 9060 XT", hw.get("gpu", ""))
        self.assertIn("16 GB", hw.get("ram", ""))
        self.assertIn("SN5100", hw.get("storage", ""))

        # Check communication protocols
        comm = prof.get("communication_protocols", {})
        self.assertIn("balım", comm.get("default_tone", {}).get("allowed_terms_of_endearment", []))
        self.assertIn("müfettiş", " ".join(comm.get("inspector_mode", {}).get("triggers", [])))

        # Check project constraints (Lussera local-only)
        lus = prof.get("projects", {}).get("lussera", {})
        self.assertIn("ASLA", lus.get("strict_rule", ""))
        self.assertIn("yerel", lus.get("strict_rule", "").lower())

    def test_memory_graph_synchronization(self):
        """Verifies that memory_graph syncs the user profile and includes it in context summary."""
        memory_graph.sync_user_profile()
        summary = memory_graph.get_context_summary()

        self.assertIn("Mücahit Hilmi", summary)
        self.assertIn("RX 9060 XT", summary)
        self.assertIn("lussera", summary.lower())
        self.assertIn("balım", summary)

    def test_jarvis_persona_prompt_contains_rules(self):
        """Verifies that JARVIS_PERSONA_PROMPT contains the dual persona, hardware baseline, and project rules."""
        self.assertIn("Mücahit Hilmi", JARVIS_PERSONA_PROMPT)
        self.assertIn("balım", JARVIS_PERSONA_PROMPT)
        self.assertIn("hayatım", JARVIS_PERSONA_PROMPT)
        self.assertIn("Müfettiş Modu", JARVIS_PERSONA_PROMPT)
        self.assertIn("RX 9060 XT", JARVIS_PERSONA_PROMPT)
        self.assertIn("i5-14400F", JARVIS_PERSONA_PROMPT)
        self.assertIn("Lussera", JARVIS_PERSONA_PROMPT)
        self.assertIn("Asla Varsayım Yapma", JARVIS_PERSONA_PROMPT)

    def test_browser_automation_and_youtube_playback(self):
        """Tests browser web search and direct YouTube video launching."""
        from core_jarvis.tools.system_tool import system_tool

        # Web search in browser
        res_search = system_tool.open_browser_search("yapay zeka haberleri", engine="google")
        self.assertTrue(res_search.get("success"))
        self.assertIn("google.com/search", res_search.get("url"))
        self.assertEqual(res_search.get("query"), "yapay zeka haberleri")

        # YouTube playback
        res_yt = system_tool.open_youtube_video("Barış Özcan son videosu")
        self.assertTrue(res_yt.get("success"))
        self.assertIn("youtube.com", res_yt.get("url"))

    def test_series_history_inspection_and_episode_opening(self):
        """Tests browser history inspection for TV show progress and opening the target episode."""
        from core_jarvis.tools.system_tool import system_tool

        # Inspect history for series
        hist = system_tool.inspect_browser_history_for_series("Breaking Bad")
        self.assertTrue(hist.get("found"))
        self.assertIn("Breaking Bad", hist.get("series"))

        # Open episode from history
        ep_res = system_tool.open_series_episode("Breaking Bad", from_history=True)
        self.assertTrue(ep_res.get("success"))
        self.assertIn("Breaking Bad", ep_res.get("message"))

    def test_live_weather_service(self):
        """Tests live weather retrieval with Open-Meteo & resilient seasonal fallback."""
        from core_jarvis.tools.system_tool import system_tool

        w = system_tool.get_live_weather("Eskişehir")
        self.assertTrue(w.get("success"))
        self.assertEqual(w.get("city"), "Eskişehir")
        self.assertIn("Eskişehir", w.get("summary_text"))
        self.assertTrue(w.get("temperature") > -50)

    def test_jarvis_brain_intent_routes_new_actions(self):
        """Tests that JARVIS Brain cleanly routes YouTube, series, browser search, and live weather intents."""
        from core_jarvis.jarvis_brain import jarvis_brain

        # YouTube intent
        r1 = jarvis_brain.process_message("YouTube'da Barış Özcan son videosunu aç")
        self.assertEqual(r1.get("action_taken"), "play_youtube")
        self.assertIn("YouTube", r1.get("reply"))

        # Browser search intent
        r2 = jarvis_brain.process_message("Tarayıcıda yapay zeka haberleri ara")
        self.assertEqual(r2.get("action_taken"), "browser_search")
        self.assertIn("Tarayıcıda Web Araması", r2.get("reply"))

        # Series intent
        r3 = jarvis_brain.process_message("Breaking Bad dizisinde son kaldığım bölümü aç")
        self.assertEqual(r3.get("action_taken"), "watch_series")
        self.assertIn("Dizi Oynatıcı", r3.get("reply"))

        # Weather intent
        r4 = jarvis_brain.process_message("Eskişehir hava durumu nasıl?")
        self.assertEqual(r4.get("action_taken"), "live_weather")
        self.assertIn("Hava Durumu", r4.get("reply"))


if __name__ == "__main__":
    unittest.main()
