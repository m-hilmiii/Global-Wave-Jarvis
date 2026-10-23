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
import random
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from config.settings import get_ffmpeg_bin, load_settings, ASSETS_DIR, OUTPUT_DIR, TEMP_WORKSPACE
from engine.sfx_engine import build_transition_sfx_track

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
        
    if enable_ken_burns:
        # Subtle, high-end documentary Ken Burns slow zoom
        scale_w, scale_h = int(w * 1.12), int(h * 1.12)
        vf = (
            f"scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase,"
            f"crop={scale_w}:{scale_h},"
            f"zoompan=z='min(zoom+0.0006,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=150:s={w}x{h},"
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
    
    # 0. Teaser Splice (Faz 3): If requested for Shorts, extract 0.7s flash cut from a climax clip
    clips_to_stitch = list(normalized_clips)
    if enable_teaser_splice and len(normalized_clips) >= 3 and orientation != "horizontal":
        try:
            climax_clip = normalized_clips[2]
            teaser_out = os.path.join(task_temp_dir, "teaser_flash.mp4")
            cmd_teaser = [
                ffmpeg_bin, "-y",
                "-i", climax_clip,
                "-t", "0.75",
                "-c", "copy",
                teaser_out
            ]
            subprocess.run(cmd_teaser, capture_output=True, text=True, check=True)
            clips_to_stitch = [teaser_out] + clips_to_stitch
            print("[VIDEO/TEASER] Injected 0.75s flash teaser splice at 0.0s.")
        except Exception as e:
            print(f"[WARN] Teaser splice failed: {e}")

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
    
    bgm_file = pick_bgm() if enable_bgm else None
    temp_master = os.path.join(task_temp_dir, "master_rendered.mp4")
    escaped_ass = escape_ffmpeg_path(subtitle_ass_path)
    vf_chain = f"ass='{escaped_ass}'"

    # 2. Build Micro SFX Whoosh track
    sfx_track = None
    if scene_durations and len(scene_durations) > 1:
        sfx_out = os.path.join(task_temp_dir, "transitions_sfx.wav")
        sfx_track = build_transition_sfx_track(scene_durations, total_audio_duration, sfx_out, volume=0.35)

    # 3. Audio graph assembly with sidechain ducking
    inputs = ["-i", temp_visuals, "-i", master_speech_mp3]
    filter_parts = [f"[0:v]{vf_chain}[vout]"]
    input_idx = 2

    if bgm_file and os.path.exists(bgm_file):
        inputs.extend(["-stream_loop", "-1", "-i", bgm_file])
        filter_parts.append("[1:a]asplit=2[speech_main][speech_sc]")
        filter_parts.append(f"[{input_idx}:a]volume={bgm_volume:.2f}[bgm_base]")
        filter_parts.append("[bgm_base][speech_sc]sidechaincompress=threshold=0.08:ratio=4:attack=50:release=300[bgm_ducked]")
        audio_inputs_to_mix = ["[speech_main]", "[bgm_ducked]"]
        input_idx += 1
    else:
        audio_inputs_to_mix = ["[1:a]"]

    if sfx_track and os.path.exists(sfx_track):
        inputs.extend(["-i", sfx_track])
        audio_inputs_to_mix.append(f"[{input_idx}:a]")
        input_idx += 1

    num_audio = len(audio_inputs_to_mix)
    if num_audio > 1:
        mix_inputs = "".join(audio_inputs_to_mix)
        filter_parts.append(f"{mix_inputs}amix=inputs={num_audio}:duration=first:dropout_transition=2[aout]")
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
            "-t", f"{total_audio_duration:.3f}",
            "-shortest",
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
            "-t", f"{total_audio_duration:.3f}",
            temp_master
        ]
        
    subprocess.run(cmd_master, capture_output=True, text=True, check=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_output_name = f"global_wave_short_{timestamp}.mp4"
    final_output_path = str(OUTPUT_DIR / final_output_name)
    
    shutil.copy2(temp_master, final_output_path)
    return final_output_path