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
        out_wav = self.output_dir / f"jarvis_{file_id}.wav"

        try:
            from engine.voice_kokoro import synthesize_kokoro_chunk
            dur = synthesize_kokoro_chunk(
                text=spoken_text,
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
            logger.error(f"Kokoro synthesis failed: {e}")
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
