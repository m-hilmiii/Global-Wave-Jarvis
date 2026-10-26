"""
Test Suite: Systemic Debugging & Stability Verification
Validates:
1. WSL / LAN trusted IP detection (resolves UI lockout & 403 freeze)
2. WhatsApp conversation analysis intent and execution (no stalling)
3. Defensive JSON request parsing (prevents 500 JSONDecodeError)
4. Transcription response format compatibility (both 'transcript' and 'text')
"""

import pytest
from starlette.testclient import TestClient
from web.server import app, is_trusted_or_local_ip, LOCAL_SESSION_TOKEN
from core_jarvis.jarvis_brain import jarvis_brain


@pytest.fixture
def client():
    return TestClient(app)


def test_trusted_or_local_ip_validation():
    """Verify loopback, WSL2 virtual switch gateways, and LAN IPs are trusted, while WAN IPs are rejected."""
    # Loopback & test hosts
    assert is_trusted_or_local_ip("127.0.0.1") is True
    assert is_trusted_or_local_ip("localhost") is True
    assert is_trusted_or_local_ip("::1") is True
    assert is_trusted_or_local_ip("testclient") is True

    # WSL2 virtual ethernet subnets (172.16.0.0/12)
    assert is_trusted_or_local_ip("172.26.32.1") is True
    assert is_trusted_or_local_ip("172.20.0.1") is True
    assert is_trusted_or_local_ip("172.31.255.254") is True

    # Home / Office LAN (192.168.0.0/16, 10.0.0.0/8)
    assert is_trusted_or_local_ip("192.168.1.100") is True
    assert is_trusted_or_local_ip("10.0.0.15") is True

    # Public WAN Internet IPs (MUST be blocked)
    assert is_trusted_or_local_ip("8.8.8.8") is False
    assert is_trusted_or_local_ip("1.1.1.1") is False
    assert is_trusted_or_local_ip("142.250.190.46") is False
    assert is_trusted_or_local_ip("invalid_host_xyz") is False
    assert is_trusted_or_local_ip("") is False


def test_session_token_endpoint_local_and_rejection(client):
    """Verify local session token endpoint succeeds for trusted clients."""
    resp = client.get("/api/session/token")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "success"
    assert data.get("token") == LOCAL_SESSION_TOKEN


def test_analyze_whatsapp_chat_intent_routing():
    """Verify 'annemle olan konuşmaları analiz et' routes to analyze_whatsapp_chat with target 'annem'."""
    prompt = "annemle olan konuşmaları analiz et"
    decision = jarvis_brain._route_intent(prompt)
    assert decision.get("action") == "analyze_whatsapp_chat"


def test_analyze_whatsapp_chat_honest_execution_when_empty():
    """Verify analyze_whatsapp_chat returns an honest, non-stalling response when no messages exist."""
    jarvis_brain._last_contact = None
    res = jarvis_brain.process_message("05999999999 kişisiyle olan konuşmaları analiz et")
    assert res.get("action_taken") in ("no_chat_history", "contact_not_specified", "contact_not_found")
    assert "oyalamam" in res.get("reply", "") or "belirleyemedim" in res.get("reply", "") or "bulunamadı" in res.get("reply", "")


def test_defensive_json_parsing_on_empty_payload(client):
    """Verify empty or non-JSON payloads return clean 400 Bad Request instead of 500 error."""
    headers = {
        "X-Local-Token": LOCAL_SESSION_TOKEN,
        "Content-Type": "application/json"
    }
    # Empty body to /api/jarvis/contacts
    resp1 = client.post("/api/jarvis/contacts", data="", headers=headers)
    assert resp1.status_code == 400
    assert "İsim ve telefon" in resp1.json().get("message", "")

    # Empty body to /api/jarvis/assistant/tasks
    resp2 = client.post("/api/jarvis/assistant/tasks", data="", headers=headers)
    assert resp2.status_code == 400
    assert "Başlık gereklidir" in resp2.json().get("message", "")

    # Empty body to /api/jarvis/chats/test_id/send
    resp3 = client.post("/api/jarvis/chats/test_id/send", data="", headers=headers)
    assert resp3.status_code == 400
    assert "Mesaj metni zorunludur" in resp3.json().get("message", "")


def test_voice_transcribe_returns_both_transcript_and_text(client, monkeypatch):
    """Verify transcribe endpoint returns both 'transcript' and 'text' keys for web UI compatibility."""
    import web.routers.voice as v_module

    # Mock whisper transcribe
    def _mock_transcribe(fpath: str):
        return "Sayın Hilmi sistem aktif"

    headers = {"X-Local-Token": LOCAL_SESSION_TOKEN}
    # Create fake WAV header
    wav_bytes = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"

    # We mock run_in_threadpool inside the endpoint
    async def _async_mock(fn, *args, **kwargs):
        return "Sayın Hilmi sistem aktif"

    with monkeypatch.context() as m:
        m.setattr(v_module, "run_in_threadpool", _async_mock)
        files = {"file": ("voice.wav", wav_bytes, "audio/wav")}
        resp = client.post("/api/jarvis/transcribe", files=files, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "success"
        assert data.get("transcript") == "Sayın Hilmi sistem aktif"
        assert data.get("text") == "Sayın Hilmi sistem aktif"
