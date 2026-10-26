"""
Global-Wawe / Stark-Core - WhatsApp Advanced Features Unit Tests
Tests:
1. Auto-Dispatch WhatsApp (Zero-Click Mode vs. HITL Confirmation)
2. AI Delegate (Meşgul Modu / Human-like Assistant Delegation)
3. Baileys Store History Sync & Reconnect
4. WhatsApp Chat Export Import (.txt format)
5. Voice Note (PTT) Dispatch Architecture
"""

import os
import sys
import json
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ["JARVIS_TEST_MODE"] = "true"

from core_jarvis.jarvis_brain import jarvis_brain
from core_jarvis.whatsapp_daemon import whatsapp_daemon, INBOX_FILE
from core_jarvis.tools.whatsapp_tool import whatsapp_tool


class TestWhatsAppAdvancedFeatures(unittest.TestCase):

    def setUp(self):
        self.original_auto_dispatch = jarvis_brain.auto_dispatch_whatsapp
        self.original_delegate_active = whatsapp_daemon.ai_delegate_active
        self.original_delegate_targets = list(whatsapp_daemon.ai_delegate_targets)
        self.original_delegate_logs = list(whatsapp_daemon.ai_delegate_logs)
        self.original_inbox = whatsapp_daemon._read_inbox_locked()

    def tearDown(self):
        jarvis_brain.auto_dispatch_whatsapp = self.original_auto_dispatch
        whatsapp_daemon.ai_delegate_active = self.original_delegate_active
        whatsapp_daemon.ai_delegate_targets = self.original_delegate_targets
        whatsapp_daemon.ai_delegate_logs = self.original_delegate_logs
        whatsapp_daemon._atomic_write_inbox(self.original_inbox)

    def test_auto_dispatch_toggle_and_persistence(self):
        """Tests that auto_dispatch can be enabled and disabled programmatically."""
        jarvis_brain.set_auto_dispatch_whatsapp(True)
        self.assertTrue(jarvis_brain.auto_dispatch_whatsapp)

        jarvis_brain.set_auto_dispatch_whatsapp(False)
        self.assertFalse(jarvis_brain.auto_dispatch_whatsapp)

    def test_auto_dispatch_voice_command_fastpaths(self):
        """Tests voice and chat commands that toggle auto dispatch."""
        res1 = jarvis_brain.process_message("Jarvis, sormadan direkt gönder modunu aç")
        self.assertTrue(jarvis_brain.auto_dispatch_whatsapp)
        self.assertEqual(res1.get("action_taken"), "auto_dispatch_enabled")
        self.assertIn("Otomatik Gönderim Modu Açıldı", res1.get("reply", ""))

        res2 = jarvis_brain.process_message("Jarvis, onay iste her mesajda")
        self.assertFalse(jarvis_brain.auto_dispatch_whatsapp)
        self.assertEqual(res2.get("action_taken"), "auto_dispatch_disabled")
        self.assertIn("Onaylı Gönderim Modu Açıldı", res2.get("reply", ""))

    def test_auto_dispatch_direct_send(self):
        """When auto-dispatch is True, replies are sent directly without pending_draft."""
        jarvis_brain.auto_dispatch_whatsapp = True
        with patch.object(jarvis_brain.whatsapp, "send_message_to_phone") as mock_send, \
             patch.object(jarvis_brain, "_route_intent") as mock_route, \
             patch.object(jarvis_brain, "_synthesize_whatsapp_draft_or_ask") as mock_synth:
            
            mock_route.return_value = {
                "action": "reply_whatsapp",
                "target_person": "Babam",
                "user_instruction": "selam verip atölyedeyim yaz"
            }
            mock_synth.return_value = {
                "detected_intimacy": "samimi",
                "needs_user_decision": False,
                "draft_message": "Aleyküm selam babacığım, atölyedeyim."
            }
            mock_send.return_value = {"success": True, "status": "sent"}

            res = jarvis_brain.process_message("Babamın son mesajına selam verip atölyedeyim yaz")
            self.assertEqual(res.get("action_taken"), "whatsapp_auto_dispatched")
            self.assertIn("Doğrudan İletildi", res.get("reply", ""))
            mock_send.assert_called_once()

    def test_ai_delegate_activation_and_targeting(self):
        """Tests activating and targeting AI Delegate (Meşgul Modu)."""
        whatsapp_daemon.enable_ai_delegate("Babam")
        self.assertTrue(whatsapp_daemon.ai_delegate_active)
        self.assertIn("Babam", whatsapp_daemon.ai_delegate_targets)
        self.assertTrue(whatsapp_daemon.is_target_delegated("Babam (Yaşar Ünal)", "05432029704"))
        self.assertFalse(whatsapp_daemon.is_target_delegated("Ahmet Yılmaz", "05551234567"))

        # Test disabling
        logs = whatsapp_daemon.disable_ai_delegate()
        self.assertFalse(whatsapp_daemon.ai_delegate_active)
        self.assertEqual(len(whatsapp_daemon.ai_delegate_targets), 0)

    def test_ai_delegate_voice_commands(self):
        """Tests chat fast-paths for activating/deactivating AI Delegate."""
        res = jarvis_brain.process_message("Jarvis şu an çok meşgulüm Babamla sen konuş")
        self.assertEqual(res.get("action_taken"), "ai_delegate_enabled")
        self.assertTrue(whatsapp_daemon.ai_delegate_active)
        self.assertIn("Babam", whatsapp_daemon.ai_delegate_targets)

        # Deactivate
        res_close = jarvis_brain.process_message("Jarvis meşgul modunu kapat ben devralıyorum")
        self.assertEqual(res_close.get("action_taken"), "ai_delegate_disabled")
        self.assertFalse(whatsapp_daemon.ai_delegate_active)

    def test_generate_delegate_reply(self):
        """Tests that generate_delegate_reply generates an authentic assistant response."""
        with patch.object(jarvis_brain, "_call_ollama") as mock_call:
            mock_call.return_value = "Merhabalar Yaşar Bey, ben Mücahit Hilmi'nin yapay zeka asistanı JARVIS. Mücahit Bey şu anda önemli bir çalışma üzerinde olduğu için müsait değil. Acil bir durum varsa hemen not alıp kendisine iletebilirim."
            
            reply = jarvis_brain.generate_delegate_reply(
                sender_name="Babam (Yaşar Ünal)",
                incoming_text="Oğlum akşam kaçta gelirsin?",
                chat_history=[]
            )
            self.assertIn("JARVIS", reply)
            self.assertIn("Mücahit", reply)

    def test_import_chat_export_parser(self):
        """Tests parsing WhatsApp exported text format into local inbox."""
        sample_export = (
            "[24.10.2024, 14:30:15] Yaşar Ünal: Selam oğlum atölyede misin?\n"
            "[24.10.2024, 14:31:02] Mücahit Hilmi: Evet baba bilgisayar başındayım.\n"
            "[24.10.2024, 14:32:00] Yaşar Ünal: Tamam kolay gelsin.\n"
            "Görüşürüz.\n"
        )
        res = whatsapp_daemon.import_chat_export("Babam", sample_export)
        self.assertTrue(res.get("success"))
        self.assertGreaterEqual(res.get("count", 0), 3)

        # Verify messages exist in get_chat_history
        hist = whatsapp_daemon.get_chat_history("Babam")
        texts = [m.get("text", "") for m in hist]
        self.assertTrue(any("Selam oğlum atölyede misin" in t for t in texts))

    def test_reconnect_and_sync_state(self):
        """Tests reconnect_and_sync resets connection state without touching live auth dir."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            with patch.object(whatsapp_daemon, "start_bridge"), \
                 patch.object(whatsapp_daemon, "_kill_zombies"), \
                 patch("core_jarvis.whatsapp_daemon.AUTH_DIR", tmp_path), \
                 patch("core_jarvis.whatsapp_daemon.MEDIA_DIR", tmp_path):
                res = whatsapp_daemon.reconnect_and_sync()
                self.assertTrue(res.get("success"))
                self.assertFalse(whatsapp_daemon.socket_ready.is_set())

    def test_history_batch_sync_and_qr_status(self):
        """Tests _handle_history_batch and get_status qr_image field."""
        batch = [
            {
                "message_id": "HIST_BATCH_TEST_001",
                "jid": "905498705294@s.whatsapp.net",
                "sender": "905498705294@s.whatsapp.net",
                "text": "Geçmiş senkronizasyon test mesajı",
                "pushName": "Yaşar Ünal",
                "from_me": False,
                "timestamp": time.time() - 3600,
                "is_history": True
            }
        ]
        whatsapp_daemon._handle_history_batch(batch)
        hist = whatsapp_daemon.get_chat_history("Babam")
        self.assertTrue(any(m.get("id") == "HIST_BATCH_TEST_001" for m in hist))

        whatsapp_daemon.latest_qr_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg=="
        st = whatsapp_daemon.get_status()
        self.assertTrue(st.get("has_qr"))
        self.assertEqual(st.get("qr_image"), "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==")
        whatsapp_daemon.latest_qr_image = None

    def test_ai_delegate_newsletter_and_broadcast_exclusion(self):
        """Tests that newsletters, broadcast channels, and unconfigured groups are never delegated."""
        whatsapp_daemon.enable_ai_delegate()  # Delegate ALL mode
        self.assertTrue(whatsapp_daemon.ai_delegate_active)

        # 1. Newsletters must NEVER be delegated
        self.assertFalse(whatsapp_daemon.is_target_delegated("KPSS Duyuru", "120363403021905949", "120363403021905949@newsletter"))
        self.assertFalse(whatsapp_daemon.is_target_delegated("Kanal", "120363403021905949@newsletter"))

        # 2. Status broadcasts must NEVER be delegated
        self.assertFalse(whatsapp_daemon.is_target_delegated("Status", "status@broadcast", "status@broadcast"))

        # 3. Unconfigured groups must NOT be auto-spammed in general Meşgul Modu
        self.assertFalse(whatsapp_daemon.is_target_delegated("Aile Grubu (Grup)", "1203630283@g.us", "1203630283@g.us"))

        # 4. Standard 1-to-1 contact IS delegated
        self.assertTrue(whatsapp_daemon.is_target_delegated("Ahmet", "05551234567", "905551234567@s.whatsapp.net"))

        # 5. _process_delegate_message early-exits for newsletters
        with patch.object(whatsapp_daemon, "send_message") as mock_send:
            whatsapp_daemon._process_delegate_message("120363403021905949@newsletter", "120363403021905949", "Kanal", "Yeni haber!")
            mock_send.assert_not_called()

        whatsapp_daemon.disable_ai_delegate()

    def test_get_chat_history_performance_and_caching(self):
        """Tests that get_chat_history resolves unsaved JIDs in milliseconds with TTL caching."""
        t0 = time.time()
        res1 = whatsapp_daemon.get_chat_history("120363403021905949")
        dur1 = time.time() - t0
        self.assertIsInstance(res1, list)
        self.assertLess(dur1, 1.0)  # Must be sub-second

        t1 = time.time()
        res2 = whatsapp_daemon.get_chat_history("120363403021905949@newsletter")
        dur2 = time.time() - t1
        self.assertIsInstance(res2, list)
        self.assertLess(dur2, 0.2)  # Cached must be sub-200ms

        # Cache test
        maps1 = whatsapp_daemon._load_lid_and_pushname_maps()
        cache_ts1 = getattr(whatsapp_daemon, "_lid_maps_cache_ts", 0)
        self.assertGreater(cache_ts1, 0)
        maps2 = whatsapp_daemon._load_lid_and_pushname_maps()
        cache_ts2 = getattr(whatsapp_daemon, "_lid_maps_cache_ts", 0)
        self.assertEqual(cache_ts1, cache_ts2)


if __name__ == "__main__":
    unittest.main()
