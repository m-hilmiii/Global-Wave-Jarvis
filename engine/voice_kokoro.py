"""
Global Wave - Kokoro ONNX Local TTS Engine
100 percent offline, studio-quality neural voice synthesis running on ONNX Runtime.
No GPU or cloud connection required (uses ~300MB RAM, CPU-optimized).
"""
import os
import soundfile as sf
from kokoro_onnx import Kokoro

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models", "kokoro")
ONNX_MODEL_PATH = os.path.join(MODELS_DIR, "kokoro-v1.0.onnx")
VOICES_BIN_PATH = os.path.join(MODELS_DIR, "voices-v1.0.bin")

_KOKORO_INSTANCE = None

PERSONA_VOICE_MAP = {
    "us_hustler": "am_adam",
    "uk_critic": "bm_george",
    "de_engineer": "am_michael",
    "jp_zenmaster": "af_heart",
    "br_socialite": "af_bella",
}

def get_kokoro() -> Kokoro:
    global _KOKORO_INSTANCE
    if _KOKORO_INSTANCE is None:
        if not os.path.exists(ONNX_MODEL_PATH) or not os.path.exists(VOICES_BIN_PATH):
            raise FileNotFoundError(f"Kokoro model files not found in {MODELS_DIR}")
        _KOKORO_INSTANCE = Kokoro(ONNX_MODEL_PATH, VOICES_BIN_PATH)
    return _KOKORO_INSTANCE

def synthesize_kokoro_chunk(text: str, voice_name: str, out_wav: str, speed: float = 1.05) -> float:
    clean_text = text.strip()
    if not clean_text:
        clean_text = "..."
        
    kokoro = get_kokoro()
    lang = "en-gb" if voice_name.startswith("b") else "en-us"
    
    samples, sample_rate = kokoro.create(
        clean_text,
        voice=voice_name,
        speed=speed,
        lang=lang
    )
    
    os.makedirs(os.path.dirname(out_wav), exist_ok=True)
    sf.write(out_wav, samples, sample_rate)
    
    duration = len(samples) / float(sample_rate)
    return duration

def generate_scene_audios_kokoro(scenes: list, persona_id: str, task_temp_dir: str) -> list:
    voice_name = PERSONA_VOICE_MAP.get(persona_id, "am_adam")
    results = []
    
    for i, sc in enumerate(scenes):
        out_wav = os.path.join(task_temp_dir, f"audio_scene_{i}.wav")
        text = sc.get("text", "").strip()
        dur = synthesize_kokoro_chunk(text, voice_name, out_wav, speed=1.05)
        
        results.append({
            "scene_id": sc.get("scene_id", i),
            "mp3_path": out_wav,
            "duration": dur,
            "text": text,
            "visual_keyword": sc.get("visual_keyword", "cinematic dark vertical video")
        })
        
    return results