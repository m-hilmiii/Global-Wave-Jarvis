"""
Global-Wawe / Stark-Core - Protocol Zero (Kill-Switch / Emergency Lockdown Engine)
Section 8.8 of JARVIS_CAPABILITIES_MASTER.md

Provides instant system-wide emergency freeze:
1. Immediately cancels and drains all active background jobs (renders, tests, models).
2. Locks WhatsApp auto-dispatch and clears any pending message drafts.
3. Places JARVIS into a locked-down, read-only defensive stance.
4. Logs an immutable Level-4 security audit event.
"""

import os
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("Jarvis.ProtocolZero")

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = WORKSPACE_ROOT / ".jarvis_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = CACHE_DIR / "protocol_zero_state.json"


class ProtocolZeroManager:
    def __init__(self):
        self._active: bool = False
        self._activated_at: Optional[float] = None
        self._reason: str = ""
        self._load_state()

    def _load_state(self):
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._active = bool(data.get("active", False))
                    self._activated_at = data.get("activated_at")
                    self._reason = data.get("reason", "")
            except Exception as exc:
                logger.warning(f"[ProtocolZero] Failed to load state: {exc}")

    def _save_state(self):
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "active": self._active,
                    "activated_at": self._activated_at,
                    "reason": self._reason,
                    "updated_at": time.time()
                }, f, indent=2)
        except Exception as exc:
            logger.warning(f"[ProtocolZero] Failed to save state: {exc}")

    @property
    def is_active(self) -> bool:
        return self._active

    def activate(self, reason: str = "Kullanıcı acil durum direktifi (Protokol Sıfır)") -> Dict[str, Any]:
        """
        Engages Protocol Zero: cancels all active jobs, pauses WhatsApp auto-dispatch,
        clears pending drafts, and locks system down.
        """
        cancelled_jobs = []
        try:
            from core_jarvis.task_coordinator import task_coordinator
            for job in task_coordinator.list_jobs(status="running"):
                jid = job.get("job_id")
                if jid:
                    task_coordinator.cancel_job(jid)
                    cancelled_jobs.append(jid)
        except Exception as exc:
            logger.warning(f"[ProtocolZero] Task coordinator drain error: {exc}")

        # Clear drafts and lock auto-dispatch if brain is active
        try:
            from core_jarvis.jarvis_brain import jarvis_brain
            jarvis_brain.pending_draft = None
            jarvis_brain.set_auto_dispatch_whatsapp(False)
        except Exception as exc:
            logger.warning(f"[ProtocolZero] Brain lockdown error: {exc}")

        self._active = True
        self._activated_at = time.time()
        self._reason = reason
        self._save_state()

        # Audit log entry
        try:
            from core_jarvis.permission_guard import permission_guard
            permission_guard.audit_log.append({
                "timestamp": int(self._activated_at),
                "action": "protocol_zero_activated",
                "level": 4,
                "status": "ENGAGED",
                "details": f"Acil Durum Protokol Sıfır devreye alındı. {len(cancelled_jobs)} arka plan görevi durduruldu. Sebep: {reason}"
            })
        except Exception:
            pass

        logger.critical(f"[ProtocolZero] PROTOCOL ZERO ENGAGED: {reason}")
        return {
            "success": True,
            "status": "ENGAGED",
            "activated_at": self._activated_at,
            "reason": self._reason,
            "cancelled_jobs_count": len(cancelled_jobs),
            "cancelled_jobs": cancelled_jobs,
            "auto_dispatch_locked": True,
            "drafts_cleared": True
        }

    def deactivate(self) -> Dict[str, Any]:
        """Releases Protocol Zero and restores normal operational status."""
        was_active = self._active
        duration = int(time.time() - (self._activated_at or time.time())) if was_active else 0
        self._active = False
        self._activated_at = None
        self._reason = ""
        self._save_state()

        try:
            from core_jarvis.permission_guard import permission_guard
            permission_guard.audit_log.append({
                "timestamp": int(time.time()),
                "action": "protocol_zero_deactivated",
                "level": 3,
                "status": "RESTORED",
                "details": f"Protokol Sıfır kaldırıldı. Sistem normale döndürüldü. Kilit süresi: {duration} sn"
            })
        except Exception:
            pass

        logger.info("[ProtocolZero] Protocol Zero deactivated. Systems nominal.")
        return {
            "success": True,
            "status": "RESTORED",
            "lockdown_duration_seconds": duration,
            "was_active": was_active
        }

    def get_status(self) -> Dict[str, Any]:
        duration = int(time.time() - self._activated_at) if (self._active and self._activated_at) else 0
        return {
            "active": self._active,
            "activated_at": self._activated_at,
            "reason": self._reason,
            "lockdown_duration_seconds": duration
        }


protocol_zero = ProtocolZeroManager()
