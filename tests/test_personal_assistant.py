"""
Unit Tests for Personal Assistant & Daily Planner Engine (Stage 5)
Verifies:
1. Daily Briefing aggregation (Agenda, tasks, reality state, communications)
2. Task CRUD & completion flow
3. Reminder engine
4. Executive quick notes
5. Orchestrator intent routing for daily assistant queries
6. FastAPI REST endpoints for assistant
"""

import unittest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from core_jarvis.personal_assistant import personal_assistant, PersonalAssistant
from core_jarvis.orchestrator import orchestrator
from web.server import app, LOCAL_SESSION_TOKEN

class TestPersonalAssistant(unittest.TestCase):

    def test_daily_briefing_structure(self):
        briefing = personal_assistant.get_daily_briefing()
        self.assertIn("date", briefing)
        self.assertIn("day_name", briefing)
        self.assertIn("tasks", briefing)
        self.assertIn("project_state", briefing)
        self.assertIn("communications", briefing)
        self.assertIn("executive_briefing_text", briefing)
        self.assertIn("Sayın Hilmi", briefing["executive_briefing_text"])

    def test_task_management_lifecycle(self):
        # 1. Add Task
        res = personal_assistant.add_task(
            title="Antigravity Birim Testi",
            priority="urgent",
            due_date=datetime.now().strftime("%Y-%m-%d"),
            category="development"
        )
        self.assertTrue(res["success"])
        task_id = res["task"]["id"]
        self.assertEqual(res["task"]["status"], "pending")

        # 2. Query task in active list
        tasks = personal_assistant.get_tasks()
        task_ids = [t["id"] for t in tasks]
        self.assertIn(task_id, task_ids)

        # 3. Complete Task
        comp_res = personal_assistant.complete_task(task_id)
        self.assertTrue(comp_res["success"])
        self.assertEqual(comp_res["task"]["status"], "completed")
        self.assertIsNotNone(comp_res["task"]["completed_at"])

    def test_overdue_task_detection(self):
        yesterday_str = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        res = personal_assistant.add_task(
            title="Gecikmiş Eski Görev",
            priority="high",
            due_date=yesterday_str
        )
        self.assertTrue(res["success"])
        overdue_id = res["task"]["id"]

        briefing = personal_assistant.get_daily_briefing()
        overdue_ids = [t["id"] for t in briefing["tasks"]["overdue"]]
        self.assertIn(overdue_id, overdue_ids)
        self.assertIn("gecikmiş göreviniz bulunuyor", briefing["executive_briefing_text"])

    def test_reminders_and_notes(self):
        # 1. Add Reminder
        rem_res = personal_assistant.add_reminder(
            title="Toplantı Hatırlatıcısı",
            datetime_iso=f"{datetime.now().strftime('%Y-%m-%d')}T15:30:00",
            lead_minutes=10
        )
        self.assertTrue(rem_res["success"])
        reminders = personal_assistant.get_reminders()
        self.assertTrue(any(r["id"] == rem_res["reminder"]["id"] for r in reminders))

        # 2. Add Note
        note_res = personal_assistant.add_note(
            title="Test Memosu",
            content="Jarvis Stage 5 kişisel asistan entegre edildi.",
            tags=["jarvis", "milestone"]
        )
        self.assertTrue(note_res["success"])
        notes = personal_assistant.get_notes()
        self.assertTrue(any(n["id"] == note_res["note"]["id"] for n in notes))

    def test_orchestrator_assistant_intents(self):
        # 1. Briefing intent
        res_brief = orchestrator.handle_intent("Jarvis, bugün ne yapmam gerekiyor?")
        self.assertEqual(res_brief["specialist"], "AssistantSpecialist")
        self.assertEqual(res_brief["intent"], "daily_briefing")
        self.assertIn("speak_text", res_brief)

        # 2. Add task intent
        res_task = orchestrator.handle_intent("görev ekle: YouTube shorts yayınla")
        self.assertEqual(res_task["specialist"], "AssistantSpecialist")
        self.assertEqual(res_task["intent"], "add_task")
        self.assertTrue(res_task["result"]["success"])

        # 3. Add note intent
        res_note = orchestrator.handle_intent("not al: Yeni proje fikri")
        self.assertEqual(res_note["specialist"], "AssistantSpecialist")
        self.assertEqual(res_note["intent"], "add_note")
        self.assertTrue(res_note["result"]["success"])

    def test_api_assistant_endpoints(self):
        client = TestClient(app)
        headers = {"X-Local-Token": LOCAL_SESSION_TOKEN}

        # 1. GET /api/jarvis/assistant/briefing
        b_res = client.get("/api/jarvis/assistant/briefing", headers=headers)
        self.assertEqual(b_res.status_code, 200)
        self.assertEqual(b_res.json()["status"], "success")
        self.assertIn("briefing", b_res.json())

        # 2. GET /api/jarvis/assistant/tasks
        t_res = client.get("/api/jarvis/assistant/tasks", headers=headers)
        self.assertEqual(t_res.status_code, 200)
        self.assertEqual(t_res.json()["status"], "success")

        # 3. POST /api/jarvis/assistant/tasks
        post_task = client.post(
            "/api/jarvis/assistant/tasks",
            json={"title": "API Görevi", "priority": "high"},
            headers=headers
        )
        self.assertEqual(post_task.status_code, 200)
        created_id = post_task.json()["result"]["task"]["id"]

        # 4. POST /api/jarvis/assistant/tasks/{task_id}/complete
        comp_task = client.post(f"/api/jarvis/assistant/tasks/{created_id}/complete", headers=headers)
        self.assertEqual(comp_task.status_code, 200)
        self.assertTrue(comp_task.json()["result"]["success"])

        # 5. GET & POST /api/jarvis/assistant/notes
        post_note = client.post(
            "/api/jarvis/assistant/notes",
            json={"title": "Not Başlığı", "content": "İçerik", "tags": ["api"]},
            headers=headers
        )
        self.assertEqual(post_note.status_code, 200)
        self.assertTrue(post_note.json()["result"]["success"])


if __name__ == "__main__":
    unittest.main()
