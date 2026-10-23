"""
Global Wave - SQLite3 Checkpoint & Persistence Engine (Crash Survival)
Stores task states, checkpoints, scene metadata, and YouTube upload history in app.db.
High-concurrency WAL mode, busy timeouts, and thread-safe connection pooling.
"""
import sqlite3
import json
import os
import threading
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "config"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "app.db"

_db_lock = threading.Lock()
_db_initialized = False

def get_db_connection() -> sqlite3.Connection:
    """Creates an SQLite connection configured with WAL journal mode and busy timeout."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db():
    """Initializes the SQLite schema once with table and column migration checks."""
    global _db_initialized
    with _db_lock:
        if _db_initialized:
            return
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    persona_id TEXT,
                    topic TEXT,
                    target_duration TEXT,
                    tts_engine TEXT,
                    enable_bgm INTEGER,
                    bgm_volume REAL,
                    stage TEXT,
                    percent INTEGER,
                    message TEXT,
                    video_url TEXT,
                    task_data TEXT,
                    youtube_url TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
            ''')
            try:
                c.execute("ALTER TABLE tasks ADD COLUMN youtube_url TEXT")
            except Exception:
                pass
            conn.commit()
            _db_initialized = True
        finally:
            conn.close()

def save_task_init(task_id: str, persona_id: str, topic: str, target_duration: str, tts_engine: str, enable_bgm: bool, bgm_volume: float):
    init_db()
    conn = get_db_connection()
    try:
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute('''
            INSERT OR REPLACE INTO tasks 
            (task_id, persona_id, topic, target_duration, tts_engine, enable_bgm, bgm_volume, stage, percent, message, video_url, task_data, youtube_url, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (task_id, persona_id, topic, target_duration, tts_engine, int(enable_bgm), bgm_volume, "init", 5, "Initializing task...", None, "{}", None, now, now))
        conn.commit()
    finally:
        conn.close()

def update_task_checkpoint(task_id: str, percent: int, stage: str, message: str, video_url: str = None, task_data: dict = None):
    init_db()
    conn = get_db_connection()
    try:
        c = conn.cursor()
        now = datetime.now().isoformat()
        if task_data is not None:
            c.execute('''
                UPDATE tasks 
                SET percent = ?, stage = ?, message = ?, video_url = COALESCE(?, video_url), task_data = ?, updated_at = ?
                WHERE task_id = ?
            ''', (percent, stage, message, video_url, json.dumps(task_data), now, task_id))
        else:
            c.execute('''
                UPDATE tasks 
                SET percent = ?, stage = ?, message = ?, video_url = COALESCE(?, video_url), updated_at = ?
                WHERE task_id = ?
            ''', (percent, stage, message, video_url, now, task_id))
        conn.commit()
    finally:
        conn.close()

def update_task_youtube(task_id: str, youtube_url: str):
    init_db()
    conn = get_db_connection()
    try:
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute('''
            UPDATE tasks 
            SET youtube_url = ?, updated_at = ?
            WHERE task_id = ?
        ''', (youtube_url, now, task_id))
        conn.commit()
    finally:
        conn.close()

def get_task(task_id: str) -> dict | None:
    init_db()
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = c.fetchone()
        if not row:
            return None
        t = dict(row)
        if t.get("task_data"):
            try:
                t["task_data"] = json.loads(t["task_data"])
            except Exception:
                t["task_data"] = {}
        return t
    finally:
        conn.close()

def get_all_tasks(limit: int = 50) -> list:
    init_db()
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,))
        tasks = []
        for row in c.fetchall():
            t = dict(row)
            if t.get("task_data"):
                try:
                    t["task_data"] = json.loads(t["task_data"])
                except Exception:
                    t["task_data"] = {}
            tasks.append(t)
        return tasks
    finally:
        conn.close()

def get_completed_tasks(limit: int = 30) -> list:
    init_db()
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM tasks WHERE percent >= 100 AND video_url IS NOT NULL ORDER BY updated_at DESC LIMIT ?", (limit,))
        tasks = []
        for row in c.fetchall():
            t = dict(row)
            if t.get("task_data"):
                try:
                    t["task_data"] = json.loads(t["task_data"])
                except Exception:
                    t["task_data"] = {}
            tasks.append(t)
        return tasks
    finally:
        conn.close()

def get_resumable_tasks() -> list:
    init_db()
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM tasks WHERE percent < 100 AND stage != 'error' ORDER BY updated_at DESC")
        tasks = []
        for row in c.fetchall():
            t = dict(row)
            if t.get("task_data"):
                try:
                    t["task_data"] = json.loads(t["task_data"])
                except Exception:
                    t["task_data"] = {}
            tasks.append(t)
        return tasks
    finally:
        conn.close()
