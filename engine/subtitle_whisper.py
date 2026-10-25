"""
Global Wave - Faster-Whisper Word-Level Karaoke Subtitle Engine
Uses sub-100ms forced alignment to generate MrBeast / Alex Hormozi style
dynamic ASS subtitles where each spoken word lights up in vibrant yellow/green.
"""
import os
import re
try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

_WHISPER_MODEL = None

def get_whisper_model() -> WhisperModel:
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        _WHISPER_MODEL = WhisperModel("base", device="cpu", compute_type="int8")
    return _WHISPER_MODEL

def format_ass_time(seconds: float) -> str:
    """Format seconds into ASS timestamp: H:MM:SS.cc"""
    if seconds < 0:
        seconds = 0.0
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        centis = 99
    return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"

def generate_karaoke_ass(master_audio_path: str, out_ass_path: str, font_name: str = "Arial Black") -> str:
    """
    Transcribes audio with word-level timestamps and produces
    MrBeast/Hormozi style karaoke ASS subtitles.
    """
    model = get_whisper_model()
    segments, _ = model.transcribe(master_audio_path, word_timestamps=True)
    
    all_words = []
    for segment in segments:
        if segment.words:
            for w in segment.words:
                cleaned = w.word.strip()
                if cleaned:
                    all_words.append({
                        "word": cleaned.upper(),
                        "start": w.start,
                        "end": w.end
                    })

    if not all_words:
        print("[WARN] Whisper detected no words, creating empty ASS.")
        all_words = [{"word": "...", "start": 0.0, "end": 2.0}]

    # Chunk words into small punchy groups of 3-4 words for vertical Shorts
    WORDS_PER_CHUNK = 3
    chunks = []
    for i in range(0, len(all_words), WORDS_PER_CHUNK):
        chunks.append(all_words[i:i + WORDS_PER_CHUNK])

    # ASS Header with high-contrast styling (MrBeast yellow highlight, thick outline)
    header = f"""[Script Info]
Title: Global Wave Karaoke Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: KaraokeActive,{font_name},78,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,6,3,2,50,50,320,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []

    # For each chunk, generate events where the active word is highlighted in yellow
    for ch in chunks:
        ch_words = [item["word"] for item in ch]
        for active_idx, target_word_obj in enumerate(ch):
            start_t = target_word_obj["start"]
            end_t = target_word_obj["end"]
            
            # Highlight current word in vivid Yellow &H0000FFFF
            line_parts = []
            for idx, w in enumerate(ch_words):
                if idx == active_idx:
                    line_parts.append(f"{{\\c&H0000FFFF\\b1}}{w}{{\\r}}")
                else:
                    line_parts.append(w)
            
            formatted_line = " ".join(line_parts)
            start_str = format_ass_time(start_t)
            end_str = format_ass_time(end_t)
            events.append(f"Dialogue: 0,{start_str},{end_str},KaraokeActive,,0,0,0,,{formatted_line}")

    os.makedirs(os.path.dirname(out_ass_path), exist_ok=True)
    with open(out_ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")

    return out_ass_path