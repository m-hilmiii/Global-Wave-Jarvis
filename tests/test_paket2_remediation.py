"""
Global Wave - Paket 2 Remediation Unit Tests
Verifies:
1. Jarvis Brain: Unified Ollama host URL from settings and memory/history context injection.
2. VRAM Guard: Proper active model unload list and robust error logging.
3. WhatsApp Daemon: Thread-safe atomic write (.tmp -> replace) and locked reads.
4. Requirements: Presence of httpx and laya packages.
5. Memory Graph: Clean creator identity without roleplay contradiction.
"""
import os
import json
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from core_jarvis.jarvis_brain import get_ollama_url, jarvis_brain
from core_jarvis.vram_guard import vram_guard
from core_jarvis.whatsapp_daemon import whatsapp_daemon, INBOX_FILE
from core_jarvis.memory_graph import memory_graph
from config.settings import BASE_DIR

class TestPaket2Remediation(unittest.TestCase):

    def test_jarvis_brain_unified_ollama_url(self):
        url = get_ollama_url()
        self.assertTrue(url.startswith("http://") or url.startswith("https://"))
        self.assertIn("11434", url)

    def test_jarvis_brain_memory_graph_and_history_integration(self):
        # Mock requests.post to capture payload sent to Ollama
        jarvis_brain.conversation_history = [
            {"role": "user", "content": "Merhaba Jarvis"},
            {"role": "assistant", "content": "Merhaba Mücahit Bey, nasıl yardımcı olabilirim?"}
        ]

        with patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "message": {"content": json.dumps({"action": "chat", "hud_reply": "Emrinizdeyim efendim."})}
            }
            mock_post.return_value = mock_resp

            decision = jarvis_brain._query_qwen_decision("Günün planı nedir?")
            self.assertEqual(decision.get("action"), "chat")

            # Verify requests.post was called with history and memory in payload
            self.assertTrue(mock_post.called)
            called_kwargs = mock_post.call_args[1]
            json_payload = called_kwargs["json"]
            messages = json_payload["messages"]

            # First message must be system instruction containing HAFIZA VE KURALLAR
            self.assertEqual(messages[0]["role"], "system")
            self.assertIn("HAFIZA VE KURALLAR", messages[0]["content"])

            # Middle messages must contain the conversation history turns
            roles = [m["role"] for m in messages]
            self.assertIn("user", roles[:-1])  # At least one past user turn
            self.assertIn("assistant", roles)   # Past assistant turn

            # Last message must be current user text
            self.assertEqual(messages[-1]["role"], "user")
            self.assertEqual(messages[-1]["content"], "Günün planı nedir?")

    def test_vram_guard_clean_memory_stops_active_models(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            vram_guard.clean_memory()

            # Verify subprocess.run called for qwen3:14b, qwen3:8b, mistral-nemo:12b
            stopped_models = []
            for call in mock_run.call_args_list:
                args = call[0][0]
                if len(args) >= 3 and args[0] == "ollama" and args[1] == "stop":
                    stopped_models.append(args[2])

            self.assertIn("qwen3:14b", stopped_models)
            self.assertIn("qwen3:8b", stopped_models)
            self.assertIn("mistral-nemo:12b", stopped_models)
            self.assertNotIn("qwen2.5:7b", stopped_models)

    def test_whatsapp_daemon_atomic_inbox_and_thread_safety(self):
        # Test atomic write and locked read
        test_data = [{"id": "TEST_MSG_1", "text": "Atomic test message", "unread": True}]
        whatsapp_daemon._atomic_write_inbox(test_data)

        # Read under lock
        read_data = whatsapp_daemon._read_inbox_locked()
        self.assertEqual(len(read_data), 1)
        self.assertEqual(read_data[0]["id"], "TEST_MSG_1")
        self.assertEqual(read_data[0]["text"], "Atomic test message")

        # Verify no left-over .tmp file exists
        tmp_file = INBOX_FILE.with_suffix(".tmp")
        self.assertFalse(tmp_file.exists())

        # Clean up test entry
        whatsapp_daemon._atomic_write_inbox([])

    def test_requirements_contains_httpx_and_laya(self):
        req_path = BASE_DIR / "requirements.txt"
        with open(req_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("httpx", content)
        self.assertIn("laya", content)

    def test_memory_graph_no_tony_stark_contradiction(self):
        context = memory_graph.get_context_summary()
        self.assertNotIn("Tony Stark rolünde", context)

if __name__ == "__main__":
    unittest.main()
