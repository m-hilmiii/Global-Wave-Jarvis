"""
Global-Wawe / Stark-Core - Telegram Executive Hotline Tool
Adapted from OpenJarvis telegram.py.
Provides user with direct 24/7 hotline on their phone for voice notes, status, and videos.
"""

import os
import requests
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("Jarvis.Telegram")

class TelegramTool:
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")

    def is_configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def send_message(self, text: str) -> Dict[str, Any]:
        if not self.is_configured():
            logger.warning(f"[Telegram Standby] (Token not configured): {text}")
            return {
                "success": False,
                "status": "not_configured",
                "error": "Telegram bot henüz yapılandırılmamış efendim (TELEGRAM_BOT_TOKEN ortam değişkeni tanımlanmalı)."
            }

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            resp = requests.post(url, json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}, timeout=10)
            return {"success": resp.status_code == 200, "response": resp.json()}
        except Exception as e:
            logger.error(f"[Telegram Error] {e}")
            return {"success": False, "error": str(e)}

    def send_video(self, video_path: str, caption: str = "") -> Dict[str, Any]:
        if not self.is_configured() or not os.path.exists(video_path):
            return {"success": False, "note": "Telegram not configured or video not found"}

        url = f"https://api.telegram.org/bot{self.token}/sendVideo"
        try:
            with open(video_path, "rb") as f:
                resp = requests.post(url, data={"chat_id": self.chat_id, "caption": caption}, files={"video": f}, timeout=60)
            return {"success": resp.status_code == 200, "response": resp.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

telegram_tool = TelegramTool()
