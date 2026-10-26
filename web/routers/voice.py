"""
JARVIS Voice, Speech-to-Text & Neural Synthesis Router
Handles Faster-Whisper Turkish STT, Edge-TTS/gTTS AhmetNeural synthesis, and voice status.
"""

import asyncio
import os
import uuid
import tempfile
from pathlib import Path
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from core_jarvis.tools.voice_tool import voice_tool
from core_jarvis.logger import get_logger
from web.schemas import VoiceSpeakRequest, VoiceCommandRequest

logger = get_logger("Jarvis.Router.Voice")
router = APIRouter(prefix="/api/jarvis", tags=["Voice & Speech"])

# Single Whisper concurrency lock
TRANSCRIBE_SEMAPHORE = asyncio.Semaphore(1)
MAX_AUDIO_BYTES = 25 * 1024 * 1024
TEMP_WORKSPACE = Path(__file__).resolve().parent.parent.parent / ".jarvis_cache" / "temp_audio"
TEMP_WORKSPACE.mkdir(parents=True, exist_ok=True)


@router.post("/voice/speak")
async def api_jarvis_voice_speak(payload: VoiceSpeakRequest):
    """Synthesizes text into high-fidelity Turkish speech using Edge-TTS AhmetNeural."""
    text = payload.text.strip()
    if not text:
        return JSONResponse({"status": "error", "message": "Metin gereklidir."}, status_code=status.HTTP_400_BAD_REQUEST)

    res = await run_in_threadpool(voice_tool.synthesize_speech, text=text, voice_name=payload.voice, speed=payload.speed)
    return {
        "status": "success" if res.get("success") else "error",
        "audio_url": res.get("audio_url"),
        "speech": res
    }


@router.post("/voice/command")
async def api_jarvis_voice_command(payload: VoiceCommandRequest):
    """Processes an incoming voice transcript as a high-priority voice command."""
    text = payload.text.strip()
    if not text:
        return JSONResponse({"status": "error", "message": "Metin gereklidir."}, status_code=status.HTTP_400_BAD_REQUEST)

    res = await run_in_threadpool(voice_tool.process_voice_command, user_input=text, voice_name=payload.voice)
    return {"status": "success", "voice_response": res}


@router.get("/voice/status")
async def api_jarvis_voice_status():
    """Returns local TTS/STT engine health and available voices."""
    res = await run_in_threadpool(voice_tool.get_status)
    return {"status": "success", "voice_status": res}


@router.post("/transcribe")
async def api_jarvis_transcribe(request: Request):
    """Transcribes an uploaded audio file using local Faster-Whisper Turkish model."""
    cl_header = request.headers.get("content-length")
    if cl_header:
        try:
            if int(cl_header) > MAX_AUDIO_BYTES:
                return JSONResponse({"status": "error", "message": "Ses dosyası boyutu 25MB sınırını aşamaz."}, status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        except ValueError:
            pass

    if TRANSCRIBE_SEMAPHORE.locked():
        return JSONResponse({"status": "error", "message": "Sunucu şu anda başka bir ses işliyor. Lütfen birkaç saniye sonra tekrar deneyin."}, status_code=status.HTTP_429_TOO_MANY_REQUESTS)

    content = bytearray()
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        audio_file = form.get("file")
        if not audio_file:
            return JSONResponse({"status": "error", "message": "Ses dosyası bulunamadı."}, status_code=status.HTTP_400_BAD_REQUEST)
        while True:
            chunk = await audio_file.read(64 * 1024)
            if not chunk:
                break
            content.extend(chunk)
            if len(content) > MAX_AUDIO_BYTES:
                return JSONResponse({"status": "error", "message": "Ses dosyası boyutu 25MB sınırını aşamaz."}, status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
    else:
        async for chunk in request.stream():
            content.extend(chunk)
            if len(content) > MAX_AUDIO_BYTES:
                return JSONResponse({"status": "error", "message": "Ses dosyası boyutu 25MB sınırını aşamaz."}, status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    if not content or len(content) < 16:
        return JSONResponse({"status": "error", "message": "Ses içeriği boş veya geçersiz."}, status_code=status.HTTP_400_BAD_REQUEST)

    # Validate audio magic bytes (WebM, WAV, OGG, MP3, M4A)
    is_valid_audio = (
        content.startswith(b"\x1a\x45\xdf\xa3")
        or content.startswith(b"RIFF")
        or content.startswith(b"OggS")
        or content.startswith(b"ID3")
        or (content[0:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"))
        or (len(content) > 12 and content[4:8] == b"ftyp")
    )
    if not is_valid_audio:
        return JSONResponse({"status": "error", "message": "Desteklenmeyen veya geçersiz ses biçimi."}, status_code=status.HTTP_400_BAD_REQUEST)

    async with TRANSCRIBE_SEMAPHORE:
        temp_file = TEMP_WORKSPACE / f"voice_{uuid.uuid4().hex[:8]}.webm"
        try:
            temp_file.write_bytes(content)

            def _do_transcribe(fpath: str) -> str:
                from engine.subtitle_whisper import get_whisper_model
                model = get_whisper_model()
                prompt_text = "Jarvis, Mücahit, Hilmi, WhatsApp, YouTube, Gönder, İptal, Onayla, Ses, Durdur, Başlat"
                segments, _ = model.transcribe(
                    fpath,
                    language="tr",
                    initial_prompt=prompt_text,
                    beam_size=5,
                    vad_filter=True
                )
                return " ".join([s.text for s in segments]).strip()

            transcript = await run_in_threadpool(_do_transcribe, str(temp_file))
            return {"status": "success", "transcript": transcript}
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return JSONResponse({"status": "error", "message": f"Deşifre hatası: {e}"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception as del_err:
                    logger.debug(f"Temp audio cleanup: {del_err}")
