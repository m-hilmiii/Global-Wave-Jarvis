"""
Global Wave - SQLite3 Checkpoint & Persistence Engine (Crash Survival)
Stores task states, checkpoints, scene metadata, and YouTube upload history in app.db.
"""
import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime

DB_DIR = Path(r"C:\Users\unalm\OneDrive\Masaüstü\Global-Wawe\config")
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "app.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
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
    # Try adding youtube_url column if older db exists
    try:
        c.execute("ALTER TABLE tasks ADD COLUMN youtube_url TEXT")
    except Exception:
        pass
    conn.commit()
    conn.close()

def save_task_init(task_id: str, persona_id: str, topic: str, target_duration: str, tts_engine: str, enable_bgm: bool, bgm_volume: float):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''
        INSERT OR REPLACE INTO tasks 
        (task_id, persona_id, topic, target_duration, tts_engine, enable_bgm, bgm_volume, stage, percent, message, video_url, task_data, youtube_url, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        task_id, persona_id, topic, target_duration, tts_engine,
        1 if enable_bgm else 0, bgm_volume,
        "init", 5, "Initializing autonomous pipeline...", None, json.dumps({}), None,
        now, now
    ))
    conn.commit()
    conn.close()

def update_task_checkpoint(task_id: str, percent: int, stage: str, message: str, video_url: str = None, task_data: dict = None):
    init_db()
    conn = sqlite3.connect(DB_PATH)
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
    conn.close()

def update_task_youtube(task_id: str, youtube_url: str):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("UPDATE tasks SET youtube_url = ?, updated_at = ? WHERE task_id = ?", (youtube_url, now, task_id))
    conn.commit()
    conn.close()

def get_task(task_id: str) -> dict | None:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM tasks WHERE task_id = ?', (task_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    if d.get("task_data"):
        try:
            d["task_data"] = json.loads(d["task_data"])
        except Exception:
            d["task_data"] = {}
    return d

def get_all_tasks(limit: int = 50) -> list:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM tasks ORDER BY updated_at DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    res = []
    for r in rows:
        d = dict(r)
        if d.get("task_data"):
            try:
                d["task_data"] = json.loads(d["task_data"])
            except Exception:
                d["task_data"] = {}
        res.append(d)
    return res

def get_completed_tasks(limit: int = 30) -> list:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tasks WHERE video_url IS NOT NULL AND stage = 'done' ORDER BY updated_at DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    res = []
    for r in rows:
        d = dict(r)
        if d.get("task_data"):
            try:
                d["task_data"] = json.loads(d["task_data"])
            except Exception:
                d["task_data"] = {}
        res.append(d)
    return res

def get_resumable_tasks() -> list:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tasks WHERE stage != 'completed' AND stage != 'done' ORDER BY updated_at DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    res = []
    for r in rows:
        d = dict(r)
        if d.get("task_data"):
            try:
                d["task_data"] = json.loads(d["task_data"])
            except Exception:
                d["task_data"] = {}
        res.append(d)
    return res