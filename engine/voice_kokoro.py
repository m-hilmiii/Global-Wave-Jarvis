"""
Global Wave - Kokoro ONNX Local TTS Engine
100 percent offline, studio-quality neural voice synthesis running on ONNX Runtime.
No GPU or cloud connection required (uses ~300MB RAM, CPU-optimized).

NOTE: Kokoro-82M strictly supports English ('en-us', 'en-gb') and experimental Japanese.
It DOES NOT support Turkish phonetics. Attempting Turkish synthesis with Kokoro
results in English phonetic corruption. For Turkish, route to Neural Edge-TTS or Piper.
"""
import os
import soundfile as sf
from kokoro_onnx import Kokoro

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models", "kokoro")
ONNX_MODEL_PATH = os.path.join(MODELS_DIR, "kokoro-v1.0.onnx")
VOICES_BIN_PATH = os.path.join(MODELS_DIR, "voices-v1.0.bin")

_KOKORO_INSTANCE = None

SUPPORTED_PERSONAS = {
    "us_hustler": "am_adam",
    "uk_critic": "bm_george",
}

PERSONA_VOICE_MAP = {
    "us_hustler": "am_adam",
    "uk_critic": "bm_george",
}

SUPPORTED_LANGUAGES = {"en-us", "en-gb", "en", "ja"}

def is_kokoro_supported(persona_id: str, lang: str = None) -> bool:
    """Check if persona and language are legitimately supported by Kokoro-82M phonetics."""
    if lang:
        clean_lang = lang.lower().strip()
        if clean_lang.startswith("tr") or clean_lang.startswith("de") or clean_lang.startswith("es") or clean_lang.startswith("pt"):
            return False
        if clean_lang in SUPPORTED_LANGUAGES or clean_lang.startswith("en"):
            return True
    return persona_id in SUPPORTED_PERSONAS

def get_kokoro() -> Kokoro:
    global _KOKORO_INSTANCE
    if _KOKORO_INSTANCE is None:
        if not os.path.exists(ONNX_MODEL_PATH) or not os.path.exists(VOICES_BIN_PATH):
            raise FileNotFoundError(f"Kokoro model dosyaları bulunamadı: {MODELS_DIR}. models/kokoro/kokoro-v1.0.onnx ve voices-v1.0.bin gereklidir.")
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
    if not is_kokoro_supported(persona_id):
        raise ValueError(f"Kokoro-82M '{persona_id}' personasını veya bu dili desteklemez. Kokoro yalnızca İngilizce ve Japonca dillerini destekler. Türkçe ve diğer diller için Edge-TTS veya Piper kullanılmalıdır.")

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
            "visual_keyword": sc.get("visual_keyword", "cinematic dark vertical video"),
            "audio_meta": {
                "requested_engine": "kokoro",
                "actual_engine": "kokoro",
                "language": "en-US" if not voice_name.startswith("b") else "en-GB",
                "voice_id": voice_name,
                "fallback_used": False,
                "fallback_reason": None
            }
        })
        
    return results
