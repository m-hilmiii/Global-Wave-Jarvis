"""
Unit Tests for Multi-Agent Task Coordinator & Container/AI Infrastructure (Stage 4)
Verifies:
1. Supervised Background Job Execution, Progress, and Completion (TaskCoordinator)
2. Job Cancellation mechanics
3. Docker & Ollama Infrastructure Status (InfraTool)
4. Zero-Cost Dynamic Model Routing ($0.00 priority)
5. Orchestrator Infrastructure & Job Dispatch
6. FastAPI REST Endpoints (/api/jarvis/jobs, /api/jarvis/infra)
"""

import time
import unittest
from fastapi.testclient import TestClient

from core_jarvis.task_coordinator import task_coordinator, JobStatus
from core_jarvis.tools.infra_tool import infra_tool
from core_jarvis.orchestrator import orchestrator
from web.server import app, LOCAL_SESSION_TOKEN

class TestTaskCoordinatorAndInfra(unittest.TestCase):

    def test_job_execution_lifecycle(self):
        def sample_work(progress_callback=None):
            if progress_callback:
                progress_callback(30, "Aşama 1 tamamlandı")
                time.sleep(0.05)
                progress_callback(70, "Aşama 2 tamamlandı")
                time.sleep(0.05)
            return {"result_data": "success_123"}

        spawn_info = task_coordinator.spawn_job(
            title="Birim Testi Arka Plan İşi",
            specialist="SystemSpecialist",
            target_func=sample_work
        )
        job_id = spawn_info["job_id"]
        self.assertIn("job_", job_id)

        # Wait briefly for execution
        time.sleep(0.2)
        job_state = task_coordinator.get_job(job_id)
        self.assertIsNotNone(job_state)
        self.assertEqual(job_state["status"], JobStatus.COMPLETED)
        self.assertEqual(job_state["progress_pct"], 100)
        self.assertTrue(job_state["has_result"])

    def test_job_cancellation(self):
        def long_loop(progress_callback=None):
            for i in range(50):
                if progress_callback:
                    progress_callback(i * 2, f"Döngü {i}")
                time.sleep(0.05)
            return "done"

        spawn_info = task_coordinator.spawn_job(
            title="İptal Edilecek Uzun İş",
            specialist="ContentSpecialist",
            target_func=long_loop
        )
        job_id = spawn_info["job_id"]

        time.sleep(0.05)
        cancel_res = task_coordinator.cancel_job(job_id)
        self.assertTrue(cancel_res["success"])

        time.sleep(0.15)
        job_state = task_coordinator.get_job(job_id)
        self.assertEqual(job_state["status"], JobStatus.CANCELLED)

    def test_docker_and_ollama_discovery(self):
        docker_info = infra_tool.check_docker_status()
        self.assertIn("installed", docker_info)
        self.assertIn("running", docker_info)
        self.assertIn("summary", docker_info)

        ollama_info = infra_tool.get_ollama_models()
        self.assertIn("online", ollama_info)
        self.assertIn("models", ollama_info)

    def test_zero_cost_model_router(self):
        # 1. Coding task -> qwen2.5-coder:7b
        code_route = infra_tool.route_model_for_task("Python test and bugfix")
        self.assertEqual(code_route["chosen_model"], "qwen2.5-coder:7b")
        self.assertEqual(code_route["cost_usd"], 0.0)
        self.assertTrue(code_route["is_local"])

        # 2. Longform documentary -> default deep model
        doc_route = infra_tool.route_model_for_task("16min documentary script")
        self.assertIn("14b", doc_route["chosen_model"])
        self.assertEqual(doc_route["cost_usd"], 0.0)

        # 3. Routine task -> fast 8B model
        routine_route = infra_tool.route_model_for_task("routine sentiment triage")
        self.assertIn("8b", routine_route["chosen_model"])
        self.assertEqual(routine_route["cost_usd"], 0.0)

    def test_orchestrator_infra_intents(self):
        # 1. Docker intent
        d_res = orchestrator.handle_intent("docker durumu nedir?")
        self.assertEqual(d_res["specialist"], "SystemSpecialist")
        self.assertEqual(d_res["intent"], "check_docker")
        self.assertIn("running", d_res["result"])

        # 2. Ollama intent
        o_res = orchestrator.handle_intent("hangi yerel modeller yüklü?")
        self.assertEqual(o_res["specialist"], "SystemSpecialist")
        self.assertEqual(o_res["intent"], "get_ai_models")

        # 3. Jobs intent
        j_res = orchestrator.handle_intent("aktif görevler ve kuyruk")
        self.assertEqual(j_res["specialist"], "TaskCoordinator")
        self.assertEqual(j_res["intent"], "list_jobs")
        self.assertIsInstance(j_res["result"], list)

    def test_api_jobs_and_infra_endpoints(self):
        client = TestClient(app)
        headers = {"X-Local-Token": LOCAL_SESSION_TOKEN}

        # 1. GET /api/jarvis/jobs
        jobs_res = client.get("/api/jarvis/jobs", headers=headers)
        self.assertEqual(jobs_res.status_code, 200)
        self.assertEqual(jobs_res.json()["status"], "success")

        # 2. GET /api/jarvis/infra/docker
        dock_res = client.get("/api/jarvis/infra/docker", headers=headers)
        self.assertEqual(dock_res.status_code, 200)
        self.assertEqual(dock_res.json()["status"], "success")

        # 3. POST /api/jarvis/infra/route
        route_res = client.post(
            "/api/jarvis/infra/route",
            json={"task_type": "coding"},
            headers=headers
        )
        self.assertEqual(route_res.status_code, 200)
        self.assertEqual(route_res.json()["routing"]["chosen_model"], "qwen2.5-coder:7b")


if __name__ == "__main__":
    unittest.main()
