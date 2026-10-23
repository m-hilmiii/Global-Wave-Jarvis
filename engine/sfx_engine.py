"""
Global Wave - Micro SFX Engine (ShortGPT Style)
Generates an audio track with transition whooshes aligned exactly to scene boundaries.
"""
import os
import wave
import struct
from pathlib import Path
from config.settings import ASSETS_DIR

SFX_DIR = ASSETS_DIR / "sfx"
WHOOSH_WAV = SFX_DIR / "whoosh.wav"
POP_WAV = SFX_DIR / "pop.wav"

def build_transition_sfx_track(scene_durations: list, total_duration: float, out_wav_path: str, volume: float = 0.35) -> str:
    """
    Creates a single WAV audio track containing whoosh SFX triggered at each scene transition.
    """
    if not WHOOSH_WAV.exists():
        return None

    # Read whoosh WAV
    with wave.open(str(WHOOSH_WAV), 'rb') as wf:
        sample_rate = wf.getframerate()
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        whoosh_frames = wf.readframes(wf.getnframes())

    total_samples = int(sample_rate * total_duration) + 1000
    track_samples = [0] * total_samples

    # Convert whoosh raw bytes to integer samples
    whoosh_data = struct.unpack(f"<{len(whoosh_frames)//2}h", whoosh_frames)

    # Place whoosh at transition boundaries: t = dur_0, dur_0 + dur_1, etc.
    current_time = 0.0
    for dur in scene_durations[:-1]:
        current_time += dur
        start_idx = int(current_time * sample_rate)
        
        for i, s in enumerate(whoosh_data):
            idx = start_idx + i
            if idx < total_samples:
                # Mix with volume scaling
                mixed = track_samples[idx] + int(s * volume)
                track_samples[idx] = max(-32768, min(32767, mixed))

    # Write final master SFX WAV
    os.makedirs(os.path.dirname(out_wav_path), exist_ok=True)
    with wave.open(out_wav_path, 'wb') as out_wf:
        out_wf.setnchannels(1)
        out_wf.setsampwidth(2)
        out_wf.setframerate(sample_rate)
        out_bytes = struct.pack(f"<{len(track_samples)}h", *track_samples)
        out_wf.writeframes(out_bytes)

    return out_wav_path