"""
Unit Tests for 3-Stage Autonomous Content Pipeline (Global Wave / Zenvia Media)
Verifies:
1. Stage 1 Production Draft logic & metadata
2. Stage 2 Quality Control (QC) technical measurements vs AI simulation separation
3. Stage 3 Staging & Publishing requiring Level 3 confirmation
4. FastAPI Content Pipeline Endpoints
"""

import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from engine.content_pipeline import content_pipeline
from core_jarvis.permission_guard import PermissionLevel
from web.server import app, LOCAL_SESSION_TOKEN

WORKSPACE_DIR = Path(__file__).resolve().parent.parent

class TestContentPipeline(unittest.TestCase):

    def test_stage_1_production_structure(self):
        # Test draft production structure with mocked script engine
        mock_script = {
            "title": "Yapay Zeka Devrimi",
            "scenes": [
                {"scene_num": 0, "narration": "Hook scene", "visual_prompt": "ai robot"},
                {"scene_num": 1, "narration": "Second scene", "visual_prompt": "coding"}
            ]
        }
        with patch("engine.script_engine.generate_script", return_value=mock_script):
            res = content_pipeline.stage_1_produce_draft(
                topic="Yapay Zeka",
                target_duration="30s",
                orientation="vertical"
            )
            self.assertTrue(res["success"])
            self.assertEqual(res["stage"], "production")
            self.assertEqual(res["scenes_count"], 2)
            self.assertEqual(res["title"], "Yapay Zeka Devrimi")

    def test_stage_2_qc_missing_file(self):
        res = content_pipeline.stage_2_quality_control("non_existent_video.mp4", {})
        self.assertFalse(res["success"])
        self.assertFalse(res["qc_passed"])
        self.assertIn("bulunamadı", res["error"])

    def test_stage_2_qc_ai_prediction_distinction(self):
        # Create a mock existing file
        temp_video = WORKSPACE_DIR / "temp_qc_mock.mp4"
        temp_video.write_bytes(b"dummy video bytes for test")
        try:
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = '{"format": {"duration": "35.5"}, "streams": [{"codec_type": "video", "width": 1080, "height": 1920}, {"codec_type": "audio"}]}'

                res = content_pipeline.stage_2_quality_control(str(temp_video), {})
                self.assertTrue(res["success"])
                self.assertTrue(res["qc_passed"])
                self.assertIn("technical_measurements", res)
                self.assertEqual(res["technical_measurements"]["width"], 1080)
                self.assertEqual(res["technical_measurements"]["height"], 1920)
                self.assertTrue(res["technical_measurements"]["has_audio_track"])

                # Verify explicit separation of AI simulation vs technical reality
                self.assertIn("ai_predictive_simulation", res)
                self.assertEqual(res["ai_predictive_simulation"]["type"], "YAPAY ZEKA TAHMİNİ (Simülasyon)")
                self.assertIn("disclaimer", res["ai_predictive_simulation"])
        finally:
            if temp_video.exists():
                temp_video.unlink()

    def test_stage_3_publish_requires_confirmation(self):
        # Without confirmation -> must be blocked and staged
        res_unconfirmed = content_pipeline.stage_3_prepare_and_publish(
            video_path="output/test.mp4",
            title="Harika Video #Shorts",
            description="Açıklama",
            tags=["yapayzeka", "shorts"],
            confirmed_by_user=False
        )
        self.assertFalse(res_unconfirmed["success"])
        self.assertEqual(res_unconfirmed["status"], "awaiting_confirmation")
        self.assertTrue(res_unconfirmed["requires_confirmation"])
        self.assertEqual(res_unconfirmed["staging_package"]["permission_level"], PermissionLevel.LEVEL_3_CONFIRMED)

    def test_stage_3_publish_with_confirmation(self):
        with patch("engine.uploader_youtube.upload_short_video") as mock_upload:
            mock_upload.return_value = {"status": "success", "video_id": "yt_123", "video_url": "https://youtu.be/yt_123"}
            res_confirmed = content_pipeline.stage_3_prepare_and_publish(
                video_path="output/test.mp4",
                title="Harika Video #Shorts",
                description="Açıklama",
                tags=["yapayzeka", "shorts"],
                confirmed_by_user=True
            )
            self.assertTrue(res_confirmed["success"])
            self.assertEqual(res_confirmed["status"], "published")
            self.assertEqual(res_confirmed["upload_result"]["video_id"], "yt_123")

    def test_api_content_pipeline_endpoints(self):
        client = TestClient(app)
        headers = {"X-Local-Token": LOCAL_SESSION_TOKEN}

        # 1. POST /api/jarvis/content/publish without confirmation -> 200 with awaiting_confirmation status
        pub_res = client.post(
            "/api/jarvis/content/publish",
            json={"video_path": "output/test.mp4", "title": "Test Title", "confirm": False},
            headers=headers
        )
        self.assertEqual(pub_res.status_code, 200)
        self.assertEqual(pub_res.json()["result"]["status"], "awaiting_confirmation")


if __name__ == "__main__":
    unittest.main()
