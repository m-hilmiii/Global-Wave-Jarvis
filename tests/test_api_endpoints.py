"""
Global Wave - API Security Integration Tests
Tests HTTP layer authentication, rejection of unauthorized access,
and input validation using FastAPI TestClient.
"""

import unittest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from web.server import app, LOCAL_SESSION_TOKEN


class TestApiSecurityEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.auth_headers = {"X-Local-Token": LOCAL_SESSION_TOKEN}

    def test_unauthorized_api_access_blocked(self):
        # 1. GET /api/config without token must return 401
        res = self.client.get("/api/config")
        self.assertEqual(res.status_code, 401)
        self.assertIn("Yetkilendirme hatas", res.json().get("message", ""))

        # 2. POST /api/generate without token must return 401
        res = self.client.post("/api/generate", json={"topic": "Test"})
        self.assertEqual(res.status_code, 401)

    def test_session_token_endpoint_succeeds(self):
        # /api/session/token is the handshake endpoint
        res = self.client.get("/api/session/token")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("token"), LOCAL_SESSION_TOKEN)

    def test_authorized_api_access_succeeds(self):
        # /api/config with valid X-Local-Token must return 200
        res = self.client.get("/api/config", headers=self.auth_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("settings", data)
        self.assertIn("personas", data)

    def test_generate_rejects_empty_topic(self):
        # Empty topic must return 400
        res = self.client.post("/api/generate", json={"topic": "   "}, headers=self.auth_headers)
        self.assertEqual(res.status_code, 400)
        self.assertIn("boş bırakılamaz", res.json().get("message", ""))

    def test_draft_confirm_requires_draft_id(self):
        # Confirming without explicit draft_id must return 400
        res = self.client.post("/api/jarvis/draft/confirm", json={}, headers=self.auth_headers)
        self.assertEqual(res.status_code, 400)
        self.assertIn("taslak kimliği", res.json().get("message", ""))

    def test_transcribe_rejects_invalid_audio_bytes(self):
        # Uploading non-audio file must return 400
        fake_binary = b"MZ\x90\x00\x03\x00\x00\x00FakePEHeaderFile"
        res = self.client.post(
            "/api/jarvis/transcribe",
            content=fake_binary,
            headers={**self.auth_headers, "Content-Type": "audio/webm"}
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Desteklenmeyen veya geçersiz", res.json().get("message", ""))


    def test_legitimate_local_origin_accepted(self):
        # Local origin http://127.0.0.1:8000 must pass origin filter
        res = self.client.post(
            "/api/generate",
            json={"topic": "   "},
            headers={**self.auth_headers, "Origin": "http://127.0.0.1:8000"}
        )
        # Must pass origin validation without 403 and reach endpoint logic (400 for empty topic)
        self.assertEqual(res.status_code, 400)
        self.assertIn("boş bırakılamaz", res.json().get("message", ""))

    def test_external_cross_origin_rejected(self):
        # External cross-origin request must be strictly rejected with 403
        res = self.client.post(
            "/api/generate",
            json={"topic": "Test"},
            headers={**self.auth_headers, "Origin": "http://malicious-external-site.com"}
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("Forbidden: Cross-origin request rejected.", res.json().get("message", ""))


if __name__ == "__main__":
    unittest.main()
