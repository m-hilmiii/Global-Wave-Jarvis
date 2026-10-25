"""
Global-Wawe / Stark-Core - Reality-Anchored Memory Engine (Truth-Over-Memory)
Ensures Jarvis's memory is never out-of-sync with real disk, git, test, and system state.
Implements:
1. Persistent Preferences (directories, cost limits, working style)
2. Project Knowledge Base (Global Wave architecture, completed tasks, open milestones)
3. Task State Tracker (active job, current step, blockers)
4. Reality Sync: Verifies truth via git diff, modified timestamps, and service health.
"""

import os
import json
import time
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("Jarvis.RealityMemory")

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = WORKSPACE_DIR / "config"
STATE_FILE = CONFIG_DIR / "jarvis_reality_state.json"
PREFS_FILE = CONFIG_DIR / "jarvis_preferences.json"

DEFAULT_PREFERENCES = {
    "owner": "Mücahit Hilmi",
    "honorific": "Sayın Hilmi",
    "autonomy_level": "balanced",  # cautious | balanced | high
    "ai_mode": "hybrid_local_first",
    "hardware_profile": {
        "cpu": "Intel Core i5-14400F",
        "gpu": "AMD Radeon RX 9060 XT",
        "ram_gb": 16
    },
    "max_retry_attempts": 3,
    "allowed_workspace_roots": [str(WORKSPACE_DIR)],
    "cost_limit_daily_usd": 0.0  # Zero-cost local-first priority
}

DEFAULT_PROJECT_STATE = {
    "project_name": "Global-Wave (formerly Zenvia Media)",
    "active_version": "v5.0",
    "last_synced_timestamp": 0,
    "last_known_commit": "",
    "last_known_branch": "main",
    "uncommitted_changes_count": 0,
    "active_task": None,
    "task_history": [],
    "recent_milestones": [
        "Wake-on-LAN (WOL) 102-byte magic packet & discovery engine implemented",
        "4-Level Permission Guard (Auto, Bounded, Confirmed, Forbidden) activated",
        "Contacts Hub & WhatsApp daemon bridge integrated",
        "2-Stage FFmpeg Pre-normalization & OneDrive isolation completed"
    ]
}

class RealityMemory:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.preferences = self._load_json(PREFS_FILE, DEFAULT_PREFERENCES)
        self.state = self._load_json(STATE_FILE, DEFAULT_PROJECT_STATE)

    def _load_json(self, path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read {path}: {e}, using default")
        return dict(default)

    def _save_json(self, path: Path, data: Dict[str, Any]):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save {path}: {e}")

    def sync_with_reality(self) -> Dict[str, Any]:
        """
        Enforces Truth-Over-Memory:
        Queries real git state, modified files, and service ports to synchronize memory.
        """
        reality_snapshot = {
            "timestamp": time.time(),
            "branch": "unknown",
            "commit": "unknown",
            "dirty": False,
            "changed_files": [],
            "open_services": {},
            "active_task": self.state.get("active_task")
        }

        # 1. Git State
        try:
            branch_res = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, cwd=str(WORKSPACE_DIR), timeout=4
            )
            if branch_res.returncode == 0:
                reality_snapshot["branch"] = branch_res.stdout.strip()

            commit_res = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, cwd=str(WORKSPACE_DIR), timeout=4
            )
            if commit_res.returncode == 0:
                reality_snapshot["commit"] = commit_res.stdout.strip()

            status_res = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, cwd=str(WORKSPACE_DIR), timeout=4
            )
            if status_res.returncode == 0:
                lines = [l.strip() for l in status_res.stdout.splitlines() if l.strip()]
                reality_snapshot["changed_files"] = lines
                reality_snapshot["dirty"] = len(lines) > 0
                reality_snapshot["uncommitted_changes_count"] = len(lines)
        except Exception as e:
            logger.warning(f"Git reality sync error: {e}")

        # 2. Check Service Ports (e.g. 7860 Web HUD, 11434 Ollama)
        for name, port in [("Web_HUD", 7860), ("Ollama", 11434)]:
            is_open = self._check_port("127.0.0.1", port)
            reality_snapshot["open_services"][name] = {"port": port, "active": is_open}

        # Update persistent memory state
        self.state["last_synced_timestamp"] = reality_snapshot["timestamp"]
        self.state["last_known_commit"] = reality_snapshot["commit"]
        self.state["last_known_branch"] = reality_snapshot["branch"]
        self.state["uncommitted_changes_count"] = reality_snapshot.get("uncommitted_changes_count", 0)
        self._save_json(STATE_FILE, self.state)

        return reality_snapshot

    def _check_port(self, host: str, port: int) -> bool:
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                return s.connect_ex((host, port)) == 0
        except Exception:
            return False

    def resume_context(self) -> Dict[str, Any]:
        """
        Answers 'Jarvis, geçen sefer kaldığımız yerden devam et.'
        Produces a grounded summary comparing stored expectations vs real disk state.
        """
        reality = self.sync_with_reality()
        active_task = self.state.get("active_task")

        summary = {
            "status": "ready",
            "git_branch": reality["branch"],
            "current_commit": reality["commit"],
            "has_uncommitted_work": reality["dirty"],
            "uncommitted_files": reality["changed_files"],
            "active_task": active_task,
            "recent_milestones": self.state.get("recent_milestones", [])[-3:],
            "services": reality["open_services"]
        }

        if active_task and active_task.get("status") == "in_progress":
            summary["recommendation"] = (
                f"Yarım kalan görev tespit edildi: '{active_task.get('name')}'. "
                f"Adım: {active_task.get('current_step')}/{active_task.get('total_steps')}. Devam edilebilir."
            )
        elif reality["dirty"]:
            summary["recommendation"] = (
                f"Çalışma alanında {len(reality['changed_files'])} adet kaydedilmemiş değişiklik var. "
                "Önce testleri çalıştırıp durumu doğrulamamızı öneririm."
            )
        else:
            summary["recommendation"] = "Sistem temiz durumda. Yeni bir göreve veya planlanan geliştirmeye hazırız."

        return summary

    def set_active_task(self, name: str, plan_steps: List[str]) -> Dict[str, Any]:
        """
        Tracks a high-level task state across multi-step execution.
        """
        task = {
            "name": name,
            "status": "in_progress",
            "current_step": 0,
            "total_steps": len(plan_steps),
            "steps": [{"step": s, "completed": False, "result": None} for s in plan_steps],
            "started_at": time.time(),
            "updated_at": time.time()
        }
        self.state["active_task"] = task
        self._save_json(STATE_FILE, self.state)
        return task

    def update_task_step(self, step_index: int, completed: bool, result: Optional[Any] = None):
        task = self.state.get("active_task")
        if not task:
            return
        if 0 <= step_index < len(task.steps if hasattr(task, 'steps') else task.get("steps", [])):
            task["steps"][step_index]["completed"] = completed
            task["steps"][step_index]["result"] = result
            task["current_step"] = step_index + 1
            task["updated_at"] = time.time()
            if task["current_step"] >= task["total_steps"]:
                task["status"] = "completed"
                # Archive to task history
                self.state.setdefault("task_history", []).append(task)
            self._save_json(STATE_FILE, self.state)

    def mark_task_failed(self, reason: str):
        task = self.state.get("active_task")
        if task:
            task["status"] = "failed"
            task["failure_reason"] = reason
            task["updated_at"] = time.time()
            self.state.setdefault("task_history", []).append(task)
            self._save_json(STATE_FILE, self.state)


reality_memory = RealityMemory()
