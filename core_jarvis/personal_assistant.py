"""
Global-Wawe / Stark-Core - Executive Personal Assistant Engine (Stage 5)
Handles:
1. Daily Briefing & Agenda Aggregator ("Jarvis, bugün ne yapmam gerekiyor?")
2. Task & Project Board Manager (priorities, due dates, overdue detection)
3. Calendar & Reminder Engine (datetime triggers, lead alerts)
4. Executive Quick Notes & Document Management
5. Communication & Inbound Triage Summary (WhatsApp, Telegram, Gmail)
"""

import os
import json
import time
import uuid
import threading
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Optional

from core_jarvis.reality_memory import reality_memory
from core_jarvis.permission_guard import permission_guard, PermissionLevel

logger = logging.getLogger("Jarvis.PersonalAssistant")

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = WORKSPACE_DIR / "config"
AGENDA_FILE = CONFIG_DIR / "personal_agenda.json"

AGENDA_LOCK = threading.RLock()

DEFAULT_AGENDA = {
    "tasks": [
        {
            "id": "task_init_1",
            "title": "Global Wave v5.0 Master Mimarisi Doğrulaması",
            "category": "project",
            "priority": "high",
            "due_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "completed",
            "created_at": time.time() - 3600,
            "completed_at": time.time()
        },
        {
            "id": "task_init_2",
            "title": "Zenvia içerik motoru kalite kontrolü (QC) testleri",
            "category": "content",
            "priority": "urgent",
            "due_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "in_progress",
            "created_at": time.time() - 1800,
            "completed_at": None
        }
    ],
    "reminders": [
        {
            "id": "rem_init_1",
            "title": "YouTube Studio haftalık analitik kontrolü",
            "datetime_iso": f"{datetime.now().strftime('%Y-%m-%d')}T20:00:00",
            "lead_minutes": 15,
            "recurring": "weekly",
            "active": True
        }
    ],
    "notes": [
        {
            "id": "note_init_1",
            "title": "Global Wave İçerik İlkeleri",
            "content": "Shorts videolarında ilk 3 saniye dual-hook, 2.33 kelime/sn ritmi ve net bilgi kazanımı zorunludur.",
            "tags": ["content", "standard"],
            "created_at": time.time(),
            "updated_at": time.time()
        }
    ]
}

class PersonalAssistant:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.data = self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        with AGENDA_LOCK:
            if not AGENDA_FILE.exists():
                self._save_data_unlocked(DEFAULT_AGENDA)
                return json.loads(json.dumps(DEFAULT_AGENDA))
            try:
                with open(AGENDA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load {AGENDA_FILE}: {e}")
                return json.loads(json.dumps(DEFAULT_AGENDA))

    def _save_data_unlocked(self, data: Dict[str, Any]):
        try:
            tmp_file = AGENDA_FILE.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            tmp_file.replace(AGENDA_FILE)
        except Exception as e:
            logger.error(f"Failed to save {AGENDA_FILE}: {e}")

    # ==========================================================================
    # 1. DAILY BRIEFING ("Jarvis, bugün ne yapmam gerekiyor?")
    # ==========================================================================
    def get_daily_briefing(self) -> Dict[str, Any]:
        """
        Aggregates calendar events, todos, ongoing project state, and communication triage.
        """
        today_str = datetime.now().strftime("%Y-%m-%d")
        day_names_tr = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        current_day_name = day_names_tr[datetime.now().weekday()]

        with AGENDA_LOCK:
            all_tasks = self.data.get("tasks", [])
            all_reminders = self.data.get("reminders", [])

        # Categorize tasks
        due_today = []
        overdue = []
        completed_today = []

        for t in all_tasks:
            due = t.get("due_date", "")
            status = t.get("status", "pending")
            if status == "completed":
                if t.get("completed_at") and date.fromtimestamp(t["completed_at"]).isoformat() == today_str:
                    completed_today.append(t)
            elif due:
                if due < today_str:
                    overdue.append(t)
                elif due == today_str:
                    due_today.append(t)

        # Active Reminders for Today
        today_reminders = [
            r for r in all_reminders
            if r.get("active") and r.get("datetime_iso", "").startswith(today_str)
        ]

        # Reality Memory Project Sync
        reality = reality_memory.sync_with_reality()
        active_project_task = reality.get("active_task")
        uncommitted_count = reality.get("uncommitted_changes_count", 0)

        # Inbound Communications check (WhatsApp & Gmail)
        unread_whatsapp_count = 0
        try:
            from core_jarvis.whatsapp_daemon import whatsapp_daemon
            chats = whatsapp_daemon.get_chats_overview()
            unread_whatsapp_count = sum(c.get("unread_count", 0) for c in chats)
        except Exception:
            pass

        # Executive Speech Synthesis Draft (Turkish)
        speech_parts = [f"Günaydın Sayın Hilmi. Bugün {current_day_name}, {datetime.now().strftime('%d.%m.%Y')}."]

        if overdue:
            speech_parts.append(f"Dikkat: {len(overdue)} adet gecikmiş göreviniz bulunuyor.")

        if due_today:
            speech_parts.append(f"Bugün tamamlanması gereken {len(due_today)} öncelikli işiniz var.")
            urgent_tasks = [t['title'] for t in due_today if t.get('priority') in ['urgent', 'high']]
            if urgent_tasks:
                speech_parts.append(f"En acil olan: {urgent_tasks[0]}.")
        else:
            speech_parts.append("Bugün için vadesi dolan bekleyen görev bulunmuyor.")

        if today_reminders:
            speech_parts.append(f"Ajandanızda bugün için {len(today_reminders)} hatırlatıcı kayıtlı.")

        if unread_whatsapp_count > 0:
            speech_parts.append(f"WhatsApp üzerinden {unread_whatsapp_count} adet okunmamış mesajınız var.")

        if active_project_task and active_project_task.get("status") == "in_progress":
            speech_parts.append(f"Global Wave projesinde '{active_project_task.get('name')}' görevi devam ediyor.")

        executive_speech = " ".join(speech_parts)

        return {
            "date": today_str,
            "day_name": current_day_name,
            "tasks": {
                "due_today": due_today,
                "overdue": overdue,
                "completed_today": completed_today,
                "total_active": len(due_today) + len(overdue)
            },
            "reminders": today_reminders,
            "project_state": {
                "active_task": active_project_task,
                "uncommitted_files": uncommitted_count,
                "git_branch": reality.get("branch")
            },
            "communications": {
                "unread_whatsapp": unread_whatsapp_count,
                "gmail_status": "ready"
            },
            "executive_briefing_text": executive_speech
        }

    # ==========================================================================
    # 2. TASK & PROJECT MANAGEMENT
    # ==========================================================================
    def add_task(
        self,
        title: str,
        priority: str = "normal",
        due_date: Optional[str] = None,
        category: str = "general"
    ) -> Dict[str, Any]:
        if not due_date:
            due_date = datetime.now().strftime("%Y-%m-%d")

        task = {
            "id": f"task_{uuid.uuid4().hex[:8]}",
            "title": title.strip(),
            "category": category,
            "priority": priority if priority in ["urgent", "high", "normal", "low"] else "normal",
            "due_date": due_date,
            "status": "pending",
            "created_at": time.time(),
            "completed_at": None
        }

        with AGENDA_LOCK:
            self.data.setdefault("tasks", []).append(task)
            self._save_data_unlocked(self.data)

        logger.info(f"[PersonalAssistant] Task added: {task['id']} - {task['title']}")
        return {"success": True, "task": task}

    def complete_task(self, task_id: str) -> Dict[str, Any]:
        with AGENDA_LOCK:
            for t in self.data.get("tasks", []):
                if t.get("id") == task_id:
                    t["status"] = "completed"
                    t["completed_at"] = time.time()
                    self._save_data_unlocked(self.data)
                    return {"success": True, "task": t}

        return {"success": False, "error": f"Görev bulunamadı: {task_id}"}

    def get_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with AGENDA_LOCK:
            tasks = self.data.get("tasks", [])
            if status:
                return [t for t in tasks if t.get("status") == status]
            return list(tasks)

    # ==========================================================================
    # 3. CALENDAR & REMINDERS
    # ==========================================================================
    def add_reminder(
        self,
        title: str,
        datetime_iso: str,
        lead_minutes: int = 15,
        recurring: Optional[str] = None
    ) -> Dict[str, Any]:
        reminder = {
            "id": f"rem_{uuid.uuid4().hex[:8]}",
            "title": title.strip(),
            "datetime_iso": datetime_iso,
            "lead_minutes": int(lead_minutes),
            "recurring": recurring,
            "active": True,
            "created_at": time.time()
        }

        with AGENDA_LOCK:
            self.data.setdefault("reminders", []).append(reminder)
            self._save_data_unlocked(self.data)

        logger.info(f"[PersonalAssistant] Reminder set: {reminder['id']} - {reminder['title']}")
        return {"success": True, "reminder": reminder}

    def get_reminders(self) -> List[Dict[str, Any]]:
        with AGENDA_LOCK:
            return list(self.data.get("reminders", []))

    # ==========================================================================
    # 4. EXECUTIVE NOTES & DOCUMENTS
    # ==========================================================================
    def add_note(self, title: str, content: str, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        note = {
            "id": f"note_{uuid.uuid4().hex[:8]}",
            "title": title.strip(),
            "content": content.strip(),
            "tags": tags or [],
            "created_at": time.time(),
            "updated_at": time.time()
        }

        with AGENDA_LOCK:
            self.data.setdefault("notes", []).append(note)
            self._save_data_unlocked(self.data)

        logger.info(f"[PersonalAssistant] Note saved: {note['id']} - {note['title']}")
        return {"success": True, "note": note}

    def get_notes(self) -> List[Dict[str, Any]]:
        with AGENDA_LOCK:
            return list(self.data.get("notes", []))


personal_assistant = PersonalAssistant()
