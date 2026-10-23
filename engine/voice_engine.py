"""
Global Wave - Audio Engine with Dual TTS (Kokoro Local & Edge-TTS Cloud) + Whisper Word Karaoke
Features:
1. Kokoro-82M ONNX local studio voice synthesis (offline, ~300MB RAM, English personas).
2. Edge-TTS neural cloud voice synthesis (Turkish 'tr-TR-AhmetNeural', German, Spanish, etc.).
3. Strict local mode enforcement: No silent cloud fallback if strict_local=True.
4. Rich generation metadata (requested_engine, actual_engine, language, voice_id, fallback_used, fallback_reason).
5. Sub-100ms Faster-Whisper word-level forced alignment for dynamic Hormozi/MrBeast karaoke ASS.
"""
import asyncio
import os
import subprocess
import requests
import edge_tts
from config.settings import get_ffmpeg_bin, get_ffprobe_bin, load_settings
from engine.personas import get_persona
from engine.voice_kokoro import generate_scene_audios_kokoro, is_kokoro_supported
from engine.subtitle_whisper import generate_karaoke_ass

def escape_ffmpeg_concat_path(path_str: str) -> str:
    """Escapes file paths for safe inclusion in FFmpeg concat list files."""
    clean = str(path_str).replace("\\", "/")
    clean = clean.replace("'", "'\\''")
    clean = clean.replace("\n", "").replace("\r", "")
    return clean

def get_audio_duration(file_path: str) -> float:
    """Accurately measure audio duration in seconds using ffprobe or wave headers."""
    ffprobe_bin = get_ffprobe_bin()
    cmd = [
        ffprobe_bin, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        dur = float(res.stdout.strip())
        if dur <= 0:
            raise ValueError(f"Invalid duration {dur}")
        return dur
    except Exception as e:
        # Fallback to wave module if WAV file
        if str(file_path).lower().endswith(".wav"):
            try:
                import wave
                with wave.open(file_path, "rb") as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    dur = frames / float(rate)
                    if dur > 0:
                        return dur
            except Exception:
                pass
        raise RuntimeError(f"Ses dosyası süresi okunamadı ({file_path}): {e}")

def synthesize_chunk_elevenlabs(text: str, out_mp3: str, api_key: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM") -> bool:
    """Synthesize audio using official ElevenLabs REST API."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        if resp.status_code == 200:
            with open(out_mp3, "wb") as f:
                f.write(resp.content)
            return True
        else:
            print(f"[WARN] ElevenLabs API error {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"[WARN] ElevenLabs request failed: {e}")
        return False

async def synthesize_chunk_edge(text: str, voice: str, out_mp3: str):
    """Synthesize a single text chunk with edge-tts."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_mp3)

def generate_scene_audios_edge(scenes: list, voice: str, task_temp_dir: str, audio_meta: dict = None) -> list:
    """Synthesize all scenes in batches to handle long scripts smoothly."""
    results = []
    meta = audio_meta or {
        "requested_engine": "edge-tts",
        "actual_engine": "edge-tts",
        "voice_id": voice,
        "fallback_used": False,
        "fallback_reason": None
    }
    
    async def _run_batch(batch_scenes, start_idx):
        tasks = []
        batch_meta = []
        for i, sc in enumerate(batch_scenes):
            idx = start_idx + i
            out_mp3 = os.path.join(task_temp_dir, f"audio_scene_{idx}.mp3")
            text = sc.get("text", "").strip() or "..."
            tasks.append(synthesize_chunk_edge(text, voice, out_mp3))
            batch_meta.append((sc.get("scene_id", idx), out_mp3, text, sc.get("visual_keyword", "cinematic technology")))
        
        await asyncio.gather(*tasks)
        
        for sc_id, out_mp3, text, v_kw in batch_meta:
            dur = get_audio_duration(out_mp3)
            results.append({
                "scene_id": sc_id,
                "mp3_path": out_mp3,
                "duration": dur,
                "text": text,
                "visual_keyword": v_kw,
                "audio_meta": dict(meta)
            })

    # Process in chunks of 5 for safety and memory stability
    batch_size = 5
    for start in range(0, len(scenes), batch_size):
        chunk = scenes[start:start+batch_size]
        asyncio.run(_run_batch(chunk, start))
        
    return results

def generate_scene_audios(scenes: list, voice: str, persona_id: str, task_temp_dir: str, tts_engine: str = "kokoro") -> list:
    """
    Unified scene audio generator with strict local isolation.
    If strict_local=True, absolutely zero outbound cloud requests (ElevenLabs or Edge-TTS)
    are permitted under any circumstance.
    """
    settings = load_settings()
    strict_local = bool(settings.get("strict_local", False))
    persona_data = get_persona(persona_id)
    persona_lang = persona_data.get("language", "en-US")
    resolved_voice = voice or persona_data.get("voice", "tr-TR-AhmetNeural")
    clean_engine = str(tts_engine).lower().strip()

    # STRICT LOCAL ENFORCEMENT: Block any cloud engine immediately
    if strict_local:
        if clean_engine in ("elevenlabs", "edge-tts", "edge_tts"):
            raise ValueError(
                f"strict_local modu etkin: Bulut tabanli TTS motoru ('{tts_engine}') kullanilamaz. "
                f"Lutfen yerel motor (Kokoro/Piper) kullanin veya strict_local ayarini kapatin."
            )
        if clean_engine != "kokoro":
            raise ValueError(
                f"strict_local modu etkin: Desteklenmeyen veya yerel olmayan motor '{tts_engine}'. "
                f"Yalnizca yerel motorlar calistirilabilir."
            )
        # In strict_local, Kokoro MUST support the persona and language
        if not is_kokoro_supported(persona_id, persona_lang):
            raise RuntimeError(
                f"strict_local modu etkin: Kokoro-82M '{persona_lang}' dilini ({persona_id}) desteklemez. "
                f"Kokoro yalnizca Ingilizce fonetikleri ('en-US', 'en-GB') destekler. Cevrimdisi Turkce ses icin "
                f"yerel Piper modeli kurulmali veya bulut tabanli Edge-TTS icin strict_local ayari kapatilmalidir."
            )
        try:
            print("[VOICE] Synthesizing with Kokoro-82M local ONNX engine (strict_local mode)...")
            return generate_scene_audios_kokoro(scenes, persona_id, task_temp_dir)
        except Exception as e:
            raise RuntimeError(f"strict_local modu etkin ve Kokoro yerel ses uretimi basarisiz oldu: {e}. Bulut fallback engellendi.")

    # NORMAL MODE (strict_local is False):
    if clean_engine == "elevenlabs":
        eleven_key = settings.get("elevenlabs_api_key", "")
        eleven_voice = settings.get("elevenlabs_voice_id", "21m00Tcm4TlvDq8ikWAM")
        if not eleven_key:
            raise ValueError("ElevenLabs motoru secildi fakat 'elevenlabs_api_key' tanimli degil.")
        print("[VOICE] Synthesizing with ElevenLabs API...")
        results = []
        for i, sc in enumerate(scenes):
            out_mp3 = os.path.join(task_temp_dir, f"audio_scene_{i}.mp3")
            text = sc.get("text", "").strip() or "..."
            success = synthesize_chunk_elevenlabs(text, out_mp3, eleven_key, eleven_voice)
            if not success:
                raise RuntimeError(f"ElevenLabs API uzerinden sahne {i} icin ses uretilemedi.")
            dur = get_audio_duration(out_mp3)
            results.append({
                "scene_id": sc.get("scene_id", i),
                "mp3_path": out_mp3,
                "audio_path": out_mp3,
                "duration": dur,
                "text": text,
                "visual_keyword": sc.get("visual_keyword", "cinematic technology"),
                "audio_meta": {
                    "requested_engine": "elevenlabs",
                    "actual_engine": "elevenlabs",
                    "language": persona_lang,
                    "voice_id": eleven_voice,
                    "fallback_used": False,
                    "fallback_reason": None
                }
            })
        return results

    if clean_engine == "kokoro":
        if not is_kokoro_supported(persona_id, persona_lang):
            print(f"[VOICE] Kokoro-82M '{persona_lang}' dilini desteklemez. Dogal telaffuz icin Neural Edge-TTS ({resolved_voice}) motoruna yonlendiriliyor...")
            meta = {
                "requested_engine": "kokoro",
                "actual_engine": "edge-tts",
                "language": persona_lang,
                "voice_id": resolved_voice,
                "fallback_used": True,
                "fallback_reason": f"Kokoro-82M does not support language '{persona_lang}'; routed to neural Edge-TTS voice"
            }
            return generate_scene_audios_edge(scenes, resolved_voice, task_temp_dir, audio_meta=meta)
        try:
            print("[VOICE] Synthesizing with Kokoro-82M local ONNX engine...")
            return generate_scene_audios_kokoro(scenes, persona_id, task_temp_dir)
        except Exception as e:
            print(f"[WARN] Kokoro synthesis failed ({e}), falling back to Edge-TTS...")
            meta = {
                "requested_engine": "kokoro",
                "actual_engine": "edge-tts",
                "language": persona_lang,
                "voice_id": resolved_voice,
                "fallback_used": True,
                "fallback_reason": str(e)
            }
            return generate_scene_audios_edge(scenes, resolved_voice, task_temp_dir, audio_meta=meta)

    if clean_engine in ("edge-tts", "edge_tts", "default"):
        print(f"[VOICE] Synthesizing with Edge-TTS neural engine ({resolved_voice})...")
        meta = {
            "requested_engine": "edge-tts",
            "actual_engine": "edge-tts",
            "language": persona_lang,
            "voice_id": resolved_voice,
            "fallback_used": False,
            "fallback_reason": None
        }
        return generate_scene_audios_edge(scenes, resolved_voice, task_temp_dir, audio_meta=meta)

    raise ValueError(f"Gecersiz tts_engine: '{tts_engine}'. Desteklenen motorlar: kokoro, edge-tts, elevenlabs.")

def concatenate_audios(audio_chunks: list, master_mp3_path: str) -> float:
    """Concatenate audio chunks seamlessly using FFmpeg concat."""
    ffmpeg_bin = get_ffmpeg_bin()
    concat_list_file = os.path.join(os.path.dirname(master_mp3_path), "audio_concat_list.txt")
    
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for chunk in audio_chunks:
            escaped_p = escape_ffmpeg_concat_path(chunk["mp3_path"])
            f.write(f"file '{escaped_p}'\n")
            
    cmd = [
        ffmpeg_bin, "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list_file, "-c:a", "libmp3lame", "-q:a", "2",
        master_mp3_path
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    return get_audio_duration(master_mp3_path)

def generate_subtitles(master_audio_path: str, audio_chunks: list, out_ass_path: str, font_name: str = "Arial Black"):
    """
    Generates dynamic word-level karaoke ASS subtitles via Faster-Whisper.
    Falls back to legacy chunked ASS if Whisper alignment fails.
    """
    try:
        print("[SUBTITLES] Generating dynamic word-level karaoke subtitles via Faster-Whisper...")
        generate_karaoke_ass(master_audio_path, out_ass_path, font_name=font_name)
    except Exception as e:
        print(f"[WARN] Faster-Whisper karaoke generation failed ({e}), falling back to standard ASS...")
        _legacy_generate_ass(audio_chunks, out_ass_path, font_name)

def _legacy_generate_ass(audio_chunks: list, out_ass_path: str, font_name: str = "Arial"):
    header = f"""[Script Info]
Title: Global Wave Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: GlobalShorts,{font_name},72,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,6,2,2,40,40,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    current_time = 0.0
    for chunk in audio_chunks:
        start_t = current_time
        end_t = current_time + chunk["duration"]
        current_time = end_t
        words = chunk["text"].split()
        if not words:
            continue
        words_per_slice = 4
        slices = [words[i:i + words_per_slice] for i in range(0, len(words), words_per_slice)]
        slice_dur = chunk["duration"] / len(slices)
        s_time = start_t
        for sl in slices:
            e_time = s_time + slice_dur
            events.append(f"Dialogue: 0,{s_time:.2f},{e_time:.2f},GlobalShorts,,0,0,0,,{' '.join(sl)}")
            s_time = e_time

    with open(out_ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")
