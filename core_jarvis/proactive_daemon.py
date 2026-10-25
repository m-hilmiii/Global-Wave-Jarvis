"""
Global-Wawe / Stark-Core - Proactive Hardware & Job Watchdog (Stage 5)
Runs a lightweight, non-blocking background supervisor thread that monitors:
1. Critical RAM/VRAM thresholds (alerts if RAM > 92%)
2. TaskCoordinator background jobs (notifies when long video renders or tasks finish)
3. Registers notifications for the HUD toast and WhatsApp alert dispatcher
"""

import time
import threading
import logging
from typing import Dict, Any, List, Optional, Callable

from core_jarvis.vram_guard import vram_guard
from core_jarvis.task_coordinator import task_coordinator, JobStatus

logger = logging.getLogger("Jarvis.Watchdog")


class ProactiveWatchdog:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProactiveWatchdog, cls).__new__(cls)
            cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.interval_seconds = 20
        self.alert_history: List[Dict[str, Any]] = []
        self.lock = threading.RLock()
        self._last_ram_alert = 0.0
        self._known_job_statuses: Dict[str, str] = {}
        self.listeners: List[Callable[[Dict[str, Any]], None]] = []

    def start(self):
        """Starts the background supervisor thread."""
        with self.lock:
            if self.running:
                return
            self.running = True
            self.thread = threading.Thread(
                target=self._watch_loop,
                name="JARVIS-ProactiveWatchdog",
                daemon=True
            )
            self.thread.start()
            logger.info("[Watchdog] Proactive Watchdog supervisor started.")

    def stop(self):
        with self.lock:
            self.running = False

    def add_listener(self, callback: Callable[[Dict[str, Any]], None]):
        self.listeners.append(callback)

    def _emit_alert(self, category: str, title: str, message: str, level: str = "warning"):
        alert = {
            "timestamp": time.time(),
            "category": category,
            "title": title,
            "message": message,
            "level": level
        }
        with self.lock:
            self.alert_history.append(alert)
            if len(self.alert_history) > 50:
                self.alert_history.pop(0)

        logger.info(f"[Watchdog Alert] [{category}] {title}: {message}")
        for l in self.listeners:
            try:
                l(alert)
            except Exception as e:
                logger.debug(f"[Watchdog] Alert listener error: {e}")

    def _watch_loop(self):
        while self.running:
            try:
                now = time.time()

                # 1. Check RAM usage
                metrics = vram_guard.get_system_metrics()
                ram_pct = metrics.get("ram_used_pct") or 0
                if ram_pct >= 92 and (now - self._last_ram_alert > 180):
                    self._last_ram_alert = now
                    free_gb = metrics.get("ram_available_gb", 0)
                    self._emit_alert(
                        category="hardware_ram",
                        title="Yüksek Bellek (RAM) Uyarısı",
                        message=f"Sistem RAM'i %{ram_pct} doluluğa ulaştı (Yalnızca {free_gb} GB boş). Gereksiz uygulamaları kapatabilirsiniz.",
                        level="warning"
                    )

                # 2. Check Task Coordinator background jobs
                jobs = task_coordinator.list_jobs()
                for j in jobs:
                    jid = j["job_id"]
                    curr_status = j["status"]
                    prev_status = self._known_job_statuses.get(jid)

                    if prev_status == JobStatus.RUNNING and curr_status == JobStatus.COMPLETED:
                        self._emit_alert(
                            category="job_completed",
                            title="Görev Tamamlandı",
                            message=f"'{j['title']}' görevi başarıyla tamamlandı efendim ({j['elapsed_seconds']} sn).",
                            level="info"
                        )
                    elif prev_status == JobStatus.RUNNING and curr_status == JobStatus.FAILED:
                        self._emit_alert(
                            category="job_failed",
                            title="Görev Başarısız Oldu",
                            message=f"'{j['title']}' görevi hata verdi: {j.get('error', 'Bilinmeyen hata')}",
                            level="error"
                        )

                    self._known_job_statuses[jid] = curr_status

            except Exception as exc:
                logger.debug(f"[Watchdog] Loop iteration warning: {exc}")

            time.sleep(self.interval_seconds)

    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self.lock:
            return list(self.alert_history[-limit:])


proactive_watchdog = ProactiveWatchdog()
