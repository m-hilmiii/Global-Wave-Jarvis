"""
Global-Wave & LTX-2 Studio Bridge for JARVIS (v3.0)
Decouples JARVIS AI Operating System from Global-Wave Media Agency & LTX-2 Video Factory.
Provides Zero-VRAM Evacuation, autonomous background monitoring, and seamless cross-folder communication.
"""

import os
import sys
import time
import subprocess
import threading
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("Jarvis.StudioBridge")

CURRENT_DIR = Path(__file__).resolve().parent.parent.parent  # Jarvis root
PARENT_DIR = CURRENT_DIR.parent                             # Jarvis master folder (or Masaüstü)

# Locate Global Wawe directory
GLOBAL_WAVE_DIR: Path = CURRENT_DIR
for candidate in [
    PARENT_DIR / "Global Wawe",
    PARENT_DIR / "Global-Wave",
    PARENT_DIR / "Global-Wawe",
    CURRENT_DIR.parent / "Global-Wawe",
    CURRENT_DIR
]:
    if (candidate / "engine").exists():
        GLOBAL_WAVE_DIR = candidate
        break

# Locate LTX-2-main directory
LTX_DIR: Path = PARENT_DIR / "LTX-2-main"
if not (LTX_DIR / "scripts").exists():
    for candidate in [
        PARENT_DIR / "LTX-2-main",
        Path("/mnt/c/Users/unalm/OneDrive/Masaüstü/Jarvis/LTX-2-main"),
        Path("/mnt/c/Users/unalm/OneDrive/Masaüstü/LTX-2-main"),
        Path("/mnt/c/Users/unalm/OneDrive/Masaüstü/Github Repoları/LTX-2-main")
    ]:
        if (candidate / "scripts").exists():
            LTX_DIR = candidate
            break

# Ensure Global Wave is dynamically resolvable on sys.path
if GLOBAL_WAVE_DIR.exists() and str(GLOBAL_WAVE_DIR) not in sys.path:
    sys.path.insert(0, str(GLOBAL_WAVE_DIR))


class StudioBridge:
    """
    Orchestrates the Global Wave Media Studio and LTX-2 Video Factory
    while ensuring strict 16GB VRAM isolation for AMD Radeon RX 9060 XT.
    """
    def __init__(self):
        self.global_wave_dir = GLOBAL_WAVE_DIR
        self.ltx_dir = LTX_DIR
        self._ltx_lock = threading.Lock()
        self._active_ltx_job: Optional[Dict[str, Any]] = None

    def get_studio_paths(self) -> Dict[str, str]:
        """Returns the physical decoupled locations of all 3 departments."""
        return {
            "jarvis_core_dir": str(CURRENT_DIR),
            "global_wave_dir": str(self.global_wave_dir),
            "ltx_factory_dir": str(self.ltx_dir),
            "ltx_models_ready": (self.ltx_dir / "models" / "ltx-2.5").exists()
        }

    def is_ltx_rendering(self) -> bool:
        """Checks if LTX-2 heavy video generation is currently consuming the 16GB VRAM."""
        with self._ltx_lock:
            if not self._active_ltx_job:
                return False
            # Check if process is still alive
            proc: Optional[subprocess.Popen] = self._active_ltx_job.get("process")
            if proc and proc.poll() is None:
                return True
            self._active_ltx_job = None
            return False

    def get_ltx_status_summary(self) -> str:
        """Returns friendly status for WhatsApp and Web HUD while LTX is active."""
        if not self.is_ltx_rendering():
            return "LTX-2 fabrikası şu an boşta. Video üretimi başlatılabilir efendim."
        job = self._active_ltx_job or {}
        elapsed = int(time.time() - job.get("start_time", time.time()))
        mins, secs = divmod(elapsed, 60)
        return (
            f"🎬 **LTX-2.5 Video Fabrikası Çalışıyor:**\n\n"
            f"• **Görev:** {job.get('task_name', 'Video Render')}\n"
            f"• **Geçen Süre:** {mins} dk {secs} sn\n"
            f"• **VRAM Koruma:** Devrede (%100 GPU VRAM LTX-2'ye tahsis edildi)\n\n"
            f"Render tamamlandığında sizi otomatik olarak bilgilendireceğim balım!"
        )

    def trigger_ltx_video(
        self,
        prompt: str,
        frames: int = 49,
        width: int = 704,
        height: int = 1280,
        output_name: str = "output.mp4",
        image_input: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes LTX-2 with Zero-VRAM Evacuation Protocol:
        1. Completely unloads Ollama models from VRAM (0 MB VRAM)
        2. Spawns LTX-2.5 generation on RX 9060 XT
        3. Monitors output and restores qwen3:8b primary brain upon completion
        """
        from core_jarvis.tools.model_manager import model_manager

        if self.is_ltx_rendering():
            return {
                "success": False,
                "error": "Şu anda devam eden aktif bir LTX-2 render işlemi bulunuyor. Lütfen tamamlanmasını bekleyin.",
                "status": self.get_ltx_status_summary()
            }

        out_path = self.ltx_dir / output_name

        # 1. Zero-VRAM Evacuation: Flush Ollama models so full 16GB VRAM belongs to LTX-2
        logger.info("[StudioBridge] Evacuating VRAM for LTX-2 heavy render...")
        try:
            model_manager.prepare_vram_for_model("__NONE__")
            # Force keep_alive 0 on active models
            for r in model_manager.get_running_models():
                model_manager.session.post(
                    f"{model_manager.ollama_url}/api/generate",
                    json={"model": r.get("name"), "keep_alive": 0},
                    timeout=2
                )
        except Exception as exc:
            logger.warning(f"[StudioBridge] VRAM evacuation warning: {exc}")

        # 2. Build shell command targeting generate_video.sh
        gen_script = self.ltx_dir / "scripts" / "generate_video.sh"
        cmd = [
            "bash",
            str(gen_script),
            prompt,
            str(out_path),
            str(frames),
            str(height),
            str(width)
        ]
        if image_input and Path(image_input).exists():
            cmd.append(str(image_input))

        # 3. Launch background worker thread
        def _worker():
            start_t = time.time()
            try:
                logger.info(f"[StudioBridge] Spawning LTX-2 process: {' '.join(cmd)}")
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(self.ltx_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                with self._ltx_lock:
                    self._active_ltx_job = {
                        "process": proc,
                        "prompt": prompt,
                        "output_path": str(out_path),
                        "start_time": start_t,
                        "task_name": f"LTX-2 ({frames} kare, {width}x{height})"
                    }

                stdout, stderr = proc.communicate()
                elapsed = round(time.time() - start_t, 1)

                if proc.returncode == 0 and out_path.exists():
                    logger.info(f"[StudioBridge] LTX-2 generation succeeded in {elapsed}s: {out_path}")
                else:
                    logger.error(f"[StudioBridge] LTX-2 generation failed (code {proc.returncode}): {stderr}")

            except Exception as e:
                logger.error(f"[StudioBridge] LTX-2 worker exception: {e}", exc_info=True)
            finally:
                with self._ltx_lock:
                    self._active_ltx_job = None
                # Restore primary brain back into VRAM
                logger.info("[StudioBridge] Render finished. Pre-warming Primary Brain back into VRAM...")
                model_manager._prewarm_primary_brain()

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

        return {
            "success": True,
            "message": f"🚀 LTX-2.5 video üretimi başlatıldı balım! (Çıktı: {output_name})\n\nVRAM güvenliği için Ollama modelleri boşaltıldı. Render tamamlandığında sizi otomatik bilgilendireceğim.",
            "output_target": str(out_path),
            "estimated_frames": frames
        }

    def trigger_story_generator(self, scene_num: Optional[int] = None, all_scenes: bool = False) -> Dict[str, Any]:
        """Triggers the 11-scene continuous Cyberpunk story pipeline with I2V frame-chaining."""
        from core_jarvis.tools.model_manager import model_manager

        if self.is_ltx_rendering():
            return {
                "success": False,
                "error": "Şu anda devam eden aktif bir LTX-2 render işlemi var.",
                "status": self.get_ltx_status_summary()
            }

        # Evacuate VRAM
        try:
            model_manager.prepare_vram_for_model("__NONE__")
            for r in model_manager.get_running_models():
                model_manager.session.post(
                    f"{model_manager.ollama_url}/api/generate",
                    json={"model": r.get("name"), "keep_alive": 0},
                    timeout=2
                )
        except Exception:
            pass

        story_py = self.ltx_dir / "scripts" / "story_generator.py"
        py_bin = "/root/ltx_env/bin/python3" if Path("/root/ltx_env/bin/python3").exists() else "python3"

        args = [py_bin, str(story_py)]
        if all_scenes:
            args.append("--all")
            task_desc = "11 Sahnelik 45s Full Kesintisiz Film"
        elif scene_num is not None:
            args.extend(["--scene", str(scene_num)])
            task_desc = f"Sahne {scene_num} Üretimi"
        else:
            args.append("--list")
            task_desc = "Senaryo Listeleme"

        def _worker():
            try:
                proc = subprocess.Popen(args, cwd=str(self.ltx_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                with self._ltx_lock:
                    self._active_ltx_job = {
                        "process": proc,
                        "task_name": task_desc,
                        "start_time": time.time()
                    }
                proc.communicate()
            except Exception as exc:
                logger.error(f"[StudioBridge] Story worker error: {exc}")
            finally:
                with self._ltx_lock:
                    self._active_ltx_job = None
                model_manager._prewarm_primary_brain()

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

        return {
            "success": True,
            "message": f"🎬 **LTX-2.5 Hikaye Fabrikası Başlatıldı:** {task_desc}\n\n16GB VRAM LTX-2'ye tahsis edildi. Arka planda işleniyor balım!",
            "task": task_desc
        }

    def fetch_shorts_ideas(self) -> Dict[str, Any]:
        """Fetches viral Shorts ideas leveraging Global Wave's transkript knowledge."""
        try:
            from core_jarvis.tools.knowledge_indexer import knowledge_indexer
            hits = knowledge_indexer.search("youtube shorts kanca hook izlenme", top_k=2).get("results", [])
            rag_tip = hits[0]["preview"][:180] if hits else "Merak uyandıran kanca ve ilk 3 saniye soru formatı."
        except Exception:
            rag_tip = "İlk 3 saniye merak kancası ve hızlı sahne kesimleri."

        ideas = [
            {
                "title": "Büyük Çip Devrimi (Hardware & AI)",
                "hook": "NVIDIA'nın tahtı sallanıyor mu? Açık kaynak çipler pazarı değiştiriyor!",
                "duration": "42s",
                "engine": "LTX-2.5 Cyberpunk / Global Wave"
            },
            {
                "title": "Sıfır Sermaye ile Yerel AI Ajansı (SMMA / AI Agency)",
                "hook": "Bulut API'lerine binlerce dolar ödemeyi bıraktım. İşte yerel çözüm!",
                "duration": "48s",
                "engine": "Global Wave Auto-Pipeline"
            },
            {
                "title": "Görünmez Veri Tehlikesi (Cybersecurity)",
                "hook": "Telefonunuz sizi gizlice dinliyor mu? Bu ayarı hemen kapatın!",
                "duration": "38s",
                "engine": "LTX-2.5 Noir Style"
            }
        ]
        return {
            "ideas": ideas,
            "rag_tip": rag_tip
        }


studio_bridge = StudioBridge()
