"""
Global-Wawe - LTX-2.5 WSL Video Diffusion Engine
Bridges Global-Wawe directly to the high-performance WSL2 ROCm 7.2 LTX-2.5 video generator.
Supports sequential multi-scene generation with Image-to-Video (I2V) last-frame continuity.
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from core_jarvis.vram_guard import vram_guard

logger = logging.getLogger("GlobalWawe.LTX")

LTX_DIR_WIN = Path(r"C:\Users\unalm\OneDrive\Masaüstü\LTX-2-main")
LTX_DIR_WSL = "/mnt/c/Users/unalm/OneDrive/Masaüstü/LTX-2-main"

class LTXVideoEngine:
    def __init__(self, ltx_dir: Path = LTX_DIR_WIN):
        self.ltx_dir = ltx_dir
        self.script_path_wsl = f"{LTX_DIR_WSL}/scripts/generate_video.sh"

    def generate_scene(
        self,
        prompt: str,
        output_filename: str,
        width: int = 704,
        height: int = 1280,
        num_frames: int = 97,
        frame_rate: int = 24,
        input_image_wsl: Optional[str] = None,
        image_strength: float = 0.95
    ) -> Dict[str, Any]:
        """Generates a single video scene in WSL2."""
        vram_guard.prepare_for_diffusion()
        
        output_rel = f"story_output/{output_filename}"
        output_full_win = self.ltx_dir / "story_output" / output_filename
        output_full_win.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "wsl", "-e", "bash", "-c",
            f"cd {LTX_DIR_WSL} && ./scripts/generate_video.sh "
            f"\"{prompt}\" \"{output_rel}\" {width} {height} {num_frames} {frame_rate} "
            f"\"{input_image_wsl or ''}\" {image_strength}"
        ]

        logger.info(f"[LTX] Launching WSL render for {output_filename}...")
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if res.returncode == 0 and output_full_win.exists():
                logger.info(f"[LTX] Successfully generated scene: {output_full_win}")
                return {
                    "success": True,
                    "path": str(output_full_win),
                    "filename": output_filename
                }
            else:
                logger.error(f"[LTX Error] {res.stderr}")
                return {"success": False, "error": res.stderr}
        except Exception as e:
            logger.error(f"[LTX Exception] {e}")
            return {"success": False, "error": str(e)}

    def extract_last_frame(self, video_path: str, output_image_path: str) -> bool:
        """Extracts the final frame of a video using FFmpeg for I2V scene continuity."""
        cmd = [
            "ffmpeg", "-y", "-sseof", "-1", "-i", video_path,
            "-update", "1", "-q:v", "1", output_image_path
        ]
        res = subprocess.run(cmd, capture_output=True)
        return res.returncode == 0 and os.path.exists(output_image_path)

ltx_video_engine = LTXVideoEngine()
