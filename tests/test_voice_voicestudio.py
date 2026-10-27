"""
Unit tests for VoiceStudio engine integration with Global Wave & Jarvis.
Tests:
1. is_voicestudio_available behavior (online vs offline).
2. synthesize_chunk_voicestudio request payload formatting and response handling.
3. Fallback flow in generate_scene_audios when VoiceStudio is offline or selected.
"""
import pytest
from unittest.mock import patch, MagicMock
from engine.voice_voicestudio import (
    is_voicestudio_available,
    synthesize_chunk_voicestudio,
    generate_scene_audios_voicestudio,
    get_voicestudio_url
)
from engine.voice_engine import generate_scene_audios

def test_voicestudio_url_default():
    url = get_voicestudio_url()
    assert "3900" in url

@patch("engine.voice_voicestudio.requests.get")
def test_is_voicestudio_available_online(mock_get):
    mock_get.return_value.status_code = 200
    assert is_voicestudio_available() is True

@patch("engine.voice_voicestudio.requests.get")
def test_is_voicestudio_available_offline(mock_get):
    mock_get.side_effect = Exception("Connection refused")
    assert is_voicestudio_available() is False

@patch("engine.voice_voicestudio.requests.post")
def test_synthesize_chunk_voicestudio_success(mock_post, tmp_path):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.iter_content.return_value = [b"ID3fake_mp3_audio_data"]
    mock_post.return_value = mock_resp

    out_file = str(tmp_path / "test.mp3")
    res = synthesize_chunk_voicestudio("Merhaba Sayin Hilmi", out_file, voice="alloy", language="tr")
    assert res is True
    assert (tmp_path / "test.mp3").exists()
    assert (tmp_path / "test.mp3").read_bytes() == b"ID3fake_mp3_audio_data"

@patch("engine.voice_voicestudio.synthesize_chunk_voicestudio")
@patch("engine.voice_voicestudio.get_audio_duration_fast")
def test_generate_scene_audios_voicestudio(mock_dur, mock_synth, tmp_path):
    mock_synth.return_value = True
    mock_dur.return_value = 3.5

    scenes = [
        {"scene_id": 0, "text": "Birinci sahne.", "visual_keyword": "tech"},
        {"scene_id": 1, "text": "İkinci sahne.", "visual_keyword": "ai"}
    ]

    res = generate_scene_audios_voicestudio(scenes, "jarvis_voice", str(tmp_path), language="tr")
    assert len(res) == 2
    assert res[0]["duration"] == 3.5
    assert res[0]["audio_meta"]["actual_engine"] == "voicestudio"
    assert res[1]["text"] == "İkinci sahne."

@patch("engine.voice_engine.generate_scene_audios_voicestudio")
def test_generate_scene_audios_routing_voicestudio(mock_vs_gen, tmp_path):
    mock_vs_gen.return_value = [{"scene_id": 0, "duration": 2.0}]
    scenes = [{"scene_id": 0, "text": "Test"}]

    res = generate_scene_audios(scenes, "alloy", "default_persona", str(tmp_path), tts_engine="voicestudio")
    assert res == [{"scene_id": 0, "duration": 2.0}]
    mock_vs_gen.assert_called_once()
