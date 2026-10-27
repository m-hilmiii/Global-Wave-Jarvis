"""
Unit Tests for JARVIS Multi-Modal Media Intelligence Engine
Verifies:
1. MediaAnalyst audio transcription & duration calculation.
2. MediaAnalyst photo inspection & technical metadata extraction.
3. MediaAnalyst video probe, audio transcription & scene analysis.
4. Brain Fast-Path Reflexes for voice notes, photos, and videos.
5. WhatsApp Daemon owner media flow for images and videos.
6. REST API endpoints for media analysis.
"""

import os
import json
import tempfile
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from core_jarvis.tools.media_analyst import media_analyst
from core_jarvis.jarvis_brain import jarvis_brain
from core_jarvis.whatsapp_daemon import whatsapp_daemon, WhatsAppDaemon
from web.server import app, LOCAL_SESSION_TOKEN


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-Local-Token": LOCAL_SESSION_TOKEN}


# ==========================================
# 1. MediaAnalyst Unit Tests
# ==========================================
def test_transcribe_audio_not_found():
    res = media_analyst.transcribe_audio("non_existent_audio_xyz.ogg")
    assert res["success"] is False
    assert "bulunamadı" in res["error"]


def test_transcribe_audio_test_mode(tmp_path):
    dummy_audio = tmp_path / "test_note.ogg"
    dummy_audio.write_bytes(b"dummy audio content")

    res = media_analyst.transcribe_audio(str(dummy_audio))
    assert res["success"] is True
    assert "Sayın Hilmi" in res["text"]
    assert res["duration_seconds"] > 0
    assert res["word_count"] > 0
    assert "summary" in res


def test_analyze_photo_not_found():
    res = media_analyst.analyze_photo("non_existent_photo_xyz.jpg")
    assert res["success"] is False
    assert "bulunamadı" in res["error"]


def test_analyze_photo_test_mode(tmp_path):
    dummy_img = tmp_path / "test_photo.jpg"
    dummy_img.write_bytes(b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xDB")

    res = media_analyst.analyze_photo(str(dummy_img))
    assert res["success"] is True
    assert "Görsel Analizi" in res["summary"]
    assert "metadata" in res


def test_analyze_video_not_found():
    res = media_analyst.analyze_video("non_existent_video_xyz.mp4")
    assert res["success"] is False
    assert "bulunamadı" in res["error"]


def test_analyze_video_test_mode(tmp_path):
    dummy_vid = tmp_path / "test_video.mp4"
    dummy_vid.write_bytes(b"dummy video data")

    res = media_analyst.analyze_video(str(dummy_vid))
    assert res["success"] is True
    assert res["duration_seconds"] > 0
    assert "resolution" in res
    assert "summary" in res


# ==========================================
# 2. Brain Reflex Routing Tests
# ==========================================
def test_brain_media_reflexes():
    # 1. Voice note reflex
    r1 = jarvis_brain.process_message("son ses kaydını dinle")
    assert r1["action_taken"] == "analyze_voice_note"

    r2 = jarvis_brain.process_message("babamın ses kaydında ne diyor")
    assert r2["action_taken"] == "analyze_voice_note"

    # 2. Image reflex
    r3 = jarvis_brain.process_message("son gelen fotoğrafı incele")
    assert r3["action_taken"] == "analyze_image_media"

    r4 = jarvis_brain.process_message("fotoğrafta ne var")
    assert r4["action_taken"] == "analyze_image_media"

    # 3. Video reflex
    r5 = jarvis_brain.process_message("son videoyu analiz et")
    assert r5["action_taken"] == "analyze_video_media"

    r6 = jarvis_brain.process_message("videoda ne diyor")
    assert r6["action_taken"] == "analyze_video_media"


# ==========================================
# 3. WhatsApp Daemon Owner Media Flow Tests
# ==========================================
def test_whatsapp_owner_image_and_video_handling(monkeypatch, tmp_path):
    sent_replies = []

    def mock_send(*args, **kwargs):
        target = args[1] if len(args) >= 3 else (args[0] if len(args) >= 1 else kwargs.get("phone", ""))
        msg = args[2] if len(args) >= 3 else (args[1] if len(args) >= 2 else kwargs.get("text", ""))
        sent_replies.append({"target": target, "msg": msg})

    monkeypatch.setattr(WhatsAppDaemon, "send_message", mock_send)
    monkeypatch.setattr(WhatsAppDaemon, "send_presence", lambda *a, **k: None)

    # Owner sends an image with no caption
    img_file = tmp_path / "owner_img.jpg"
    img_file.write_bytes(b"dummy")
    monkeypatch.setattr(media_analyst, "media_dir", tmp_path)

    media_info_img = {
        "media_type": "image",
        "file_name": "owner_img.jpg"
    }

    whatsapp_daemon._process_owner_message(
        jid="me@s.whatsapp.net",
        phone="me",
        text="",
        is_audio=False,
        raw_voice_text="",
        media_info=media_info_img,
        from_self_chat=True
    )

    assert len(sent_replies) == 1
    assert "Görsel" in sent_replies[0]["msg"]

    # Owner sends a video
    vid_file = tmp_path / "owner_vid.mp4"
    vid_file.write_bytes(b"dummy")

    media_info_vid = {
        "media_type": "video",
        "file_name": "owner_vid.mp4"
    }

    whatsapp_daemon._process_owner_message(
        jid="me@s.whatsapp.net",
        phone="me",
        text="Bu videoyu incele",
        is_audio=False,
        raw_voice_text="",
        media_info=media_info_vid,
        from_self_chat=True
    )

    assert len(sent_replies) == 2
    assert "Video" in sent_replies[1]["msg"]


# ==========================================
# 4. REST API Media Endpoints Tests
# ==========================================
def test_api_media_endpoints(client, auth_headers, tmp_path, monkeypatch):
    test_audio = tmp_path / "test.ogg"
    test_audio.write_bytes(b"audio")
    test_img = tmp_path / "test.jpg"
    test_img.write_bytes(b"img")
    test_vid = tmp_path / "test.mp4"
    test_vid.write_bytes(b"vid")

    # 1. Analyze Audio
    resp_audio = client.post(
        "/api/jarvis/media/analyze_audio",
        json={"file_path": str(test_audio)},
        headers=auth_headers
    )
    assert resp_audio.status_code == 200
    assert resp_audio.json()["status"] == "success"

    # 2. Analyze Image
    resp_img = client.post(
        "/api/jarvis/media/analyze_image",
        json={"file_path": str(test_img)},
        headers=auth_headers
    )
    assert resp_img.status_code == 200
    assert resp_img.json()["status"] == "success"

    # 3. Analyze Video
    resp_vid = client.post(
        "/api/jarvis/media/analyze_video",
        json={"file_path": str(test_vid)},
        headers=auth_headers
    )
    assert resp_vid.status_code == 200
    assert resp_vid.json()["status"] == "success"

    # 4. Recent Media list
    resp_recent = client.get("/api/jarvis/media/recent?type=all", headers=auth_headers)
    assert resp_recent.status_code == 200
    assert "results" in resp_recent.json()
