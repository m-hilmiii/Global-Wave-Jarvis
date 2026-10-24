def escape_ffmpeg_concat_path(path_str: str) -> str:
    """Escapes file paths for safe inclusion in FFmpeg concat list files."""
    clean = str(path_str).replace("\\", "/")
    clean = clean.replace("'", "'\\''")
    clean = clean.replace("\n", "").replace("\r", "")
    return clean

"""
Global Wave - 2-Stage FFmpeg Video Engine with Resolution (720p/1080p) & Micro SFX
"""
import os
import re
import random
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from config.settings import get_ffmpeg_bin, load_settings, ASSETS_DIR, OUTPUT_DIR, TEMP_WORKSPACE
from engine.sfx_engine import build_transition_sfx_track

def offset_ass_subtitles(input_ass_path: str, output_ass_path: str, offset_seconds: float) -> str:
    """
    Offsets all Dialogue start and end timestamps in an ASS subtitle file by offset_seconds.
    Prevents subtitle desync when a flash teaser or intro is spliced at 0.0s.
    """
    if offset_seconds <= 0 or not os.path.exists(input_ass_path):
        if input_ass_path != output_ass_path and os.path.exists(input_ass_path):
            shutil.copy2(input_ass_path, output_ass_path)
        return output_ass_path

    def parse_ass_time(t_str: str) -> float:
        parts = t_str.strip().split(":")
        h = int(parts[0])
        m = int(parts[1])
        s = float(parts[2])
        return h * 3600 + m * 60 + s

    def format_time(seconds: float) -> str:
        if seconds < 0:
            seconds = 0.0
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int(round((seconds - int(seconds)) * 100))
        if centis >= 100:
            centis = 99
        return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"

    pattern = re.compile(r"^(Dialogue:\s*\d+,)(\d+:\d{2}:\d{2}\.\d{2}),(\d+:\d{2}:\d{2}\.\d{2})(,.*)$")
    out_lines = []
    with open(input_ass_path, "r", encoding="utf-8") as f:
        for line in f:
            m = pattern.match(line)
            if m:
                prefix, start_s, end_s, suffix = m.groups()
                new_start = format_time(parse_ass_time(start_s) + offset_seconds)
                new_end = format_time(parse_ass_time(end_s) + offset_seconds)
                out_lines.append(f"{prefix}{new_start},{new_end}{suffix}\n")
            else:
                out_lines.append(line)

    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.writelines(out_lines)
    return output_ass_path

def normalize_clip(
    input_mp4: str,
    out_mp4: str,
    target_duration: float,
    resolution: str = "1080p",
    orientation: str = "vertical",
    enable_ken_burns: bool = False
) -> str:
    ffmpeg_bin = get_ffmpeg_bin()
    is_horiz = orientation in ["horizontal", "landscape"]
    
    if is_horiz:
        w, h = (1280, 720) if resolution == "720p" else (1920, 1080)
    else:
        w, h = (720, 1280) if resolution == "720p" else (1080, 1920)
        
    ext = Path(input_mp4).suffix.lower()
    is_image = ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp"]

    if is_image:
        # Still images: use zoompan with duration bounded to target_duration
        d_frames = max(30, int(target_duration * 30))
        vf = (
            f"scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"zoompan=z='min(zoom+0.0012,1.20)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d_frames}:s={w}x{h}:fps=30,"
            "format=yuv420p,"
            "setsar=1"
        )
    elif enable_ken_burns:
        # Video clips: DO NOT use zoompan:d=150 (which freezes video frames for 5s).
        # Maintain natural video motion at 30fps with subtle 6% push-in and centered crop.
        scale_w, scale_h = int(w * 1.06), int(h * 1.06)
        vf = (
            f"scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h}:x='(in_w-{w})/2':y='(in_h-{h})/2',"
            "fps=30,"
            "format=yuv420p,"
            "setsar=1"
        )
    else:
        vf = (
            f"scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},"
            "fps=30,"
            "format=yuv420p,"
            "setsar=1"
        )

    cmd = [
        ffmpeg_bin, "-y",
        "-stream_loop", "-1",
        "-i", input_mp4,
        "-t", f"{target_duration:.3f}",
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-an",
        out_mp4
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    return out_mp4

def pick_bgm(user_song_name: str = None) -> str | None:
    songs_dir = ASSETS_DIR / "songs"
    if not songs_dir.exists():
        return None
    songs = [f for f in songs_dir.iterdir() if f.suffix.lower() in [".mp3", ".wav", ".m4a"]]
    if not songs:
        return None
    if user_song_name:
        for s in songs:
            if user_song_name.lower() in s.name.lower():
                return str(s)
    return str(random.choice(songs))

def escape_ffmpeg_path(path_str: str) -> str:
    clean = path_str.replace("\\", "/")
    if len(clean) > 1 and clean[1] == ":":
        clean = clean[0] + "\\:" + clean[2:]
    return clean

def render_master_video(
    normalized_clips: list,
    master_speech_mp3: str,
    subtitle_ass_path: str,
    total_audio_duration: float,
    task_temp_dir: str,
    bgm_volume: float = 0.15,
    enable_bgm: bool = True,
    scene_durations: list = None,
    orientation: str = "vertical",
    enable_teaser_splice: bool = False
) -> str:
    ffmpeg_bin = get_ffmpeg_bin()
    
    # 0. Teaser Splice: If requested for Shorts, extract 0.75s flash cut from a climax clip
    clips_to_stitch = list(normalized_clips)
    teaser_applied = False
    teaser_offset = 0.75
    
    if enable_teaser_splice and len(normalized_clips) >= 3 and orientation != "horizontal":
        try:
            climax_clip = normalized_clips[2]
            teaser_out = os.path.join(task_temp_dir, "teaser_flash.mp4")
            cmd_teaser = [
                ffmpeg_bin, "-y",
                "-i", climax_clip,
                "-t", f"{teaser_offset:.2f}",
                "-c", "copy",
                teaser_out
            ]
            subprocess.run(cmd_teaser, capture_output=True, text=True, check=True)
            clips_to_stitch = [teaser_out] + clips_to_stitch
            teaser_applied = True
            print(f"[VIDEO/TEASER] Injected {teaser_offset}s flash teaser splice at 0.0s.")
        except Exception as e:
            print(f"[WARN] Teaser splice failed: {e}")
            teaser_applied = False

    # Calculate master total video duration to avoid cutting off speech tail
    effective_offset = teaser_offset if teaser_applied else 0.0
    total_video_duration = total_audio_duration + effective_offset

    # 1. Concat normalized visuals
    concat_list_file = os.path.join(task_temp_dir, "video_concat_list.txt")
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for clip_path in clips_to_stitch:
            escaped_p = escape_ffmpeg_concat_path(clip_path)
            f.write(f"file '{escaped_p}'\n")
            
    temp_visuals = os.path.join(task_temp_dir, "stitched_visuals.mp4")
    cmd_concat = [
        ffmpeg_bin, "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list_file,
        "-c", "copy",
        temp_visuals
    ]
    subprocess.run(cmd_concat, capture_output=True, text=True, check=True)
    
    # Shift ASS subtitles if teaser is applied so dialogue matches delayed audio exactly
    if teaser_applied and subtitle_ass_path and os.path.exists(subtitle_ass_path):
        shifted_ass = os.path.join(task_temp_dir, "subtitles_shifted.ass")
        active_ass_path = offset_ass_subtitles(subtitle_ass_path, shifted_ass, teaser_offset)
    else:
        active_ass_path = subtitle_ass_path

    bgm_file = pick_bgm() if enable_bgm else None
    temp_master = os.path.join(task_temp_dir, "master_rendered.mp4")
    escaped_ass = escape_ffmpeg_path(active_ass_path)
    vf_chain = f"ass='{escaped_ass}'"

    # 2. Build Micro SFX Whoosh track
    sfx_track = None
    if scene_durations and len(scene_durations) > 1:
        sfx_out = os.path.join(task_temp_dir, "transitions_sfx.wav")
        adjusted_durations = [teaser_offset] + list(scene_durations) if teaser_applied else list(scene_durations)
        sfx_track = build_transition_sfx_track(adjusted_durations, total_video_duration, sfx_out, volume=0.35)

    # 3. Audio graph assembly with sidechain ducking & delay alignment
    inputs = ["-i", temp_visuals, "-i", master_speech_mp3]
    filter_parts = [f"[0:v]{vf_chain}[vout]"]
    input_idx = 2

    # Delay speech audio if teaser applied to match video timeline exactly
    if teaser_applied:
        delay_ms = int(teaser_offset * 1000)
        filter_parts.append(f"[1:a]adelay={delay_ms}|{delay_ms}[speech_delayed]")
        speech_ref = "[speech_delayed]"
    else:
        speech_ref = "[1:a]"

    if bgm_file and os.path.exists(bgm_file):
        inputs.extend(["-stream_loop", "-1", "-i", bgm_file])
        filter_parts.append(f"{speech_ref}asplit=2[speech_main][speech_sc]")
        filter_parts.append(f"[{input_idx}:a]volume={bgm_volume:.2f}[bgm_base]")
        filter_parts.append("[bgm_base][speech_sc]sidechaincompress=threshold=0.08:ratio=4:attack=50:release=300[bgm_ducked]")
        audio_inputs_to_mix = ["[speech_main]", "[bgm_ducked]"]
        input_idx += 1
    else:
        audio_inputs_to_mix = [speech_ref]

    if sfx_track and os.path.exists(sfx_track):
        inputs.extend(["-i", sfx_track])
        audio_inputs_to_mix.append(f"[{input_idx}:a]")
        input_idx += 1

    num_audio = len(audio_inputs_to_mix)
    if num_audio > 1 or teaser_applied:
        mix_inputs = "".join(audio_inputs_to_mix)
        if num_audio > 1:
            filter_parts.append(f"{mix_inputs}amix=inputs={num_audio}:duration=first:dropout_transition=2[aout]")
        else:
            filter_parts.append(f"{mix_inputs}anull[aout]")

        filter_complex_str = ";".join(filter_parts)
        cmd_master = [
            ffmpeg_bin, "-y",
            *inputs,
            "-filter_complex", filter_complex_str,
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", f"{total_video_duration:.3f}",
            "-shortest",
            "-map_metadata", "-1",
            "-fflags", "+bitexact",
            temp_master
        ]
    else:
        cmd_master = [
            ffmpeg_bin, "-y",
            *inputs,
            "-vf", vf_chain,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", f"{total_video_duration:.3f}",
            "-map_metadata", "-1",
            "-fflags", "+bitexact",
            temp_master
        ]
        
    subprocess.run(cmd_master, capture_output=True, text=True, check=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_output_name = f"global_wave_short_{timestamp}.mp4"
    final_output_path = str(OUTPUT_DIR / final_output_name)
    
    shutil.copy2(temp_master, final_output_path)
    return final_output_path
