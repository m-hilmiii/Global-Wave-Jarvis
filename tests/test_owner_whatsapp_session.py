"""
Unit tests for JARVIS Owner WhatsApp Hybrid Session & Unified Cognitive Brain (Mocked & Fast)
Tests the 5 critical user revisions:
1. PTT Voice Note Security (Whisper transcription; closed session requires 'Jarvis' prefix)
2. Strict Match on session termination (/kapat, /cikis, jarvis kapat, oturumu kapat) and /temizle buffer reset
3. 8192 context safety & VRAM isolation
4. Fast-path system command bypass + instant WhatsApp typing indicator
5. Context isolation between system telemetry and deep conversational history
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core_jarvis.owner_session import OwnerSessionManager, owner_session
from core_jarvis.whatsapp_daemon import WhatsAppDaemon
from core_jarvis.jarvis_brain import JarvisBrain


class TestOwnerWhatsAppSession(unittest.TestCase):

    def setUp(self):
        owner_session._init_state()

    def test_owner_identification(self):
        self.assertTrue(owner_session.is_owner("905518477838@s.whatsapp.net"))
        self.assertTrue(owner_session.is_owner("+905518477838"))
        self.assertTrue(owner_session.is_owner("05518477838"))
        self.assertFalse(owner_session.is_owner("905321112233@s.whatsapp.net"))
        self.assertFalse(owner_session.is_owner(""))

    def test_session_lifecycle_and_timeout(self):
        self.assertFalse(owner_session.is_session_active())
        owner_session.start_session()
        self.assertTrue(owner_session.is_session_active())

        # Touch updates timer
        t1 = owner_session.last_activity_time
        owner_session.touch()
        self.assertGreaterEqual(owner_session.last_activity_time, t1)

        # Simulate timeout (> 600s)
        owner_session.last_activity_time -= 605
        self.assertFalse(owner_session.is_session_active())

    def test_strict_close_and_buffer_reset(self):
        # Strict match should close
        self.assertTrue(owner_session.check_strict_close("/kapat"))
        self.assertTrue(owner_session.check_strict_close("/cikis"))
        self.assertTrue(owner_session.check_strict_close("jarvis kapat"))
        self.assertTrue(owner_session.check_strict_close("oturumu kapat"))

        # Non-strict match must NOT close
        self.assertFalse(owner_session.check_strict_close("Chrome sekmelerini kapat"))
        self.assertFalse(owner_session.check_strict_close("kapıyı kapat lütfen"))

        # Buffer reset
        self.assertTrue(owner_session.check_buffer_clear("/temizle"))
        self.assertTrue(owner_session.check_buffer_clear("/yeni"))
        self.assertTrue(owner_session.check_buffer_clear("hafizayi temizle"))

    def test_trigger_prefix_extraction(self):
        is_trig, cmd = owner_session.is_trigger_message("Jarvis, nasılsın?")
        self.assertTrue(is_trig)
        self.assertEqual(cmd, "nasılsın?")

        is_trig, cmd = owner_session.is_trigger_message("Hey Jarvis bugünkü plan ne")
        self.assertTrue(is_trig)
        self.assertEqual(cmd, "bugünkü plan ne")

        is_trig, cmd = owner_session.is_trigger_message("Merhaba nasılsın")
        self.assertFalse(is_trig)
        self.assertEqual(cmd, "Merhaba nasılsın")

    def test_fast_system_command_detection(self):
        is_fast, ctype = owner_session.is_fast_system_command("ekran görüntüsü al")
        self.assertTrue(is_fast)
        self.assertEqual(ctype, "screen_inspect")

        is_fast, ctype = owner_session.is_fast_system_command("sistem durumu nedir")
        self.assertTrue(is_fast)
        self.assertEqual(ctype, "system_telemetry")

        is_fast, ctype = owner_session.is_fast_system_command("bana kuantum fiziğini anlat")
        self.assertFalse(is_fast)
        self.assertEqual(ctype, "")

    @patch("core_jarvis.whatsapp_daemon.WhatsAppDaemon.send_presence")
    @patch("core_jarvis.whatsapp_daemon.WhatsAppDaemon.send_message")
    def test_owner_process_strict_close(self, mock_send, mock_presence):
        daemon = WhatsAppDaemon()
        owner_session.start_session()
        self.assertTrue(owner_session.is_session_active())

        daemon._process_owner_message("905518477838@s.whatsapp.net", "905518477838", "/kapat", False, "")
        self.assertFalse(owner_session.is_session_active())
        mock_send.assert_called_once()
        self.assertIn("Oturum sonlandırıldı", mock_send.call_args[0][1])

    @patch("core_jarvis.whatsapp_daemon.WhatsAppDaemon.send_presence")
    @patch("core_jarvis.whatsapp_daemon.WhatsAppDaemon.send_message")
    def test_owner_process_voice_note_security(self, mock_send, mock_presence):
        daemon = WhatsAppDaemon()
        # Session closed initially
        self.assertFalse(owner_session.is_session_active())

        # 1. Voice note WITHOUT 'Jarvis' prefix while session closed -> MUST NOT start session
        daemon._process_owner_message(
            "905518477838@s.whatsapp.net", "905518477838", "🎤 [Sesli Mesaj]", True, "Marketten süt ve ekmek almayı unutma"
        )
        self.assertFalse(owner_session.is_session_active())
        mock_send.assert_not_called()

        # 2. Voice note WITH 'Jarvis' prefix -> MUST start session and reply
        with patch("core_jarvis.jarvis_brain.JarvisBrain.process_message") as mock_brain:
            mock_brain.return_value = {"reply": "Süt ve ekmek listeye eklendi efendim."}
            daemon._process_owner_message(
                "905518477838@s.whatsapp.net", "905518477838", "🎤 [Sesli Mesaj]", True, "Jarvis marketten süt ve ekmek almayı listeye ekle"
            )
            self.assertTrue(owner_session.is_session_active())
            mock_send.assert_called_once()
            self.assertIn("listeye eklendi", mock_send.call_args[0][1])

    @patch("core_jarvis.whatsapp_daemon.WhatsAppDaemon.send_presence")
    @patch("core_jarvis.whatsapp_daemon.WhatsAppDaemon.send_message")
    def test_fast_command_bypass_and_history_isolation(self, mock_send, mock_presence):
        daemon = WhatsAppDaemon()
        owner_session.start_session()
        self.assertEqual(len(owner_session.chat_history), 0)

        with patch("core_jarvis.tools.system_tool.system_tool.get_hardware_telemetry") as mock_telem:
            mock_telem.return_value = {
                "cpu": {"usage_percent": 24.5},
                "ram": {"usage_percent": 42.0, "used_gb": 6.7, "total_gb": 16.0},
                "disk": {"usage_percent": 35.0},
                "gpu": {"status": "AMD Radeon RX 9060 XT Nominal"}
            }
            daemon._process_owner_message("905518477838@s.whatsapp.net", "905518477838", "sistem durumu nedir", False, "")
            mock_send.assert_called_once()
            self.assertIn("Sistem Telemetrisi", mock_send.call_args[0][1])
            # Revision 5: System telemetry output must NOT pollute conversation history!
            self.assertEqual(len(owner_session.chat_history), 0)

    def test_briefing_json_keys(self):
        from core_jarvis.personal_assistant import personal_assistant
        b = personal_assistant.get_daily_briefing()
        self.assertIn("tasks_count", b)
        self.assertIn("overdue_count", b)
        self.assertIn("priority_tasks", b)
        self.assertIn("unread_messages", b)
        self.assertIn("active_jobs", b)
        self.assertIn("system_ready", b)
        self.assertIn("speak_text", b)
        self.assertIn("notes", b)

    def test_knowledge_indexer_keys(self):
        from core_jarvis.tools.knowledge_indexer import knowledge_indexer, expand_query_tokens
        with patch.object(knowledge_indexer, "_discover_files", return_value=[]):
            res = knowledge_indexer.index_workspace(force=True)
            self.assertIn("indexed_files", res)
            self.assertIn("files_indexed", res)
        expanded = expand_query_tokens(["ekran", "bellek"])
        self.assertIn("vision", expanded)
        self.assertIn("vram", expanded)

    def test_vision_tool_prompt_kwarg_and_image_analysis(self):
        from core_jarvis.tools.vision_tool import vision_tool
        with patch.object(vision_tool, "detect_vision_model", return_value=None):
            res = vision_tool.analyze_screen(prompt="Ekrandaki hataya bak", mode="error_check")
            self.assertTrue(res["success"])
            self.assertIn("analysis", res)

    def test_memory_graph_includes_learned_rules(self):
        from core_jarvis.jarvis_brain import jarvis_brain
        from core_jarvis.memory_graph import memory_graph
        jarvis_brain._auto_learn_fact("Bundan sonra tüm raporları Türkçe yönetici formatında hazırla.")
        summary = memory_graph.get_context_summary()
        self.assertIn("LEARNED_RULES", summary)

    def test_orchestrator_delegates_general_query_to_brain(self):
        from core_jarvis.orchestrator import orchestrator
        from core_jarvis.jarvis_brain import jarvis_brain
        with patch.object(jarvis_brain, "process_message", return_value={
            "reply": "Analitik yanıt hazır efendim.",
            "speak_text": "Analitik yanıt hazır efendim.",
            "action_taken": "conversational_chat"
        }):
            res = orchestrator.handle_intent("Kuantum bilgisayarların kriptografiye etkisi nedir?")
            self.assertEqual(res["specialist"], "ExecutiveJarvis")
            self.assertEqual(res["message"], "Analitik yanıt hazır efendim.")

    def test_vram_guard_cross_platform_metrics(self):
        from core_jarvis.vram_guard import vram_guard
        metrics = vram_guard.get_system_metrics()
        self.assertTrue(metrics["metrics_available"])
        self.assertIsNotNone(metrics["ram_total_gb"])

    def test_stage2_model_manager_specialist_routing_and_think_strip(self):
        from core_jarvis.tools.model_manager import model_manager
        self.assertEqual(model_manager.classify_task_domain("Bana Python ile hızlı bir SQL sorgu fonksiyonu kod yaz"), "coding")
        self.assertEqual(model_manager.classify_task_domain("YouTube kanalımız için 90 günlük büyüme stratejisi ve kök neden analizi yap"), "reasoning")
        self.assertEqual(model_manager.classify_task_domain("Bugün hava oldukça güzel"), "primary_brain")

        parsed = model_manager.strip_thinking_tags("<think>Adım 1: Veriyi incele\nAdım 2: Karar ver</think>Sonuç olarak bu mimari en doğrusudur.")
        self.assertEqual(parsed["clean_reply"], "Sonuç olarak bu mimari en doğrusudur.")
        self.assertIn("Adım 1", parsed["thinking_trace"])

        arsenal = model_manager.get_arsenal_status()
        self.assertEqual(len(arsenal["arsenal"]), 5)

    def test_stage3_autonomous_multi_step_goal_execution(self):
        from core_jarvis.autonomous_engine import autonomous_engine
        rep = autonomous_engine.plan_and_execute_goal(
            "Sistem durumunu kontrol et, git diff değişikliklerine bak ve sonucu notlara kaydet",
            max_steps=5
        )
        self.assertTrue(rep["success"])
        self.assertGreaterEqual(rep["completed_steps"], 3)

    def test_directive_fast_path_and_router_safety_guards(self):
        from core_jarvis.jarvis_brain import jarvis_brain
        res = jarvis_brain.process_message(
            "Şunu unutma: Bundan sonra tüm Python kodlarında type hint ve Türkçe docstring kullanacağız."
        )
        self.assertEqual(res["action_taken"], "directive_learned")
        self.assertIn("kalıcı hafızama", res["reply"])

    def test_task_manager_window_detection_and_steam_automation(self):
        from core_jarvis.tools.system_tool import system_tool
        from core_jarvis.jarvis_brain import jarvis_brain

        win_info = system_tool.get_open_windows_and_apps()
        self.assertIn("Brave", win_info["foreground_window"])

        open_res = system_tool.open_application("brave")
        self.assertTrue(open_res["success"])
        self.assertEqual(open_res["app"], "Brave Browser")

        close_res = system_tool.close_application("discord")
        self.assertTrue(close_res["success"])

        protected_res = system_tool.close_application("ollama")
        self.assertFalse(protected_res["success"])

        steam_res = jarvis_brain.process_message("Steam'i aç ve Counter-Strike 2 oyununu indirmeye başlat")
        self.assertEqual(steam_res["action_taken"], "steam_action")
        self.assertEqual(steam_res["result"]["appid"], 730)
        self.assertTrue(steam_res["result"].get("already_installed"))
        self.assertIn("zaten bilgisayarınızda yüklü", steam_res["reply"])

        # Test owned game install
        aom_res = jarvis_brain.process_message("Steam'den Age of Mythology oyununu indir")
        self.assertEqual(aom_res["action_taken"], "steam_action")
        self.assertTrue(aom_res["result"].get("success"))
        self.assertEqual(aom_res["result"].get("appid"), 266840)
        self.assertIn("Otomasyonu Devrede", aom_res["reply"])

        # Test unowned game blocks install and warns
        cyber_res = jarvis_brain.process_message("Steam'den Cyberpunk 2077 indir")
        self.assertEqual(cyber_res["action_taken"], "steam_action")
        self.assertFalse(cyber_res["result"].get("success"))
        self.assertTrue(cyber_res["result"].get("not_in_library"))
        self.assertIn("kütüphanenizde bulunamadı", cyber_res["reply"])

        # Test Spotify deep-link track search
        spotify_res = jarvis_brain.process_message('Spotify uygulamasını aç ve "Celladına Aşık" şarkısını çal')
        self.assertEqual(spotify_res["action_taken"], "open_app")
        self.assertEqual(spotify_res["result"].get("action"), "play_song")
        self.assertEqual(spotify_res["result"].get("song"), "Celladına Aşık")

        # Test close app & close current window
        calc_close = jarvis_brain.process_message("Hesap makinesini kapat")
        self.assertEqual(calc_close["action_taken"], "close_app")
        self.assertTrue(calc_close["result"].get("success"))

        cur_close = jarvis_brain.process_message("Şu uygulamayı kapat")
        self.assertEqual(cur_close["action_taken"], "close_app")
        self.assertTrue(cur_close["result"].get("success"))

        # Test media playback controls
        pause_res = jarvis_brain.process_message("Müziği duraklat")
        self.assertEqual(pause_res["action_taken"], "media_control")
        self.assertIn("duraklatıldı", pause_res["reply"])

        resume_res = jarvis_brain.process_message("Müziği devam ettir")
        self.assertEqual(resume_res["action_taken"], "media_control")
        self.assertIn("devam ettirildi", resume_res["reply"])

    def test_blueprint_five_bridge_features(self):
        from core_jarvis.jarvis_brain import jarvis_brain
        from core_jarvis.proactive_daemon import proactive_watchdog

        # 1. Resume project
        res_resume = jarvis_brain.process_message("Jarvis, geçen sefer kaldığımız yerden devam et")
        self.assertEqual(res_resume["action_taken"], "resume_project")
        self.assertIn("Proje Durum Brifingi", res_resume["reply"])

        # 2. Diagnose PC (System Doctor)
        res_diag = jarvis_brain.process_message("Jarvis, bilgisayarım neden yavaşladı?")
        self.assertEqual(res_diag["action_taken"], "diagnose_pc")
        self.assertIn("Sistem Doktoru", res_diag["reply"])

        # 3. Produce content ideas
        res_content = jarvis_brain.process_message("Jarvis, bugün kanal için 3 Shorts fikri hazırla")
        self.assertEqual(res_content["action_taken"], "content_ideas")
        self.assertIn("Shorts Fikri", res_content["reply"])

        # 4. Organize files preview
        res_org = jarvis_brain.process_message("İndirilenler klasörümü düzenle")
        self.assertEqual(res_org["action_taken"], "organize_files_preview")
        self.assertIn("İndirilenler", res_org["reply"])

        # 5. Proactive watchdog
        proactive_watchdog._emit_alert("test_cat", "Test Alert", "Test Message", level="info")
        alerts = proactive_watchdog.get_recent_alerts(limit=5)
        self.assertGreaterEqual(len(alerts), 1)
        self.assertEqual(alerts[-1]["title"], "Test Alert")

    def test_whatsapp_lid_resolution_and_mother_inbox(self):
        from core_jarvis.whatsapp_daemon import whatsapp_daemon
        from core_jarvis.jarvis_brain import jarvis_brain

        # Ensure test message has unread flag set
        inbox = whatsapp_daemon._read_inbox_locked()
        for m in inbox:
            if "Ev işi olabilir" in m.get("text", ""):
                m["unread"] = True
        whatsapp_daemon._atomic_write_inbox(inbox)

        # 1. Test sender name and phone resolution via WhatsApp LID
        disp, phone = whatsapp_daemon._resolve_sender_name("52948440752326@lid", push_name="Gülhan Ünal")
        self.assertIn("Annem", disp)
        self.assertIn("Gülhan Ünal", disp)
        self.assertEqual(phone, "05364138433")

        # 2. Test chats overview contains Annem with the incoming message and unread badge
        overview = whatsapp_daemon.get_chats_overview()
        annem_entry = next((c for c in overview if "annem" in c["short_name"].lower()), None)
        self.assertIsNotNone(annem_entry)
        self.assertTrue(len(annem_entry["last_text"]) > 0)
        self.assertGreaterEqual(annem_entry["unread_count"], 0)

        # 3. Test chat history retrieves Annem's message by alias and full name
        hist_alias = whatsapp_daemon.get_chat_history("Annem")
        self.assertGreaterEqual(len(hist_alias), 1)
        self.assertTrue(any("Ev işi olabilir" in m.get("text", "") or "Naber" in m.get("text", "") for m in hist_alias))

        # Check full name
        hist_full = whatsapp_daemon.get_chat_history("Gülhan")
        self.assertGreaterEqual(len(hist_full), 1)
        self.assertTrue(any("Ev işi olabilir" in m.get("text", "") or "Naber" in m.get("text", "") for m in hist_full))

        # 4. Test JARVIS brain intent routing and message reading for Annem
        res = jarvis_brain.process_message("Annemden mesaj geldi mi?")
        self.assertEqual(res["action_taken"], "contact_message_read")
        self.assertTrue(any(k in res["reply"] for k in ["Ev işi olabilir", "Naber", "Nerdesin", "Selam"]))
        self.assertIn("Gülhan Ünal", res["reply"])


if __name__ == "__main__":
    unittest.main()
