"""
Global Wave - Engagement & Rage Bait Engine (Faz 4)
Engineered for maximum YouTube Shorts / TikTok comment section activity.
Strategies:
1. Subtle typo injection in altyazı/text (triggers comment corrections & boosts algorithm score).
2. Provocative debate question generator (compels viewers to pick sides).
3. Comment bait CTA booster.
"""
import copy
import random
import re
import requests
from config.settings import load_settings

COMMON_TYPO_MAP = {
    # English
    "electricity": "electrcity",
    "government": "goverment",
    "definitely": "definately",
    "technology": "technolgy",
    "calendar": "calender",
    "receive": "recieve",
    "billion": "miliion",
    "century": "centry",
    "machine": "machne",
    "experiment": "experment",
    # Turkish
    "yalnız": "yanlız",
    "yanlış": "yalnış",
    "herkes": "herkez",
    "hükümet": "hükümat",
    "orijinal": "orjinal",
    "milyar": "milyon",
    "laboratuvar": "laboratuar",
    "bilim": "blim",
    # German
    "Ingenieur": "Ingenur",
    "Effizienz": "Effizenz",
    "Maschine": "Mashine",
    # Spanish
    "gobierno": "govierno",
    "tecnología": "tecnolojía",
    "diferente": "diferete"
}

PROVOCATIVE_QUESTIONS = {
    "us_hustler": [
        "Do you think 99% of people are too lazy to do this, or is the system rigged?",
        "Would you quit your 9-to-5 tomorrow if you mastered this tool? Be honest.",
        "Is this true wealth generation or just another high-tech trap?"
    ],
    "uk_critic": [
        "Are consumers being blatantly lied to, or do people actually enjoy being fooled?",
        "Who is really at fault here: the giant corporations or the buyers?",
        "Tell me: Would you still buy this knowing the real cost?"
    ],
    "de_engineer": [
        "Ist dieses System wirklich effizient oder nur eine teure Illusion?",
        "Würden Sie dieser Technologie vertrauen oder bleibt das deutsche Modell überlegen?",
        "Welche Methode ist rechnerisch sinnvoller? Schreiben Sie Ihre Berechnung."
    ],
    "de_historian": [
        "War dieses Ereignis reine menschliche Fahrlässigkeit oder unvermeidbare Katastrophe?",
        "Hätten die Behörden das Desaster rechtzeitig verhindern können?",
        "Welcher historische Fehler war rückblickend noch verheerender?"
    ],
    "es_narrator": [
        "¿Crees que la historia oficial nos oculta la verdad, o es simple coincidencia?",
        "Si estuvieras en ese lugar exacto, ¿qué habrías hecho tú?",
        "¿De verdad crees que la ciencia moderna tiene una explicación para esto?"
    ],
    "tr_storyteller": [
        "Sizce bu olay tamamen ihmal mi yoksa gizlenen bir gerçek mi?",
        "O an orada olsaydınız siz ne yapardınız? Dürüstçe yoruma yazın.",
        "Bu rekorun kırılması imkansız mı yoksa daha büyüğü yolda mı?"
    ]
}

def inject_subtle_typo(text: str) -> str:
    """
    Subtly replaces one word with a common typo or transposes two inner letters.
    Boosts comment retention because viewers pause or replay to type a correction.
    """
    words = text.split()
    if len(words) < 4:
        return text

    # First attempt: dictionary replacement
    for idx, w in enumerate(words):
        clean_w = re.sub(r'[^a-zA-ZçÇğĞıİöÖşŞüÜäÄöÖüÜßáéíóúñÁÉÍÓÚÑ]', '', w).lower()
        if clean_w in COMMON_TYPO_MAP:
            replacement = COMMON_TYPO_MAP[clean_w]
            # Match capitalization
            if w[0].isupper():
                replacement = replacement.capitalize()
            words[idx] = re.sub(clean_w, replacement, w, flags=re.IGNORECASE)
            print(f"[RAGE_BAIT] Injected dictionary typo: '{w}' -> '{words[idx]}'")
            return " ".join(words)

    # Second attempt: transpose two adjacent letters in a middle word
    target_idx = random.randint(1, len(words) - 2)
    target_word = words[target_idx]
    if len(target_word) >= 6 and target_word.isalpha():
        pos = random.randint(2, len(target_word) - 3)
        typo_word = target_word[:pos] + target_word[pos+1] + target_word[pos] + target_word[pos+2:]
        words[target_idx] = typo_word
        print(f"[RAGE_BAIT] Injected letter transposition typo: '{target_word}' -> '{typo_word}'")
        return " ".join(words)

    return text

def generate_rage_bait(script_data: dict, persona_id: str = "us_hustler", inject_typo: bool = False) -> dict:
    """
    Enhances a script JSON with comment bait, provocative questions, and an optional subtitle typo.
    """
    enriched = copy.deepcopy(script_data)
    scenes = enriched.get("scenes", [])
    if not scenes:
        return enriched

    # 1. Subtle typo injection in Scene 2 or 3 (where viewer attention is high)
    if inject_typo and len(scenes) >= 3:
        target_scene_idx = 2 if len(scenes) > 2 else 1
        original_text = scenes[target_scene_idx].get("text", "")
        scenes[target_scene_idx]["text"] = inject_subtle_typo(original_text)

    # 2. Pick a high-engagement provocative debate question for final CTA
    pool = PROVOCATIVE_QUESTIONS.get(persona_id, PROVOCATIVE_QUESTIONS["us_hustler"])
    selected_question = random.choice(pool)

    # Enhance final scene text if it's the CTA
    last_scene = scenes[-1]
    last_text = last_scene.get("text", "")
    if "?" not in last_text:
        last_scene["text"] = f"{last_text} {selected_question}"
    
    enriched["rage_bait_meta"] = {
        "provocative_question": selected_question,
        "typo_injected": inject_typo
    }
    print(f"[RAGE_BAIT] Enriched script with provocative angle: '{selected_question}'")
    return enriched
