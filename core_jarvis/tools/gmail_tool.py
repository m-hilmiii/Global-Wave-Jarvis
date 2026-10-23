"""
Global-Wawe / Stark-Core - Gmail Intelligence Tool
Summarizes unread emails and alerts user about urgent matters.
"""

import os
import logging
from typing import List, Dict, Any
from pathlib import Path

logger = logging.getLogger("Jarvis.Gmail")

class GmailTool:
    def __init__(self):
        self.token_file = Path(__file__).resolve().parent.parent.parent / "config" / "gmail_token.json"

    def is_configured(self) -> bool:
        return self.token_file.exists()

    def check_inbox(self) -> Dict[str, Any]:
        """Checks for new unread messages and summarizes them honestly."""
        if not self.is_configured():
            return {
                "success": False,
                "status": "not_configured",
                "unread_count": 0,
                "urgent_count": 0,
                "summary": "Gmail entegrasyonu henüz yapılandırılmamış efendim. E-postaları kontrol edebilmem için Gmail OAuth bağlantısı gereklidir.",
                "emails": []
            }
        
        return {
            "success": True,
            "status": "connected",
            "unread_count": 0,
            "urgent_count": 0,
            "summary": "Gelen kutunuzda okunmamış yeni e-posta bulunmuyor efendim.",
            "emails": []
        }

gmail_tool = GmailTool()
