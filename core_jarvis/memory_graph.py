"""
Global-Wawe / Stark-Core - Jarvis Knowledge Graph & Episodic Memory
Inspired by isair/jarvis local memory architecture.
Zero cloud costs, 100% private SQLite storage. Never forgets facts, preferences, contacts, or project goals.
"""

import sqlite3
import re
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger("Jarvis.Memory")

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "jarvis_memory.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

class MemoryGraph:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = str(db_path)
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    branch TEXT NOT NULL,          -- 'user', 'directives', 'projects', 'contacts', 'episodes'
                    key_term TEXT NOT NULL UNIQUE,  -- unique identifier or topic
                    content TEXT NOT NULL,         -- factual text or JSON string
                    importance INTEGER DEFAULT 5,  -- 1 to 10
                    access_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_branch ON memory_nodes(branch)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_key ON memory_nodes(key_term)")
            conn.commit()
            
            # Bootstrap default profile if empty
            cursor.execute("SELECT COUNT(*) FROM memory_nodes")
            if cursor.fetchone()[0] == 0:
                self._bootstrap_initial_memory(cursor)
                conn.commit()

        # Always synchronize rich user profile from config/user_profile.json if available
        self.sync_user_profile()

    def sync_user_profile(self):
        """Loads and updates nodes from config/user_profile.json into memory graph."""
        profile_path = Path(__file__).resolve().parent.parent / "config" / "user_profile.json"
        if not profile_path.exists():
            return
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                prof = json.load(f)
            
            ident = prof.get("identity", {})
            hw = prof.get("hardware_baseline", {})
            comm = prof.get("communication_protocols", {})
            work = prof.get("working_principles", {})
            projects = prof.get("projects", {})
            standards = prof.get("coding_standards", {})

            # 1. Identity & Creator node
            creator_text = (
                f"{ident.get('full_name', 'Mücahit Hilmi Ünal')} ({', '.join(ident.get('nicknames', ['Mücon', 'Hilmi']))}) - "
                f"Doğum: {ident.get('birth_date', '20.03.2005')}, Konum: {ident.get('location', 'Eskişehir')}. "
                f"Eğitim: {ident.get('education', 'Trabzon Üniv. Çarşıbaşı MYO')}. "
                f"Rol: {ident.get('role', 'Yazılım ve Backend Geliştirici')} ({', '.join(ident.get('skills', []))})."
            )
            self.save_node("user", "creator_profile", creator_text, importance=10)

            # 2. Hardware baseline node
            hw_text = (
                f"CPU: {hw.get('cpu', '')} | GPU: {hw.get('gpu', '')} | "
                f"RAM: {hw.get('ram', '')} | SSD: {hw.get('storage', '')} | "
                f"Monitörler: 1. ASUS 2K 255Hz, 2. Samsung 2K 165Hz | OS: {hw.get('os', 'Windows 11')}"
            )
            self.save_node("hardware", "hardware_baseline", hw_text, importance=10)

            # 3. Communication Style & Inspector Mode
            def_tone = comm.get("default_tone", {})
            insp = comm.get("inspector_mode", {})
            comm_text = (
                f"Samimiyet Dili: {def_tone.get('style', '')}. İzin verilen hitaplar: {', '.join(def_tone.get('allowed_terms_of_endearment', []))}. "
                f"Müfettiş Modu: Karakter analizi, kod denetimi veya sistem incelemesi istendiğinde %100 dürüst, acımasız ve manipülasyonsuz profesyonel baş müfettiş moduna geç."
            )
            self.save_node("directives", "communication_protocols", comm_text, importance=10)

            # 4. Working Rules
            work_text = (
                f"1. Asla Varsayım Yapma: {work.get('no_assumptions', '')}. "
                f"2. Web Taraması: {work.get('web_research_first', '')}. "
                f"3. Mimari İtiraz & Geliştirme: {work.get('architectural_critique', '')}."
            )
            self.save_node("directives", "working_principles", work_text, importance=10)

            # 5. Projects
            lus = projects.get("lussera", {})
            lus_text = f"{lus.get('name', 'Lussera')}: {lus.get('type', '')}. KESİN KURAL: {lus.get('strict_rule', '')}"
            self.save_node("projects", "lussera", lus_text, importance=10)

            gw = projects.get("global_wave", {})
            gw_text = f"{gw.get('name', 'Global Wave')}: {gw.get('type', '')} (Python, Kokoro, Whisper, Qwen 14B)."
            self.save_node("projects", "global_wave", gw_text, importance=9)

            stark = projects.get("stark_core", {})
            stark_text = f"{stark.get('name', 'Stark Core')}: {stark.get('type', '')} (FastAPI, Docker, Ollama, WhatsApp daemon)."
            self.save_node("projects", "stark_core", stark_text, importance=9)

            val = projects.get("valthera", {})
            val_text = f"{val.get('name', 'Valthera')}: {val.get('type', '')} (Unity 3D, C#)."
            self.save_node("projects", "valthera", val_text, importance=8)

            # 6. Coding Standards (God Mode)
            standards_text = f"Stack: {', '.join(standards.get('stack', []))}. İlkeler: {' | '.join(standards.get('principles', []))}"
            self.save_node("directives", "coding_standards_god_mode", standards_text, importance=10)

            # 7. Cyber Security
            sec = prof.get("cyber_security", {})
            sec_text = f"Siber Güvenlik & Pentest: {sec.get('guidance', '')} Odak: {', '.join(sec.get('focus', []))}"
            self.save_node("directives", "cyber_security_pentest", sec_text, importance=9)

        except Exception as e:
            logger.warning(f"[MemoryGraph] Failed to sync user profile: {e}")

    def _bootstrap_initial_memory(self, cursor):
        defaults = [
            ("user", "creator_name", "Mücahit Hilmi - Kurucu ve Baş Yönetici (Tony Stark rolünde)", 10),
            ("user", "vision", "Yapay zeka ajanlarından oluşan tamamen yerel, sıfır maliyetli sosyal medya ve yazılım şirketi.", 10),
            ("directives", "persona", "Jarvis: Saygılı, zeki, proaktif, çözüm odaklı, sadık yol arkadaşı ve operasyon yöneticisi.", 9),
            ("directives", "cost_rule", "Sıfır bulut API maliyeti. Tüm modeller (Ollama, Kokoro, Whisper, LTX-2.5) yerel çalıştırılır.", 10),
            ("directives", "video_rule", "YouTube Shorts kanca skoru (Hook Score) en az 85 olmalıdır.", 8),
            ("projects", "global_wawe", "Otonom YouTube/Reels video üretim stüdyosu ve seyirci analiz ajanı.", 9),
            ("projects", "stark_core", "Yazılım mühendisliği, kod yazma ve denetleme ajanı.", 9)
        ]
        for branch, key, content, imp in defaults:
            cursor.execute("""
                INSERT OR IGNORE INTO memory_nodes (branch, key_term, content, importance)
                VALUES (?, ?, ?, ?)
            """, (branch, key, content, imp))

    def recall_gate(self, query: str) -> bool:
        """Lightweight heuristic to decide if memory recall is needed without LLM token waste."""
        q = (query or "").lower()
        triggers = [
            "ben", "benim", "hatırla", "kimim", "plan", "proje", "kural", 
            "şirket", "hedef", "vizyon", "tercih", "kişi", "kim", "rehber", "neydi"
        ]
        return any(t in q for t in triggers) or len(q.split()) > 4

    def save_node(self, branch: str, key_term: str, content: str, importance: int = 5):
        """Saves or updates a memory node."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO memory_nodes (branch, key_term, content, importance, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key_term) DO UPDATE SET
                    content = excluded.content,
                    importance = excluded.importance,
                    access_count = access_count + 1,
                    updated_at = CURRENT_TIMESTAMP
            """, (branch, key_term, content, importance))
            conn.commit()

    def get_node(self, key_term: str) -> Optional[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM memory_nodes WHERE key_term = ?", (key_term,))
            row = cursor.fetchone()
            if row:
                cursor.execute("UPDATE memory_nodes SET access_count = access_count + 1 WHERE id = ?", (row["id"],))
                conn.commit()
                return dict(row)
        return None

    def search_memories(self, query: str, limit: int = 5) -> List[dict]:
        """Simple keyword search across memory nodes."""
        words = [w for w in re.findall(r"\w{3,}", query.lower()) if len(w) >= 3]
        if not words:
            return self.get_top_directives()

        conditions = " OR ".join(["content LIKE ? OR key_term LIKE ?" for _ in words])
        params = []
        for w in words:
            params.extend([f"%{w}%", f"%{w}%"])

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT * FROM memory_nodes
                WHERE {conditions}
                ORDER BY importance DESC, access_count DESC
                LIMIT ?
            """, (*params, limit))
            return [dict(r) for r in cursor.fetchall()]

    def get_top_directives(self, limit: int = 12) -> List[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM memory_nodes
                WHERE branch IN ('user', 'directives', 'hardware', 'projects', 'learned_rules')
                ORDER BY importance DESC, id DESC
                LIMIT ?
            """, (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def get_context_summary(self) -> str:
        """Returns concise briefing context to inject into Jarvis system prompt."""
        directives = self.get_top_directives(limit=12)
        # Ensure active learned rules are always included in context summary
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM memory_nodes
                WHERE branch = 'learned_rules'
                ORDER BY updated_at DESC, id DESC
                LIMIT 5
            """)
            learned = [dict(r) for r in cursor.fetchall()]

        seen_keys = {d["key_term"] for d in directives}
        for lr in learned:
            if lr["key_term"] not in seen_keys:
                directives.append(lr)
                seen_keys.add(lr["key_term"])

        lines = ["--- JARVIS LONG-TERM MEMORY & CONTEXT ---"]
        for d in directives:
            lines.append(f"• [{d['branch'].upper()}] {d['key_term']}: {d['content']}")
        lines.append("------------------------------------------")
        return "\n".join(lines)

memory_graph = MemoryGraph()
