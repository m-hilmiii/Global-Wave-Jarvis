"""
Global-Wawe / Stark-Core - Telegram Executive Hotline Tool
Provides Sayın Mücahit Hilmi with direct 24/7 bidirectional hotline on their phone for:
- Outbound: Text alerts, voice notes, and rendered video delivery
- Inbound: Receiving mobile instructions, status queries, and voice requests
"""

import os
import requests
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("Jarvis.Telegram")

class TelegramTool:
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")
        self._last_update_id = 0

    def is_configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def send_message(self, text: str) -> Dict[str, Any]:
        if not self.is_configured():
            logger.info("[Telegram Standby] Message dispatch skipped - Telegram bot not configured.")
            return {
                "success": False,
                "status": "not_configured",
                "error": "Telegram bot henüz yapılandırılmamış efendim (TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID tanımlanmalı)."
            }

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            resp = requests.post(
                url,
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"},
                timeout=10
            )
            data = resp.json() if resp.status_code == 200 else {}
            is_ok = bool(resp.status_code == 200 and data.get("ok") is True)
            return {"success": is_ok, "response": data}
        except Exception as e:
            logger.error(f"[Telegram Error] {e}")
            return {"success": False, "error": "Telegram API iletisim hatasi"}

    def send_video(self, video_path: str, caption: str = "") -> Dict[str, Any]:
        if not self.is_configured() or not os.path.exists(video_path):
            return {"success": False, "note": "Telegram not configured or video not found"}

        url = f"https://api.telegram.org/bot{self.token}/sendVideo"
        try:
            with open(video_path, "rb") as f:
                resp = requests.post(
                    url,
                    data={"chat_id": self.chat_id, "caption": caption},
                    files={"video": f},
                    timeout=60
                )
            return {"success": resp.status_code == 200, "response": resp.json()}
        except Exception as e:
            err_msg = str(e)
            if self.token:
                err_msg = err_msg.replace(self.token, "********")
            return {"success": False, "error": f"Telegram video dispatch error: {err_msg}"}

    def send_voice(self, voice_path: str, caption: str = "") -> Dict[str, Any]:
        """Sends an audio/voice note file directly to Sayın Hilmi's Telegram."""
        if not self.is_configured() or not os.path.exists(voice_path):
            return {"success": False, "note": "Telegram not configured or voice file not found"}

        url = f"https://api.telegram.org/bot{self.token}/sendVoice"
        try:
            with open(voice_path, "rb") as f:
                resp = requests.post(
                    url,
                    data={"chat_id": self.chat_id, "caption": caption},
                    files={"voice": f},
                    timeout=30
                )
            return {"success": resp.status_code == 200, "response": resp.json()}
        except Exception as e:
            err_msg = str(e)
            if self.token:
                err_msg = err_msg.replace(self.token, "********")
            return {"success": False, "error": f"Telegram voice dispatch error: {err_msg}"}

    def get_incoming_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Polls for new inbound messages from Telegram.
        Filters strictly by self.chat_id to ensure only authorized directives from Sayın Hilmi are accepted.
        """
        if not self.is_configured():
            return []

        url = f"https://api.telegram.org/bot{self.token}/getUpdates"
        params = {"limit": limit, "timeout": 2}
        if self._last_update_id > 0:
            params["offset"] = self._last_update_id + 1

        try:
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code != 200:
                return []
            payload = resp.json()
            if not payload.get("ok"):
                return []

            updates = payload.get("result", [])
            messages = []
            for u in updates:
                uid = u.get("update_id", 0)
                if uid > self._last_update_id:
                    self._last_update_id = uid

                msg = u.get("message") or u.get("channel_post")
                if not msg:
                    continue

                from_chat_id = str(msg.get("chat", {}).get("id", ""))
                # Strictly isolate to authorized chat ID
                if from_chat_id != str(self.chat_id):
                    logger.warning(f"[Telegram Security] Rejected message from unauthorized chat_id: {from_chat_id}")
                    continue

                text = msg.get("text") or msg.get("caption", "")
                messages.append({
                    "message_id": msg.get("message_id"),
                    "date": msg.get("date"),
                    "text": text,
                    "from": msg.get("from", {}).get("first_name", "Hilmi")
                })
            return messages
        except Exception as e:
            logger.error(f"[Telegram Polling Error] {e}")
            return []

    def process_hotline_turn(self, orchestrator_callback=None) -> List[Dict[str, Any]]:
        """
        Polls for new directives from Sayın Hilmi, routes them through the JARVIS brain/orchestrator,
        and dispatches the response back to Telegram.
        """
        messages = self.get_incoming_messages(limit=5)
        replies = []
        for msg in messages:
            user_text = msg.get("text", "").strip()
            if not user_text:
                continue

            logger.info(f"[Telegram Hotline] Received directive: {user_text}")

            reply_text = ""
            if orchestrator_callback:
                try:
                    res = orchestrator_callback(user_text)
                    reply_text = res.get("speak_text") or str(res.get("result", ""))
                except Exception as exc:
                    reply_text = f"Emrinizi işlerken bir aksaklık oluştu efendim: {exc}"
            else:
                reply_text = f"Emriniz alındı efendim: '{user_text}'. Sistemler hazır."

            send_res = self.send_message(reply_text)
            replies.append({"input": user_text, "reply": reply_text, "status": send_res})
        return replies


telegram_tool = TelegramTool()
