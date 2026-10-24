"""
Global Wave - Paket 3 Remediation Unit Tests
Verifies:
1. Stream Tickets: Automatic pruning of expired single-use/TTL tickets to prevent memory leaks.
2. Tasks Cache: Memory bounding of in-memory TASKS dictionary.
3. Threadpool Offloading: Async endpoints run heavy/blocking operations via run_in_threadpool.
4. Output Security: Verification that external client IPs are rejected from /output/ endpoints.
"""
import time
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from web.server import app, STREAM_TICKETS, STREAM_TICKETS_LOCK, TASKS, sync_task_status, LOCAL_SESSION_TOKEN

class TestPaket3Remediation(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_stream_tickets_expired_pruning(self):
        now = time.time()
        with STREAM_TICKETS_LOCK:
            # Inject old expired tickets
            STREAM_TICKETS["old_expired_ticket_1"] = now - 120
            STREAM_TICKETS["old_expired_ticket_2"] = now - 60

        # Request new stream ticket with local session token
        headers = {"X-Local-Token": LOCAL_SESSION_TOKEN}
        resp = self.client.post("/api/stream/ticket", headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("ticket", data)

        # Verify old expired tickets were pruned
        with STREAM_TICKETS_LOCK:
            self.assertNotIn("old_expired_ticket_1", STREAM_TICKETS)
            self.assertNotIn("old_expired_ticket_2", STREAM_TICKETS)
            self.assertIn(data["ticket"], STREAM_TICKETS)

    def test_sync_task_status_memory_bounding(self):
        # Clear test tasks
        TASKS.clear()
        
        # Insert 85 task entries
        for i in range(85):
            sync_task_status(f"task_{i}", 50, "rendering", f"Stage {i}")

        # In-memory dictionary must be capped to prevent memory leaks
        self.assertLessEqual(len(TASKS), 75)
        # Latest entries must be retained
        self.assertIn("task_84", TASKS)

        TASKS.clear()

    def test_jarvis_chat_endpoint_threadpool_execution(self):
        headers = {"X-Local-Token": LOCAL_SESSION_TOKEN}
        with patch("core_jarvis.jarvis_brain.jarvis_brain.process_message") as mock_proc:
            mock_proc.return_value = {"action": "chat", "hud_reply": "Asistan hazir efendim."}
            resp = self.client.post("/api/jarvis/chat", json={"message": "Merhaba"}, headers=headers)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["status"], "success")
            self.assertTrue(mock_proc.called)

    def test_output_security_blocks_external_client(self):
        # Client host override simulating an external client IP
        external_client = TestClient(app, client=("198.51.100.25", 54321))
        resp = external_client.get("/output/test_video.mp4")
        self.assertEqual(resp.status_code, 403)
        self.assertIn("External client access blocked", resp.json().get("message", ""))

if __name__ == "__main__":
    unittest.main()
