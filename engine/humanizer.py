"""
Global Wave - Script Differentiation Funnel & Humanizer Engine (Faz 2)
Removes robotic AI phrasing, injects Net Information Gain (NIG),
and adapts conversational human rhythm to pass platform AI-content scrutiny.
"""
import copy
import json
import re
import requests
from config.settings import load_settings
from engine.personas import get_persona

AI_CLICHE_PATTERNS = [
    (r"\bIn today's fast-paced world\b", "Right now"),
    (r"\bIt is important to remember that\b", "Keep in mind,"),
    (r"\bDid you know that\b", "Here is something wild:"),
    (r"\bYou won't believe this\b", "The truth is shocking:"),
    (r"\bDelve into\b", "explore"),
    (r"\bFurthermore,\b", "Even crazier,"),
    (r"\bMoreover,\b", "On top of that,"),
    (r"\bIn conclusion,\b", "At the end of the day,"),
    (r"\bTestament to\b", "proof of"),
    (r"\bBeacon of\b", "symbol of"),
    (r"\bTapestry of\b", "mix of"),
    (r"\bGame-changer\b", "breakthrough"),
    (r"\bRevolutionary\b", "monumental"),
    # Turkish cliches
    (r"\bBiliyor muydunuz\b", "İşte akılalmaz bir detay:"),
    (r"\bGelin hep birlikte inceleyelim\b", "Olayın perde arkasına bakalım:"),
    (r"\bSonuç olarak\b", "İşin aslı şu ki,"),
    (r"\bAyrıca,\b", "Dahası var,")
]

CONVERSATIONAL_INSERTS = {
    "us_hustler": ["Look,", "Here is the insane part:", "Most people miss this completely:"],
    "uk_critic": ["Here is the uncomfortable truth:", "Quite frankly,", "The numbers tell a rather different story:"],
    "de_engineer": ["Fakt ist:", "Entscheidend ist hierbei Folgendes:", "Die physikalische Realität ist eindeutig:"],
    "de_historian": ["Genau in diesem Moment:", "Was die Geschichtsbücher verschweigen:", "Die Lage spitzte sich dramatisch zu:"],
    "es_narrator": ["Mira esto con atención:", "Lo que casi nadie te cuenta es esto:", "El momento exacto en que todo cambió:"],
    "tr_storyteller": ["Şimdi sıkı durun:", "İşin en can alıcı noktası ise şu:", "Kimsenin fark etmediği o detay:"]
}

HUMANIZER_SYSTEM_PROMPT = """You are a master script editor and investigative journalist.
Your job is to HUMANALIZE and REMOVE ALL ROBOTIC AI TONE from this video script.

PERSONA: {persona_name} ({language}).
TONE: {tone}.

MANDATORY EDITING RULES:
1. NET INFORMATION GAIN (NIG): Enrich the scenes with obscure, precise facts, dates, numbers, or psychological hooks.
2. CONVERSATIONAL CADENCE: Write like a real human speaking to another human face-to-face. Use punchy sentences, natural pauses, and vivid sensory language.
3. PRESERVE THE SCHEMA: Return the exact same JSON format with identical scene IDs, visual keywords, and role names. Only refine the spoken "text" and "seamless_loop_word".
4. ZERO AI CLICHES: Never use corporate jargon, academic phrases, or formulaic transitions.
5. Language: Output spoken text in natural {language}.
6. Output RAW JSON ONLY.
"""

def clean_cliches_rule_based(text: str) -> str:
    """Fast regex-based cliché scrubbing."""
    cleaned = text
    for pattern, replacement in AI_CLICHE_PATTERNS:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    return cleaned

def humanize_script(script_data: dict, level: str = "light", persona_id: str = "us_hustler") -> dict:
    """
    Applies the differentiation funnel:
    - level="off": returns original script
    - level="light": regex cleaning + conversational marker injection
    - level="deep": second-pass LLM rewriting with Net Information Gain (NIG)
    """
    if level == "off":
        return script_data

    enriched = copy.deepcopy(script_data)
    scenes = enriched.get("scenes", [])
    if not scenes:
        return enriched

    persona = get_persona(persona_id)

    # 1. Light Level (Always executed as baseline)
    for sc in scenes:
        original = sc.get("text", "")
        sc["text"] = clean_cliches_rule_based(original)

    # Add 1 subtle conversational insert in scene 1 or 2
    inserts = CONVERSATIONAL_INSERTS.get(persona_id, CONVERSATIONAL_INSERTS["us_hustler"])
    if inserts and len(scenes) >= 2:
        marker = inserts[0]
        s1_text = scenes[1].get("text", "")
        if not s1_text.startswith(marker):
            scenes[1]["text"] = f"{marker} {s1_text}"

    if level == "light":
        print(f"[HUMANIZER] Applied Light humanization (cliché scrub + conversational markers) for {persona_id}.")
        return enriched

    # 2. Deep Level: LLM Net Information Gain & Narrative Restructuring
    settings = load_settings()
    model = settings.get("fast_model", "qwen3:8b")
    ollama_url = f"{settings['ollama_host'].rstrip('/')}/api/chat"

    prompt = HUMANIZER_SYSTEM_PROMPT.format(
        persona_name=persona["name"],
        language=persona["language"],
        tone=persona["tone"]
    )

    try:
        print(f"[HUMANIZER] Executing Deep humanization with NIG injection using {model}...")
        resp = requests.post(ollama_url, json={
            "model": model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(enriched, ensure_ascii=False)}
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.6}
        }, timeout=45)
        resp.raise_for_status()
        raw = resp.json().get("message", {}).get("content", "{}")
        deep_parsed = json.loads(raw)
        if "scenes" in deep_parsed and len(deep_parsed["scenes"]) == len(scenes):
            print(f"[HUMANIZER] Deep humanization successful ({len(deep_parsed['scenes'])} scenes updated with NIG).")
            return deep_parsed
    except Exception as e:
        print(f"[WARN] Deep humanization LLM pass timed out or failed: {e}. Falling back to Light humanization.")

    return enriched
