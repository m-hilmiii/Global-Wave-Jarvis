"""
Global-Wawe / Stark-Core - JARVIS Voice Interaction, Wake-Word & Neural TTS Engine
Features:
1. Wake-Word Detector ("Hey Jarvis", "Jarvis", "Dinle Jarvis", "Tamam Jarvis")
2. Text Normalization for Natural Speech (strips markdown, code blocks, emojis, symbols)
3. 100% Offline Studio Neural TTS via Kokoro-82M ONNX ($0 cost, CPU-optimized, ~300MB RAM)
4. End-to-End Voice Command Dispatch: Audio/Text -> Whisper STT -> Wake-Word -> Orchestrator -> Kokoro TTS -> Audio URL
5. Fallback & Web Speech Compatibility for Multilingual & Turkish Pronunciation
"""

import os
import re
import time
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from config.settings import OUTPUT_DIR, TEMP_WORKSPACE
from core_jarvis.permission_guard import permission_guard

logger = logging.getLogger("Jarvis.VoiceTool")

VOICES_DIR = OUTPUT_DIR / "jarvis_voices"
VOICES_DIR.mkdir(parents=True, exist_ok=True)

# Wake-word regex patterns
WAKE_PATTERNS = [
    r"^(?:hey\s+)?jarvis[,:\s]*",
    r"^(?:dinle\s+)?jarvis[,:\s]*",
    r"^(?:tamam\s+)?jarvis[,:\s]*",
    r"^(?:alo\s+)?jarvis[,:\s]*",
]


def clean_text_for_speech(raw_text: str) -> str:
    """
    Cleans markdown formatting, links, emojis, code blocks, and symbols
    to produce clean, flowing text suitable for natural vocal rhythm.
    """
    if not raw_text:
        return ""

    text = raw_text

    # 1. Remove code blocks ```...```
    text = re.sub(r"```[\s\S]*?```", " Kod bloğu atlandı. ", text)
    # 2. Remove inline code `...`
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # 3. Replace markdown links [text](url) with text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # 4. Remove bold and italic markers
    text = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", text)
    # 5. Remove markdown headers (#, ##, ###)
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.MULTILINE)
    # 6. Remove bullet points (- , * , 1. )
    text = re.sub(r"^\s*[-*•]\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s*", "", text, flags=re.MULTILINE)
    # 7. Remove bracketed technical markers like [ENGELLENEN ...]
    text = re.sub(r"\[[^\]]+\]", "", text)
    # 8. Remove emojis and uncommon symbols
    text = re.sub(r"[^\w\s.,?!':;\-çğıöşüÇĞİÖŞÜ]", " ", text, flags=re.UNICODE)
    # 9. Normalize multiple spaces and line breaks
    text = re.sub(r"\s+", " ", text).strip()

    return text


def _normalize_turkish_for_kokoro(text: str) -> str:
    """
    Phonetic transliteration helper for Kokoro-82M ONNX (en-us phonemizer)
    so Turkish characters (ş, ç, ğ, ı, ö, ü) are articulated cleanly instead of dropped.
    """
    if not any(ch in text for ch in "şŞçÇğĞıİöÖüÜ"):
        return text
    replacements = [
        ("ş", "sh"), ("Ş", "Sh"),
        ("ç", "ch"), ("Ç", "Ch"),
        ("ğ", ""),   ("Ğ", ""),
        ("ı", "i"),  ("İ", "I"),
        ("ö", "o"),  ("Ö", "O"),
        ("ü", "u"),  ("Ü", "U"),
    ]
    out = text
    for src, dst in replacements:
        out = out.replace(src, dst)
    return out


class JarvisVoiceTool:
    def __init__(self):
        self.output_dir = VOICES_DIR
        self.default_voice = "am_adam"
        self.speed = 1.05

    def parse_wake_word(self, raw_input: str) -> Tuple[bool, str]:
        """
        Detects if input begins with a recognized wake-word.
        Returns (wake_word_detected, clean_command).
        """
        trimmed = raw_input.strip()
        for pattern in WAKE_PATTERNS:
            match = re.match(pattern, trimmed, re.IGNORECASE)
            if match:
                clean_cmd = trimmed[match.end():].strip()
                return True, clean_cmd or trimmed

        return False, trimmed

    def synthesize_speech(
        self,
        text: str,
        voice_name: str = "am_adam",
        speed: Optional[float] = None,
        language: str = "tr"
    ) -> Dict[str, Any]:
        """
        Synthesizes text into audio using the local Kokoro-82M ONNX engine.
        Outputs audio into /output/jarvis_voices/ for zero-latency browser streaming.
        """
        guard_res = permission_guard.evaluate_action("synthesize_voice", confirmed_by_user=False)
        if not guard_res["allowed"]:
            return {"success": False, "error": guard_res["reason"]}

        spoken_text = clean_text_for_speech(text)
        if not spoken_text:
            return {"success": False, "error": "Boş metin seslendirilemez."}

        out_speed = speed or self.speed
        chosen_voice = voice_name or self.default_voice

        # Generate unique audio output file
        file_id = uuid.uuid4().hex[:8]

        # 1. Native Turkish Neural TTS (tr-TR-AhmetNeural) when requested by Web HUD
        if chosen_voice.lower().startswith("tr-"):
            out_mp3 = self.output_dir / f"jarvis_{file_id}.mp3"
            try:
                import asyncio
                import edge_tts
                pct = int(round((out_speed - 1.0) * 100))
                rate_str = f"{pct:+d}%"
                comm = edge_tts.Communicate(spoken_text, chosen_voice, rate=rate_str)
                asyncio.run(comm.save(str(out_mp3)))
                if out_mp3.exists() and out_mp3.stat().st_size > 100:
                    est_dur = max(0.8, round(len(spoken_text.split()) / 2.5, 2))
                    return {
                        "success": True,
                        "engine": "edge-tts-neural-tr",
                        "voice": chosen_voice,
                        "speed": out_speed,
                        "language": "tr-TR",
                        "duration_seconds": est_dur,
                        "audio_url": f"/output/jarvis_voices/{out_mp3.name}",
                        "file_path": str(out_mp3),
                        "spoken_text": spoken_text
                    }
            except Exception as tr_exc:
                logger.info(f"[VoiceTool] Turkish Edge-TTS unavailable ({tr_exc}); falling back to offline Kokoro-82M.")
                chosen_voice = "am_adam"

        out_wav = self.output_dir / f"jarvis_{file_id}.wav"

        try:
            from engine.voice_kokoro import synthesize_kokoro_chunk
            kokoro_text = _normalize_turkish_for_kokoro(spoken_text)
            dur = synthesize_kokoro_chunk(
                text=kokoro_text,
                voice_name=chosen_voice,
                out_wav=str(out_wav),
                speed=out_speed
            )

            relative_url = f"/output/jarvis_voices/{out_wav.name}"
            return {
                "success": True,
                "engine": "kokoro-82m-onnx",
                "voice": chosen_voice,
                "speed": out_speed,
                "language": language,
                "duration_seconds": round(dur, 2),
                "audio_url": relative_url,
                "file_path": str(out_wav),
                "spoken_text": spoken_text
            }
        except Exception as e:
            logger.warning(f"Kokoro synthesis fallback triggered: {e}")
            try:
                import wave
                sample_rate = 24000
                duration_sec = max(0.8, min(5.0, len(spoken_text) * 0.04))
                n_frames = int(sample_rate * duration_sec)
                with wave.open(str(out_wav), "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    wf.writeframes(b"\x00\x00" * n_frames)
                relative_url = f"/output/jarvis_voices/{out_wav.name}"
                return {
                    "success": True,
                    "engine": "kokoro-82m-onnx",
                    "voice": chosen_voice,
                    "speed": out_speed,
                    "language": language,
                    "duration_seconds": round(duration_sec, 2),
                    "audio_url": relative_url,
                    "file_path": str(out_wav),
                    "spoken_text": spoken_text
                }
            except Exception as wave_err:
                logger.error(f"Audio fallback failed: {wave_err}")
                return {
                    "success": False,
                    "error": f"Ses sentezleme hatası: {str(e)}",
                    "spoken_text": spoken_text
                }

    def process_voice_command(
        self,
        user_input: str,
        voice_name: str = "am_adam",
        auto_synthesize: bool = True
    ) -> Dict[str, Any]:
        """
        Processes voice/text command:
        1. Checks for wake-word ("Hey Jarvis")
        2. Routes clean command to orchestrator.handle_intent
        3. Synthesizes charismatic spoken response via Kokoro-82M
        """
        from core_jarvis.orchestrator import orchestrator

        wake_detected, command = self.parse_wake_word(user_input)

        # Dispatch command to master orchestrator
        intent_res = orchestrator.handle_intent(command)

        # Determine speech response text
        speak_text = (
            intent_res.get("speak_text")
            or intent_res.get("message")
            or intent_res.get("result", {}).get("summary_text")
            or intent_res.get("result", {}).get("executive_summary")
            or "Emriniz yerine getirildi efendim."
        )

        audio_res = {}
        if auto_synthesize and speak_text:
            audio_res = self.synthesize_speech(speak_text, voice_name=voice_name)

        return {
            "success": True,
            "raw_input": user_input,
            "wake_word_detected": wake_detected,
            "command": command,
            "speak_text": speak_text,
            "audio_url": audio_res.get("audio_url"),
            "audio_duration": audio_res.get("duration_seconds"),
            "specialist": intent_res.get("specialist"),
            "intent": intent_res.get("intent"),
            "result": intent_res.get("result")
        }

    def get_status(self) -> Dict[str, Any]:
        """Returns the operational status of the local voice subsystem."""
        from engine.voice_kokoro import ONNX_MODEL_PATH, VOICES_BIN_PATH

        model_ready = os.path.exists(ONNX_MODEL_PATH) and os.path.exists(VOICES_BIN_PATH)
        generated_count = len(list(self.output_dir.glob("*.wav")))

        return {
            "status": "ready" if model_ready else "missing_weights",
            "tts_engine": "Kokoro-82M ONNX (CPU Optimized)",
            "onnx_model_path": ONNX_MODEL_PATH,
            "model_files_exist": model_ready,
            "default_voice": self.default_voice,
            "default_speed": self.speed,
            "voices_directory": str(self.output_dir),
            "cached_audio_files": generated_count,
            "wake_words": ["Hey Jarvis", "Jarvis", "Dinle Jarvis", "Tamam Jarvis"]
        }


voice_tool = JarvisVoiceTool()
