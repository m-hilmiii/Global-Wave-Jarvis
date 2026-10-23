"""
Global Wave - Multi-Language Localization & Translation Engine (Faz 8)
Translates and culturally adapts video scripts across languages using Ollama.
Ensures zero copyright overlap across channels by localizing idioms and cultural framing.
"""
import copy
import json
import requests
from config.settings import load_settings
from engine.personas import get_persona, PERSONAS

TRANSLATION_SYSTEM_PROMPT = """You are an elite, multi-lingual documentary localization specialist.
Your task is to translate and CULTURALLY LOCALIZE a video script into natural, captivating {target_language}.

RULES:
1. DO NOT do a word-for-word translation. Adapt the phrasing, idioms, and tension to feel 100% native.
2. PRESERVE THE EXACT JSON STRUCTURE:
   - Keep the same number of scenes.
   - Keep "scene_id" identical.
   - Keep "role" identical.
   - Keep "visual_keyword" in concise 1-2 English words suitable for stock footage search.
   - Translate and adapt the "text" field into captivating {target_language}.
   - Translate/adapt "topic" and "seamless_loop_word".
3. Maintain the appropriate tone: {tone}.
4. Target Audience: {target_audience}.
5. Output RAW JSON ONLY matching the original schema. No preamble, no markdown tags.
"""

def translate_script(script_data: dict, target_persona_id: str) -> dict:
    """
    Translates and culturally adapts a script JSON to match the target persona's native language and cultural nuances.
    """
    settings = load_settings()
    persona = get_persona(target_persona_id)
    model_name = settings.get("fast_model", "qwen3:8b")
    ollama_url = f"{settings['ollama_host'].rstrip('/')}/api/chat"

    prompt = TRANSLATION_SYSTEM_PROMPT.format(
        target_language=persona["language"],
        tone=persona["tone"],
        target_audience=persona["target_audience"]
    )

    user_payload = {
        "original_topic": script_data.get("topic", ""),
        "target_persona": persona["name"],
        "target_language": persona["language"],
        "script": script_data
    }

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}
        ],
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.5,
            "num_predict": 2500
        }
    }

    try:
        print(f"[TRANSLATE] Translating script to {persona['language']} ({persona['name']}) using {model_name}...")
        resp = requests.post(ollama_url, json=payload, timeout=90)
        resp.raise_for_status()
        raw = resp.json().get("message", {}).get("content", "{}")
        translated = json.loads(raw)

        # Validate scenes
        if "scenes" in translated and len(translated["scenes"]) > 0:
            print(f"[TRANSLATE] Successfully localized {len(translated['scenes'])} scenes to {persona['language']}.")
            return translated
    except Exception as e:
        print(f"[WARN] Translation failed or timed out: {e}. Returning original script with target voice.")

    # Fallback: clone script and return
    cloned = copy.deepcopy(script_data)
    return cloned
