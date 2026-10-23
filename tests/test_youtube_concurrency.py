"""
Global Wave - YouTube Concurrency, Deadlock & Slot Reservation Tests
Tests that upload_short_video does not deadlock under threading.RLock,
atomically reserves daily slots, and properly rolls back on errors.
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import tempfile
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import engine.uploader_youtube as yt_module


class TestYouTubeConcurrency(unittest.TestCase):
    def setUp(self):
        # Create a temporary history file so tests never touch real data
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.temp_history = Path(self.temp_dir.name) / "upload_history.json"
        self.original_history_file = yt_module.HISTORY_FILE
        yt_module.HISTORY_FILE = self.temp_history

        # Create dummy video file
        self.dummy_video = Path(self.temp_dir.name) / "dummy.mp4"
        self.dummy_video.write_bytes(b"FakeVideoContent")

    def tearDown(self):
        yt_module.HISTORY_FILE = self.original_history_file
        import gc; gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    @patch("engine.uploader_youtube.get_youtube_service")
    def test_upload_short_video_does_not_deadlock(self, mock_service_func):
        # Mock YouTube API response
        mock_service = MagicMock()
        mock_req = MagicMock()
        mock_req.next_chunk.return_value = (None, {"id": "test_video_123", "snippet": {"title": "Test Title"}})
        mock_service.videos().insert.return_value = mock_req
        mock_service_func.return_value = mock_service

        # Call upload_short_video: Must complete immediately and NOT deadlock!
        result = yt_module.upload_short_video(
            video_path=str(self.dummy_video),
            title="Deadlock Test",
            privacy_status="private"
        )
        self.assertEqual(result.get("status"), "success")
        self.assertEqual(result.get("video_id"), "test_video_123")

        # Verify history file records slot
        can_upload, count = yt_module.check_daily_upload_limit(max_per_day=4)
        self.assertEqual(count, 1)

    @patch("engine.uploader_youtube.get_youtube_service")
    def test_concurrent_reservations_respect_limit(self, mock_service_func):
        mock_service = MagicMock()
        mock_req = MagicMock()
        mock_req.next_chunk.return_value = (None, {"id": "v_id", "snippet": {}})
        mock_service.videos().insert.return_value = mock_req
        mock_service_func.return_value = mock_service

        # Attempt to upload 6 videos concurrently when limit is 4
        success_count = 0
        error_count = 0

        def try_upload(idx):
            try:
                yt_module.upload_short_video(
                    video_path=str(self.dummy_video),
                    title=f"Concurrent Video {idx}"
                )
                return True
            except RuntimeError:
                return False

        with ThreadPoolExecutor(max_workers=6) as executor:
            results = list(executor.map(try_upload, range(6)))

        success_count = sum(1 for r in results if r)
        error_count = sum(1 for r in results if not r)

        # Exactly 4 must succeed and 2 must be rejected by daily quota
        self.assertEqual(success_count, 4)
        self.assertEqual(error_count, 2)

    @patch("engine.uploader_youtube.get_youtube_service")
    def test_failed_upload_releases_slot(self, mock_service_func):
        # Simulate upload error
        mock_service = MagicMock()
        mock_req = MagicMock()
        mock_req.next_chunk.side_effect = RuntimeError("Network connection reset")
        mock_service.videos().insert.return_value = mock_req
        mock_service_func.return_value = mock_service

        # Upload attempt must fail
        with self.assertRaises(RuntimeError):
            yt_module.upload_short_video(
                video_path=str(self.dummy_video),
                title="Failing Video"
            )

        # The slot should have been released (active count remains 0)
        can_upload, count = yt_module.check_daily_upload_limit(max_per_day=4)
        self.assertEqual(count, 0)
        self.assertTrue(can_upload)


if __name__ == "__main__":
    unittest.main()
