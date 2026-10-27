"""
Unit test suite verifying Jarvis v3.0 Adaptive Model Architecture:
- Single King (qwen3:8b) with permanent VRAM residency (keep_alive: -1)
- bge-m3 Embedding & Zero-Hop Semantic Router
- On-Demand Heavy Duty Escalation (qwen2.5-coder:14b & qwen3:14b) with 15m Sticky Sessions
- qwen2.5vl:7b Vision Specialist with 2m quick-release
"""

import unittest
import time
from unittest.mock import patch, MagicMock

from core_jarvis.tools.model_manager import model_manager, SPECIALIST_ARSENAL
from core_jarvis.jarvis_brain import jarvis_brain


class TestJarvisV3AdaptiveArchitecture(unittest.TestCase):

    def setUp(self):
        model_manager.reset_to_primary()

    def test_specialist_arsenal_definitions(self):
        """Verifies the 5 pinpoint specialist models in v3.0 arsenal."""
        roles = {s["role"] for s in SPECIALIST_ARSENAL}
        self.assertIn("primary_brain", roles)
        self.assertIn("embedding", roles)
        self.assertIn("vision", roles)
        self.assertIn("coding", roles)
        self.assertIn("reasoning", roles)

        # Primary Brain should be qwen3:8b
        primary = next(s for s in SPECIALIST_ARSENAL if s["role"] == "primary_brain")
        self.assertEqual(primary["name"], "qwen3:8b")
        self.assertIn(str(primary["keep_alive"]), ("-1", "-1m"))

        # Embedding should be bge-m3
        embed = next(s for s in SPECIALIST_ARSENAL if s["role"] == "embedding")
        self.assertIn("bge-m3", embed["name"])

        # Vision should be qwen2.5vl
        vision = next(s for s in SPECIALIST_ARSENAL if s["role"] == "vision")
        self.assertIn("qwen2.5vl", vision["name"])

    def test_task_domain_classification(self):
        """Verifies intelligent complexity heuristic separation."""
        # Routine chat
        self.assertEqual(model_manager.classify_task_domain("Selam balım nasılsın?"), "primary_brain")

        # Coding queries
        self.assertEqual(model_manager.classify_task_domain("Python'da hızlıca bir liste ters çevirme fonksiyonu yaz"), "coding")
        self.assertEqual(model_manager.classify_task_domain("FastAPI'de async endpoint nasıl tanımlanır?"), "coding")

        # Reasoning queries
        self.assertEqual(
            model_manager.classify_task_domain("Global Wave ajansı için 90 günlük YouTube büyüme stratejisi ve monetizasyon planı hazırla"),
            "reasoning"
        )

        # Complexity Heuristics (needs_heavy_lifting)
        # 1. Lightweight code stays on King 8B (is_heavy=False)
        is_h, dom = model_manager.needs_heavy_lifting("Bana Python ile hızlı bir SQL sorgu fonksiyonu kod yaz")
        self.assertFalse(is_h)
        self.assertEqual(dom, "coding")

        # 2. Heavy refactor escalates to 14B (is_heavy=True)
        is_h_heavy, dom_heavy = model_manager.needs_heavy_lifting("Lussera projesindeki tüm veritabanı mimarisini refactor et ve yeniden yapılandır")
        self.assertTrue(is_h_heavy)
        self.assertEqual(dom_heavy, "coding")

        # 3. Deep 90-day strategy escalates to 14B (is_heavy=True)
        is_h_strat, dom_strat = model_manager.needs_heavy_lifting("90 günlük YouTube büyüme stratejisi ve kök neden analizi yap")
        self.assertTrue(is_h_strat)
        self.assertEqual(dom_strat, "reasoning")

    def test_sticky_session_behavior(self):
        """Verifies 15-minute sticky session persistence without ping-pong swapping."""
        # 1. Normal query gets primary brain with -1
        model_1, keep_1 = model_manager.get_active_model_for_request("Nasılsın balım?")
        self.assertEqual(model_1, "qwen3:8b")
        self.assertEqual(keep_1, "-1")

        # 2. Heavy coding query escalates to heavy coder with 15m
        model_2, keep_2 = model_manager.get_active_model_for_request("Şu 3 dosyayı refactor et ve mimari denetim yap")
        self.assertEqual(model_2, "qwen2.5-coder:14b")
        self.assertEqual(keep_2, "15m")

        # 3. Subsequent routine query stays on 14B because sticky session is active
        model_3, keep_3 = model_manager.get_active_model_for_request("Harika, şimdi de bir kahve müziği aç")
        self.assertEqual(model_3, "qwen2.5-coder:14b")
        self.assertEqual(keep_3, "15m")

        # 4. Manual reset returns cleanly to primary brain
        model_manager.reset_to_primary()
        model_4, keep_4 = model_manager.get_active_model_for_request("Normal sohbete devam")
        self.assertEqual(model_4, "qwen3:8b")
        self.assertEqual(keep_4, "-1")

    def test_zero_hop_router_optimization(self):
        """Verifies that conversational chat bypasses Ollama router entirely (sub-millisecond return)."""
        with patch.object(jarvis_brain, "_call_ollama") as mock_call:
            res = jarvis_brain._route_intent("Selam balım, günün nasıl geçiyor?")
            # For casual conversation, _call_ollama should NOT even be called!
            mock_call.assert_not_called()
            self.assertEqual(res.get("action"), "chat")

    def test_tool_intent_routes_when_tool_keywords_present(self):
        """Verifies that when tool keywords are present, intent routing is invoked properly."""
        with patch.object(jarvis_brain, "_call_ollama") as mock_call:
            mock_call.return_value = '{"action": "reply_whatsapp", "target_person": "Annem", "user_instruction": "atölyedeyim"}'
            res = jarvis_brain._route_intent("Anneme mesaj at atölyedeyim de")
            mock_call.assert_called_once()
            self.assertEqual(res.get("action"), "reply_whatsapp")
            self.assertEqual(res.get("target_person"), "Annem")

    def test_strip_thinking_tags(self):
        """Verifies clean reply extraction from models that emit <think> traces."""
        raw = "<think>\nThinking through the mathematical proof step by step...\n</think>\nSonuç 42'dir balım."
        res = model_manager.strip_thinking_tags(raw)
        self.assertEqual(res["clean_reply"], "Sonuç 42'dir balım.")
        self.assertIn("Thinking through the mathematical proof", res["thinking_trace"])

    def test_cosine_similarity_math(self):
        """Verifies the mathematical cosine similarity calculation."""
        v1 = [1.0, 0.0, 0.0]
        v2 = [1.0, 0.0, 0.0]
        v3 = [0.0, 1.0, 0.0]
        self.assertAlmostEqual(model_manager.cosine_similarity(v1, v2), 1.0)
        self.assertAlmostEqual(model_manager.cosine_similarity(v1, v3), 0.0)

    def test_arsenal_status_reporting(self):
        """Verifies that get_arsenal_status reports the complete Jarvis v3.0 telemetry."""
        status = model_manager.get_arsenal_status()
        self.assertIn("architecture", status)
        self.assertIn("Jarvis v3.0", status["architecture"])
        self.assertIn("hardware_target", status)
        self.assertIn("RX 9060 XT", status["hardware_target"])
        self.assertGreaterEqual(len(status["arsenal"]), 5)


if __name__ == "__main__":
    unittest.main()
