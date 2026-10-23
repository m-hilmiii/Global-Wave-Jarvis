"""
Global-Wawe - LTX-2.5 WSL Video Diffusion Engine
Bridges Global-Wawe directly to the high-performance WSL2 ROCm 7.2 LTX-2.5 video generator.
Supports sequential multi-scene generation with Image-to-Video (I2V) last-frame continuity.
Secure execution with shell argument sanitization and portable path resolution.
"""

import os
import re
import shlex
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from core_jarvis.vram_guard import vram_guard

logger = logging.getLogger("GlobalWawe.LTX")

# Configurable paths with environment overrides and portable fallback
DEFAULT_WIN_PATH = Path(os.environ.get("LTX_DIR_WIN", r"C:\Users\unalm\OneDrive\Masaüstü\LTX-2-main"))
DEFAULT_WSL_PATH = os.environ.get("LTX_DIR_WSL", "/mnt/c/Users/unalm/OneDrive/Masaüstü/LTX-2-main")

class LTXVideoEngine:
    def __init__(self, ltx_dir: Path = DEFAULT_WIN_PATH, wsl_dir: str = DEFAULT_WSL_PATH):
        self.ltx_dir = Path(ltx_dir)
        self.wsl_dir = wsl_dir
        self.script_path_wsl = f"{self.wsl_dir}/scripts/generate_video.sh"

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
        """Generates a single video scene in WSL2 with sanitized parameters and path traversal guard."""
        vram_guard.prepare_for_diffusion()
        
        # Path traversal guard: strictly restrict filename to alphanumeric, dots, dashes, and underscores
        safe_filename = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", Path(output_filename).name)
        if not safe_filename.endswith(".mp4"):
            safe_filename += ".mp4"

        output_rel = f"story_output/{safe_filename}"
        output_full_win = (self.ltx_dir / "story_output" / safe_filename).resolve()
        
        # Verify destination stays inside ltx_dir
        target_dir = (self.ltx_dir / "story_output").resolve()
        if not str(output_full_win).startswith(str(target_dir)):
            return {"success": False, "error": "Geçersiz çıktı yolu: Güvenlik sınırı dışına çıkılamaz."}
            
        output_full_win.parent.mkdir(parents=True, exist_ok=True)

        # Secure argument quoting to prevent WSL shell injection
        quoted_wsl_dir = shlex.quote(self.wsl_dir)
        quoted_prompt = shlex.quote(prompt.strip())
        quoted_output_rel = shlex.quote(output_rel)
        quoted_img = shlex.quote(input_image_wsl.strip()) if input_image_wsl else "''"

        bash_cmd = (
            f"cd {quoted_wsl_dir} && ./scripts/generate_video.sh "
            f"{quoted_prompt} {quoted_output_rel} {int(width)} {int(height)} "
            f"{int(num_frames)} {int(frame_rate)} {quoted_img} {float(image_strength)}"
        )

        cmd = ["wsl", "-e", "bash", "-c", bash_cmd]

        logger.info(f"[LTX] Launching WSL render for {safe_filename}...")
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if res.returncode == 0 and output_full_win.exists():
                logger.info(f"[LTX] Successfully generated scene: {output_full_win}")
                return {
                    "success": True,
                    "path": str(output_full_win),
                    "filename": safe_filename
                }
            else:
                logger.error(f"[LTX Error] {res.stderr}")
                return {"success": False, "error": res.stderr}
        except Exception as e:
            logger.error(f"[LTX Exception] {e}")
            return {"success": False, "error": str(e)}

    def extract_last_frame(self, video_path: str, output_image_path: str) -> bool:
        """Extracts the final frame of a video using FFmpeg for I2V scene continuity."""
        if not os.path.exists(video_path):
            return False
        cmd = [
            "ffmpeg", "-y", "-sseof", "-1", "-i", video_path,
            "-update", "1", "-q:v", "1", output_image_path
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=30)
            return res.returncode == 0 and os.path.exists(output_image_path)
        except Exception as e:
            logger.warning(f"Failed to extract last frame: {e}")
            return False

ltx_video_engine = LTXVideoEngine()
