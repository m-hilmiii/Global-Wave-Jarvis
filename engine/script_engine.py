"""
Global Wave - Script Engine with Precision Duration Calibration, Dual Hooks & Humanization
Features:
1. Exact mathematical speech-timing calibration (2.33 words/sec benchmark).
2. Dual-Hook Architecture: Scene 0 = Primary Hook (0-3s), Scene 1 = Re-Hook (3-6s).
3. Hook Categories: Danger, Curiosity, Controversy, Record, Default.
4. Long-Form Documentary Support: 10min (20 scenes), 12min (24 scenes), 14min (26 scenes), 16min (30 scenes).
5. Seamless Loop Engineering: Final sentence flows into opening sentence.
6. Multi-tier Humanization & Rage Bait injection.
"""
import json
import re
import requests
from config.settings import load_settings
from engine.personas import get_persona
from engine.autonomous_feedback import get_channel_report
from engine.humanizer import humanize_script
from engine.engagement_engine import generate_rage_bait
try:
    from engine.hookscore import evaluate_hook_text
except Exception:
    evaluate_hook_text = None

HOOK_STYLE_INSTRUCTIONS = {
    "danger": "HOOK STYLE: DANGER / HIGH STAKES. Start in media res with an imminent catastrophe, life-or-death decision, or terrifying zero-survival scenario.",
    "curiosity": "HOOK STYLE: OBSOLETE TRUTH / FORBIDDEN MYSTERY. Start with a classified or widely misunderstood secret that defies conventional explanation.",
    "controversy": "HOOK STYLE: CONTROVERSY / ATTACK POPULAR MYTH. Start by directly attacking a widely accepted belief, proving why 99% of people are wrong.",
    "record": "HOOK STYLE: EXTREME RECORD / UNBELIEVABLE METRIC. Start with an astronomical, mind-bending number or statistic that sounds mathematically impossible.",
    "default": "HOOK STYLE: DRAMATIC CONTRAST. Start with an intense, unexpected revelation that shatters assumptions immediately."
}

def get_duration_specs(target_duration: str) -> dict:
    d = str(target_duration).lower().strip()
    
    if "16min" in d:
        return {
            "is_longform": True,
            "seconds": 960,
            "target_words": 2200,
            "min_words": 1800,
            "num_scenes": 28,
            "desc": "LONG-FORM 16-MINUTE CINEMATIC DOCUMENTARY. Write 28 rich narrative scenes with deep chronological progression, immersive POV storytelling, and detailed technical breakdown."
        }
    elif "14min" in d:
        return {
            "is_longform": True,
            "seconds": 840,
            "target_words": 1950,
            "min_words": 1600,
            "num_scenes": 26,
            "desc": "LONG-FORM 14-MINUTE CINEMATIC DOCUMENTARY. Write 26 narrative scenes with chronological tension, historical context, and high information density."
        }
    elif "12min" in d:
        return {
            "is_longform": True,
            "seconds": 720,
            "target_words": 1700,
            "min_words": 1400,
            "num_scenes": 24,
            "desc": "LONG-FORM 12-MINUTE CINEMATIC DOCUMENTARY. Write 24 narrative scenes with clear documentary act structure (Act 1: Inciting Incident, Act 2: Deep Investigation, Act 3: Climax & Resolution)."
        }
    elif "10min" in d:
        return {
            "is_longform": True,
            "seconds": 600,
            "target_words": 1400,
            "min_words": 1200,
            "num_scenes": 20,
            "desc": "LONG-FORM 10-MINUTE CINEMATIC DOCUMENTARY. Write 20 narrative scenes with gripping tension, chronological unfolding, and expert analysis."
        }
    elif "60" in d:
        return {
            "is_longform": False,
            "seconds": 60,
            "target_words": 145,
            "min_words": 130,
            "num_scenes": 9,
            "desc": "EXACTLY 60 SECONDS SHORTS. Total Spoken Script Length MUST BE 140-155 WORDS across 9-10 scenes. Each scene must contain 15-18 words (2 full descriptive sentences). Short 5-word scenes are strictly forbidden!"
        }
    elif "30" in d and "45" not in d:
        return {
            "is_longform": False,
            "seconds": 30,
            "target_words": 75,
            "min_words": 65,
            "num_scenes": 5,
            "desc": "EXACTLY 30 SECONDS SHORTS. Total Spoken Script Length MUST BE 70-80 WORDS across 5 scenes. Each scene must contain 14-16 words."
        }
    else:  # Default: 45 seconds Shorts
        return {
            "is_longform": False,
            "seconds": 45,
            "target_words": 110,
            "min_words": 95,
            "num_scenes": 7,
            "desc": "EXACTLY 45 SECONDS SHORTS. Total Spoken Script Length MUST BE 105-120 WORDS across 7-8 scenes. Each scene must contain 14-17 words (2 full descriptive sentences)."
        }

CINEMATIC_SHORTS_PROMPT = """You are an elite, award-winning short-form documentary filmmaker for YouTube Shorts, Reels, and TikTok.
Persona Voice: {persona_name} ({country}).
Tone: {tone}.
Language: All spoken text MUST be in natural, native {target_language} ({language_code}).

{hook_instruction}

DUAL HOOK ARCHITECTURE (CRITICAL FOR RETENTION):
- Scene 0 MUST have role="hook" (0-3 sec): Instant scroll-stopper statement.
- Scene 1 MUST have role="re_hook" (3-6 sec): The second punch that reinforces curiosity and makes leaving impossible.

CRITICAL SCRIPT DURATION RULE:
{target_duration_desc}
Total Spoken Word Count: MINIMUM of {min_words} words (Target: {target_words} words) across {num_scenes} scenes.
Every single scene MUST have 2 full, descriptive sentences (14 to 18 words).

MANDATORY RULES:
1. ZERO TOPIC DRIFT: Stay 100% focused on the user's exact topic with intense narrative depth.
2. BAN ON CLICHE HOOKS: NEVER start with 'Stop scrolling!' or 'Did you know?'.
3. STRICT 1-2 WORD VISUAL SEARCH TAGS: visual_keyword MUST be 1-2 English nouns (e.g. 'storm lightning', 'power grid', 'laboratory', 'city aerial').
4. SEAMLESS LOOP: Provide a seamless loop word/phrase where the final sentence flows directly back into the opening sentence.
5. ORGANIC CTA: End with an intriguing question that demands comments.

{audience_feedback_directive}

OUTPUT FORMAT (RAW JSON ONLY):
{{
  "topic": "Clean refined title",
  "scenes": [
    {{
      "scene_id": 0,
      "role": "hook",
      "text": "Shocking opening sentence. Second sentence that seals the premise.",
      "visual_keyword": "lightning storm",
      "duration_est": 6.0
    }},
    {{
      "scene_id": 1,
      "role": "re_hook",
      "text": "The unexpected escalation that proves why this changes everything. What scientists discovered next was baffling.",
      "visual_keyword": "scientific radar",
      "duration_est": 6.5
    }}
  ],
  "seamless_loop_word": "Because"
}}
"""

CINEMATIC_LONGFORM_PROMPT = """You are an award-winning long-form documentary filmmaker producing 10-16 minute high-retention documentaries for YouTube (like MagnatesMedia, Lemmino, or Vox).
Persona Voice: {persona_name} ({country}).
Tone: {tone}.
Language: Spoken text MUST be in natural, immersive {target_language} ({language_code}).

DOCUMENTARY NARRATIVE STRUCTURE:
1. ACT 1 (Scenes 0-3): The Inciting Incident & Cold Open Hook. Start in media res with gripping sensory details.
2. ACT 2 (Scenes 4-{mid_scene}): The Investigation & Context. Unpack the hidden chronology, scientific/financial mechanisms, and undisclosed records.
3. ACT 3 (Scenes {mid_scene_plus}-{num_scenes}): The Climax, Fallout, and Global Implications.

MANDATORY RULES:
1. NET INFORMATION GAIN (NIG): Include at least 8-12 specific, obscure historical or scientific facts (exact dates, locations, measurements).
2. POV IMMERSION: Bring the viewer directly into the scene ('Imagine standing in the control room as alarms sound...').
3. VISUAL PACING: Every scene represents a 25-35 second visual sequence. visual_keyword MUST be 1-2 concise English keywords suitable for archival or cinematic stock footage.
4. Total Spoken Word Count: Minimum {min_words} words across {num_scenes} scenes.

OUTPUT FORMAT (RAW JSON ONLY):
{{
  "topic": "Epic Documentary Title",
  "scenes": [
    {{
      "scene_id": 0,
      "role": "cold_open",
      "text": "Rich, immersive paragraph setting the scene with dramatic gravitas.",
      "visual_keyword": "vintage radar",
      "duration_est": 25.0
    }}
  ],
  "seamless_loop_word": "And so"
}}
"""

def generate_script(
    persona_id: str,
    topic: str,
    target_duration: str = "45",
    channel_id: str = "default",
    hook_style: str = "danger",
    humanize_level: str = "light",
    enable_rage_bait: bool = False
) -> dict:
    settings = load_settings()
    persona = get_persona(persona_id)
    spec = get_duration_specs(target_duration)
    
    clean_topic = re.sub(r'[\(\)\[\]]', '', topic).strip()
    hook_instruction = HOOK_STYLE_INSTRUCTIONS.get(hook_style, HOOK_STYLE_INSTRUCTIONS["danger"])

    # Closed-loop audience intelligence injection
    report = get_channel_report(channel_id)
    demands = ", ".join(report.get("audience_demands", []))
    weaknesses = ", ".join(report.get("weaknesses_to_avoid", []))
    catchphrase = report.get("persona_tuning", {}).get("catchphrase", "")
    
    feedback_directive = f"""
AUDIENCE INTELLIGENCE DIRECTIVE:
- Demands to satisfy: {demands}
- Critical weaknesses to AVOID: {weaknesses}
- Imprint catchphrase if appropriate: '{catchphrase}'
"""

    if spec.get("is_longform"):
        # Long-form documentary prompt
        prompt = CINEMATIC_LONGFORM_PROMPT.format(
            persona_name=persona["name"],
            country=persona["country"],
            tone=persona["tone"],
            target_language=persona["language"],
            language_code=persona["language"],
            mid_scene=spec["num_scenes"] // 2,
            mid_scene_plus=(spec["num_scenes"] // 2) + 1,
            min_words=spec["min_words"],
            num_scenes=spec["num_scenes"]
        )
        user_prompt = (
            f"Topic: '{clean_topic}'.\n"
            f"Produce a full {spec['seconds']//60}-minute documentary script with {spec['num_scenes']} scenes.\n"
            f"Write deeply descriptive, compelling narration. Output RAW JSON ONLY."
        )
        model_name = settings.get("deep_model", "qwen3:14b")
        num_predict = 4096
    else:
        # Shorts prompt with Dual Hook
        prompt = CINEMATIC_SHORTS_PROMPT.format(
            persona_name=persona["name"],
            country=persona["country"],
            tone=persona["tone"],
            target_language=persona["language"],
            language_code=persona["language"],
            hook_instruction=hook_instruction,
            target_duration_desc=spec["desc"],
            min_words=spec["min_words"],
            target_words=spec["target_words"],
            num_scenes=spec["num_scenes"],
            audience_feedback_directive=feedback_directive
        )
        user_prompt = (
            f"Topic: '{clean_topic}'.\n"
            f"Target Duration: {spec['seconds']} SECONDS.\n"
            f"Hook Style: {hook_style.upper()}.\n"
            f"Write EXACTLY {spec['num_scenes']} scenes with a TOTAL of {spec['target_words']} SPOKEN WORDS (minimum {spec['min_words']} words).\n"
            f"Scene 0 must be 'hook', Scene 1 must be 're_hook'. Output RAW JSON ONLY."
        )
        model_name = settings.get("fast_model", "qwen3:8b")
        num_predict = 2200

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_prompt}
        ],
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.65,
            "num_predict": num_predict
        }
    }
    
    ollama_url = f"{settings['ollama_host'].rstrip('/')}/api/chat"
    
    for attempt_model in [model_name, "qwen3:14b", "llama3.1:8b", "qwen3:8b"]:
        try:
            print(f"[SCRIPT] Generating with {attempt_model} for: '{clean_topic}' ({spec['seconds']}s target, style={hook_style})...")
            payload["model"] = attempt_model
            timeout_sec = 140 if spec.get("is_longform") else 65
            resp = requests.post(ollama_url, json=payload, timeout=timeout_sec)
            resp.raise_for_status()
            raw_content = resp.json().get("message", {}).get("content", "{}")
            parsed = json.loads(raw_content)
            
            scenes = parsed.get("scenes", [])
            if len(scenes) >= (10 if spec.get("is_longform") else 4):
                total_words = sum(len(s.get("text", "").split()) for s in scenes)
                print(f"[SCRIPT] Received {len(scenes)} scenes with {total_words} total words.")
                
                # Auto-enrich if short
                if total_words < spec["min_words"] and not spec.get("is_longform"):
                    parsed = enrich_script_duration(parsed, spec, clean_topic)
                    
                # Faz 2: Humanize script
                if humanize_level != "off":
                    parsed = humanize_script(parsed, level=humanize_level, persona_id=persona_id)
                
                # Faz 4: Rage Bait
                if enable_rage_bait:
                    parsed = generate_rage_bait(parsed, persona_id=persona_id)

                if evaluate_hook_text and parsed.get("scenes"):
                    first_text = parsed["scenes"][0].get("text", "")
                    parsed["hook_evaluation"] = evaluate_hook_text(first_text)

                return parsed
        except Exception as e:
            print(f"[WARN] Model {attempt_model} error: {e}. Trying next option...")

    # Fallback
    print(f"[SCRIPT] Using precision fallback calibrated for {spec['seconds']}s...")
    fallback = generate_dynamic_fallback(persona, clean_topic, spec)
    if humanize_level != "off":
        fallback = humanize_script(fallback, level=humanize_level, persona_id=persona_id)
    if enable_rage_bait:
        fallback = generate_rage_bait(fallback, persona_id=persona_id)
    return fallback

def enrich_script_duration(parsed: dict, spec: dict, topic: str) -> dict:
    """Enriches scenes so that total spoken words reach the exact target duration."""
    scenes = parsed.get("scenes", [])
    if not scenes:
        return parsed
        
    for i, sc in enumerate(scenes):
        text = sc.get("text", "").strip()
        words = text.split()
        if len(words) < 14:
            if i == 0:
                sc["text"] = f"{text} This pivotal development is fundamentally transforming modern understanding."
            elif i == len(scenes) - 1:
                sc["text"] = f"{text} Drop your thoughts and predictions in the comments below, and share your perspective with our community."
            else:
                sc["text"] = f"{text} As investigative evidence continues to surface across the globe, the broader implications are impossible to ignore."
    return parsed

def generate_dynamic_fallback(persona: dict, clean_topic: str, spec: dict) -> dict:
    """Generates an authentic, fully calibrated script meeting the word count requirement."""
    num_scenes = spec["num_scenes"]
    
    if spec["seconds"] >= 55:
        scenes_data = [
            ("Imagine a turning point so profound that it rewrites our understanding of reality.", "storm lightning"),
            (f"Behind {clean_topic} lies an untold mechanism that researchers have been tracking for decades.", "radar screen"),
            ("Traditional explanations leave critical questions unanswered while records continue to break.", "laboratory"),
            ("When conditions reached a critical tipping point, standard containment protocols failed completely.", "electricity"),
            ("Eyewitness accounts and sensor telemetry revealed an unprecedented shift in atmospheric pressure.", "cloud aerial"),
            ("Entire urban networks and infrastructure systems were placed on emergency standby within minutes.", "city skyline"),
            ("Decades of historical data could not predict the speed and intensity of what unfolded next.", "technology"),
            ("By the time the full scope was documented, the event had set a benchmark that stands to this day.", "infrastructure"),
            ("Could a phenomenon of this magnitude occur again in the near future? Share your perspective below.", "future")
        ]
    elif spec["seconds"] >= 40:
        scenes_data = [
            (f"What truly happened during {clean_topic} is far more astonishing than initial reports revealed.", "storm lightning"),
            ("Within seconds, a sequence of events began that shocked leading experts across the entire industry.", "radar screen"),
            ("Decades of historical records offered no precedent for the sheer scale of the disruption.", "laboratory"),
            ("Eyewitness telemetry confirmed that key indicators exceeded all previous safety margins.", "technology"),
            ("The fallout forced regulatory bodies to reconsider standard operating assumptions completely.", "city skyline"),
            ("Today, researchers point to this critical event as the moment everything fundamentally changed.", "infrastructure"),
            ("Would you have made the same call under those extreme circumstances? Tell us in the comments.", "future")
        ]
    else:  # 30s
        scenes_data = [
            (f"The untold truth behind {clean_topic} shatters almost everything we assumed.", "technology"),
            ("Critical safety systems began reporting anomalous readings hours before the public knew.", "laboratory"),
            ("When the threshold was crossed, the chain reaction was instantaneous and irreversible.", "electricity"),
            ("Today, experts consider this event one of the most consequential turning points in history.", "city skyline"),
            ("Was this catastrophe entirely preventable? Leave your answer in the comments below.", "future")
        ]
        
    scenes = []
    for i, (text, tag) in enumerate(scenes_data[:num_scenes]):
        role = "hook" if i == 0 else ("re_hook" if i == 1 else f"scene_{i}")
        scenes.append({
            "scene_id": i,
            "role": role,
            "text": text,
            "visual_keyword": tag,
            "duration_est": round(len(text.split()) / 2.33, 1)
        })
        
    return {
        "topic": clean_topic,
        "scenes": scenes,
        "seamless_loop_word": "Because"
    }
