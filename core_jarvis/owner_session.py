"""
Global-Wawe / Stark-Core - Owner WhatsApp Hybrid Session Manager
Manages 10-minute active conversation sessions for Mücahit Hilmi (c_owner).
Implements the 5 critical user revisions:
1. PTT Voice Note Security (Whisper transcription; closed session requires 'Jarvis' prefix)
2. Strict Match on session termination (/kapat, /cikis, jarvis kapat, oturumu kapat) and /temizle buffer reset
3. 8192 context safety & VRAM isolation
4. Fast-path system command bypass + instant WhatsApp typing indicator
5. Context isolation between system telemetry and deep conversational history
"""

import time
import re
import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("Jarvis.OwnerSession")

OWNER_PHONE = "905518477838"      # Mücahit Hilmi normalized phone
OWNER_LID = "187055053267193"     # Mücahit Hilmi WhatsApp Multi-Device LID
SESSION_TTL_SECONDS = 600         # 10 minutes active window
CREDS_FILE = Path(__file__).resolve().parent.parent / "data" / "whatsapp_auth" / "creds.json"


class OwnerSessionManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OwnerSessionManager, cls).__new__(cls)
            cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        self.is_active: bool = False
        self.session_start_time: float = 0.0
        self.last_activity_time: float = 0.0
        self.chat_history: List[Dict[str, str]] = []
        self.owner_phone: str = OWNER_PHONE
        self.owner_lid: str = OWNER_LID
        self._refresh_owner_ids()

    def _refresh_owner_ids(self):
        """Reads live owner JID and LID from data/whatsapp_auth/creds.json if available."""
        if CREDS_FILE.exists():
            try:
                with open(CREDS_FILE, "r", encoding="utf-8-sig") as f:
                    me = json.load(f).get("me", {})
                me_id = str(me.get("id", "")).split("@")[0].split(":")[0]
                me_lid = str(me.get("lid", "")).split("@")[0].split(":")[0]
                if me_id and me_id.isdigit():
                    self.owner_phone = me_id
                if me_lid and me_lid.isdigit():
                    self.owner_lid = me_lid
            except Exception as err:
                logger.debug(f"[OwnerSession] Live credentials read notice: {err}")

    def is_owner(self, phone_or_jid: str) -> bool:
        """Checks if the incoming sender or chat is Mücahit Hilmi (c_owner) by phone or LID."""
        if not phone_or_jid:
            return False
        user_part = str(phone_or_jid).split("@")[0].split(":")[0]
        digits = "".join([c for c in user_part if c.isdigit()])
        if not digits or len(digits) < 10:
            return False
        if self.owner_lid and digits == self.owner_lid:
            return True
        return digits.endswith(self.owner_phone[-10:]) or self.owner_phone.endswith(digits)

    def is_owner_self_chat(self, chat_jid: str, sender_jid: str = "") -> bool:
        """Returns True if the message occurs inside Sayın Hilmi's own 'Message Yourself' (Kendime Mesaj) chat."""
        if not chat_jid or "@g.us" in chat_jid or "@newsletter" in chat_jid or "broadcast" in chat_jid:
            return False
        return self.is_owner(chat_jid)

    def is_session_active(self) -> bool:
        """Returns True if the 10-minute session window is currently active."""
        if not self.is_active:
            return False
        if time.time() - self.last_activity_time > SESSION_TTL_SECONDS:
            self.is_active = False
            logger.info("[OwnerSession] 10-minute session TTL expired. Session moved to standby.")
            return False
        return True

    def start_session(self):
        self.is_active = True
        self.session_start_time = time.time()
        self.last_activity_time = time.time()
        logger.info("[OwnerSession] Active 10-minute session started for Sayın Hilmi.")

    def touch(self):
        """Refreshes the 10-minute timer on every message interaction."""
        self.last_activity_time = time.time()

    def close_session(self):
        self.is_active = False
        logger.info("[OwnerSession] Session closed manually.")

    def clear_history(self):
        self.chat_history.clear()
        logger.info("[OwnerSession] Conversation buffer cleared.")

    def add_turn(self, user_text: str, assistant_reply: str):
        self.chat_history.append({"role": "user", "content": user_text})
        self.chat_history.append({"role": "assistant", "content": assistant_reply})
        if len(self.chat_history) > 20:
            self.chat_history = self.chat_history[-20:]

    def check_strict_close(self, text: str) -> bool:
        """Revision 2: Strict match for closing session without false triggers."""
        normalized = text.strip().lower()
        return normalized in ["/kapat", "/cikis", "/çıkış", "jarvis kapat", "oturumu kapat"]

    def check_buffer_clear(self, text: str) -> bool:
        """Revision 2: Strict match for clearing memory buffer without closing session."""
        normalized = text.strip().lower()
        return normalized in ["/temizle", "/yeni", "hafizayi temizle", "hafızayı temizle", "sohbeti temizle"]

    def is_trigger_message(self, text: str) -> Tuple[bool, str]:
        """Checks if text begins with or contains Jarvis wake word and returns stripped text."""
        norm = text.strip()
        pattern = r"^(?:hey\s+jarvis|dinle\s+jarvis|selam\s+jarvis|merhaba\s+jarvis|jarvis)\b[\s,:]*"
        match = re.search(pattern, norm, re.IGNORECASE)
        if match:
            clean_cmd = norm[match.end():].strip()
            return True, clean_cmd
        if re.search(r"\bjarvis\b", norm, re.IGNORECASE):
            return True, norm
        return False, norm

    def is_fast_system_command(self, text: str) -> Tuple[bool, str]:
        """
        Revision 4 & 5: Fast command bypass without 14B model wait.
        Returns (is_fast, command_type).
        """
        t = text.lower().strip()
        if (
            (any(w in t for w in ["ekran", "bilgisayar", "oturum"]) and any(k in t for k in ["kilitle", "kilit"]))
            or any(s in t for s in ["windows + l", "win + l", "win+l", "windows+l", "ekran kilidi"])
        ) and not any(neg in t for neg in ["nasıl", "nedir", "rehber", "anlat"]):
            return True, "lock_workstation"
        if any(k in t for k in ["klavyeden", "tuşuna bas", "tuşlarına bas", "kısayol", "alt + f4", "ctrl +"]):
            return True, "keyboard_shortcut"
        if any(k in t for k in ["ekran görüntüsü", "ekranıma bak", "ekrana bak", "ekranı incele", "ekrandaki hata"]):
            return True, "screen_inspect"
        if any(k in t for k in ["sistem durumu", "telemetri", "kaynaklar", "cpu", "ram durumu", "donanım durumu"]):
            return True, "system_telemetry"
        if any(k in t for k in ["bugün ne yapmam gerekiyor", "günlük brifing", "ajandam", "görevlerim"]):
            return True, "daily_briefing"
        if any(k in t for k in ["testleri çalıştır", "birim testler"]):
            return True, "run_tests"
        if any(k in t for k in ["ne değişti", "git diff", "değişiklikler"]):
            return True, "git_diff"
        if "youtube" in t and any(w in t for w in ["aç", "ac", "oynat", "başlat", "cal", "çal", "izle", "dinle"]):
            return True, "play_youtube"
        if "dizi" in t and any(w in t for w in ["bölüm", "bolum", "kaldığım", "kaldigim", "sezon", "izle", "aç", "ac"]):
            return True, "watch_series"
        if any(p in t for p in ["tarayıcıda ara", "tarayicida ara", "tarayıcıda aç", "tarayicida ac", "google'da ara", "google da ara", "webde ara", "internette ara"]):
            return True, "browser_search"
        if any(w in t for w in ["hava durumu", "hava nasıl", "hava nasil", "kaç derece", "yağmur var mı"]):
            return True, "live_weather"
        if any(k in t for k in ["ltx durumu", "video render durumu", "render bitti mi", "video bitti mi"]):
            return True, "ltx_status"
        if any(k in t for k in ["ltx ile video", "ltx-2 ile video", "ltx videosu", "sinematik video üret", "siberpunk shorts filmi", "45 saniyelik film"]):
            return True, "ltx_video"
        return False, ""


owner_session = OwnerSessionManager()
