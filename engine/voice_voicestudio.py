"""
Global Wave & Jarvis - VoiceStudio Integration Module
High-fidelity local speech synthesis & voice cloning via VoiceStudio backend (:3900).

Features:
- Drop-in local TTS supporting 600+ languages including Turkish ('tr') and English ('en').
- Compatible with VoiceStudio's OpenAI speech endpoints (/v1/audio/speech).
- Support for custom cloned voice profiles (e.g. Jarvis voice persona).
- Completely offline and local (zero cloud dependency).
"""
import os
import requests
import subprocess
from typing import List, Dict, Any, Optional
from config.settings import load_settings, get_ffmpeg_bin, get_ffprobe_bin

DEFAULT_VOICESTUDIO_URL = "http://127.0.0.1:3900"

def get_voicestudio_url() -> str:
    settings = load_settings()
    return settings.get("voicestudio_host", DEFAULT_VOICESTUDIO_URL).rstrip("/")

def is_voicestudio_available(timeout_s: float = 2.0) -> bool:
    """Checks whether the VoiceStudio service is running and responsive."""
    url = f"{get_voicestudio_url()}/health"
    try:
        resp = requests.get(url, timeout=timeout_s)
        if resp.status_code == 200:
            return True
        # If still starting up (503 with progress)
        if resp.status_code == 503 and "starting" in resp.text:
            return True
        return False
    except Exception:
        return False

def get_audio_duration_fast(file_path: str) -> float:
    """Accurately measure duration of synthesized audio using ffprobe or wave."""
    ffprobe_bin = get_ffprobe_bin()
    cmd = [
        ffprobe_bin, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
        return float(res.stdout.strip())
    except Exception:
        if str(file_path).lower().endswith(".wav"):
            try:
                import wave
                with wave.open(file_path, "rb") as wf:
                    return wf.getnframes() / float(wf.getframerate())
            except Exception:
                pass
        return 0.0

def synthesize_chunk_voicestudio(
    text: str,
    out_path: str,
    voice: str = "alloy",
    model: str = "tts-1",
    language: Optional[str] = None,
    speed: float = 1.0,
    timeout_s: int = 60
) -> bool:
    """
    Synthesize speech using VoiceStudio's OpenAI-compatible speech endpoint.
    Saves audio to `out_path` (.mp3 or .wav).
    """
    base_url = get_voicestudio_url()
    url = f"{base_url}/v1/audio/speech"

    response_format = "wav" if out_path.lower().endswith(".wav") else "mp3"
    
    payload = {
        "model": model,
        "input": text,
        "voice": voice or "alloy",
        "response_format": response_format,
        "speed": float(speed)
    }
    if language:
        payload["language"] = language

    try:
        resp = requests.post(url, json=payload, timeout=timeout_s, stream=True)
        if resp.status_code == 200:
            with open(out_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
        else:
            print(f"[VOICESTUDIO WARN] API responded with {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"[VOICESTUDIO ERR] Failed to connect to VoiceStudio ({url}): {e}")
        return False

def generate_scene_audios_voicestudio(
    scenes: List[Dict[str, Any]],
    voice: str,
    task_temp_dir: str,
    language: str = "tr",
    audio_meta: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Batch synthesize audio for video scenes using local VoiceStudio engine.
    """
    results = []
    meta = audio_meta or {
        "requested_engine": "voicestudio",
        "actual_engine": "voicestudio",
        "voice_id": voice or "default",
        "language": language,
        "fallback_used": False,
        "fallback_reason": None
    }

    resolved_voice = voice or "alloy"

    for i, sc in enumerate(scenes):
        sc_id = sc.get("scene_id", i)
        text = sc.get("text", "").strip() or "..."
        out_audio = os.path.join(task_temp_dir, f"audio_scene_{i}.mp3")

        success = synthesize_chunk_voicestudio(
            text=text,
            out_path=out_audio,
            voice=resolved_voice,
            language=language
        )

        if not success:
            raise RuntimeError(f"VoiceStudio sahne {i} ('{text[:30]}...') icin ses uretemedi.")

        dur = get_audio_duration_fast(out_audio)
        results.append({
            "scene_id": sc_id,
            "mp3_path": out_audio,
            "audio_path": out_audio,
            "duration": dur,
            "text": text,
            "visual_keyword": sc.get("visual_keyword", "cinematic technology"),
            "audio_meta": dict(meta)
        })

    return results
