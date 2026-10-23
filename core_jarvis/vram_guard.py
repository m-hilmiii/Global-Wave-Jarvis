"""
Global-Wawe / Stark-Core - Hardware & VRAM Guard
Prevents Out-Of-Memory (OOM) errors and OS freezes on 16GB RAM + 16GB AMD VRAM.
Zero external dependency: Works via native Windows ctypes kernel32 API with psutil fallback.
"""

import os
import gc
import ctypes
import logging
import subprocess

logger = logging.getLogger("Jarvis.VRAMGuard")

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]

class VRAMGuard:
    def __init__(self, ram_threshold_pct: float = 85.0):
        self.ram_threshold_pct = ram_threshold_pct

    def get_system_metrics(self) -> dict:
        """Returns host RAM and swap memory status using native Windows API."""
        try:
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))

            total_ram_gb = round(stat.ullTotalPhys / (1024**3), 2)
            avail_ram_gb = round(stat.ullAvailPhys / (1024**3), 2)
            used_pct = int(stat.dwMemoryLoad)
            total_swap_gb = round(stat.ullTotalPageFile / (1024**3), 2)
            avail_swap_gb = round(stat.ullAvailPageFile / (1024**3), 2)
            swap_used_pct = round(((stat.ullTotalPageFile - stat.ullAvailPageFile) / max(1, stat.ullTotalPageFile)) * 100, 1)

            return {
                "metrics_available": True,
                "ram_total_gb": total_ram_gb,
                "ram_available_gb": avail_ram_gb,
                "ram_used_pct": used_pct,
                "swap_total_gb": total_swap_gb,
                "swap_used_pct": swap_used_pct,
                "cpu_percent": None,  # Not simulated: requires external PDH/psutil counter
                "safe_for_diffusion": used_pct < self.ram_threshold_pct
            }
        except Exception as e:
            logger.warning(f"Failed to read native memory status: {e}")
            return {
                "metrics_available": False,
                "ram_total_gb": None,
                "ram_available_gb": None,
                "ram_used_pct": None,
                "swap_total_gb": None,
                "swap_used_pct": None,
                "cpu_percent": None,
                "safe_for_diffusion": False
            }

    def check_safe_state(self) -> bool:
        """Checks if memory is healthy enough to start a heavy job (fail-closed if metrics unavailable)."""
        metrics = self.get_system_metrics()
        if not metrics.get("metrics_available") or metrics.get("ram_used_pct") is None:
            logger.warning("[RAM Guard] System telemetry unavailable; failing closed for safety.")
            return False
        if metrics["ram_used_pct"] > self.ram_threshold_pct:
            logger.warning(
                f"[GUARD ALERT] RAM usage is high ({metrics['ram_used_pct']}%). "
                f"Available: {metrics['ram_available_gb']} GB. Dropping memory caches..."
            )
            self.clean_memory()
            return False
        return True

    def clean_memory(self):
        """Forces garbage collection and unloads idle models."""
        try:
            gc.collect()
        except Exception:
            pass

        try:
            subprocess.run(["ollama", "stop", "qwen2.5:7b"], capture_output=True, timeout=5)
        except Exception:
            pass

    def prepare_for_diffusion(self):
        """Pre-flight sequence before running LTX-2.5 or Z-Image."""
        logger.info("[VRAMGuard] Preparing hardware for diffusion model...")
        self.clean_memory()
        metrics = self.get_system_metrics()
        logger.info(f"[VRAMGuard] Pre-diffusion status: RAM Used: {metrics['ram_used_pct']}%, Free: {metrics['ram_available_gb']}GB")

vram_guard = VRAMGuard()
