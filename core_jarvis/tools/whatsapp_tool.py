"""
Global-Wawe / Stark-Core - WhatsApp Automation Tool
100% Real-World Architecture using Baileys Node.js Bridge.
Never simulates. Handles any contact or raw phone number dynamically.
Manages sending and incoming message inbox.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from core_jarvis.tools.contacts import contacts_mgr
from core_jarvis.whatsapp_daemon import whatsapp_daemon

logger = logging.getLogger("Jarvis.WhatsApp")

class WhatsAppTool:
    def __init__(self):
        pass

    def is_connected(self) -> bool:
        return whatsapp_daemon.is_authenticated()

    def send_message_to_contact(self, contact_name: str, message: str) -> Dict[str, Any]:
        """Sends WhatsApp message to a named contact from contacts.json."""
        contact = contacts_mgr.find_contact(contact_name)
        if not contact:
            return {
                "success": False,
                "is_connected": self.is_connected(),
                "error": f"Rehberde '{contact_name}' kişisini bulamadım efendim. Numarasını söylerseniz hemen kaydedebilirim."
            }

        phone = contact.get("phone", "")
        return self.send_message_to_phone(phone, message, recipient_name=contact["name"])

    def send_message_to_phone(self, phone: str, message: str, recipient_name: str = "") -> Dict[str, Any]:
        """Sends real WhatsApp message to a raw phone number or contact."""
        target_display = recipient_name or phone
        
        if not self.is_connected():
            whatsapp_daemon.start_bridge()
            return {
                "success": False,
                "is_connected": False,
                "recipient": target_display,
                "phone": phone,
                "report": (
                    f"Efendim, WhatsApp oturumu henüz bağlı değil.\n\n"
                    f"{target_display} kişisine gerçek mesaj gönderebilmemiz için WhatsApp köprüsünü başlattım.\n"
                    f"Lütfen telefonunuzdan WhatsApp -> Bağlı Cihazlar -> Cihaz Bağla diyerek ekrandaki QR kodunu okutun."
                )
            }

        res = whatsapp_daemon.send_message(phone, message)
        if res.get("success"):
            return {
                "success": True,
                "is_connected": True,
                "recipient": target_display,
                "phone": phone,
                "message": message,
                "report": f"{target_display} ({phone}) kişisine \"{message}\" mesajı WhatsApp üzerinden başarıyla iletildi."
            }
        else:
            return {
                "success": False,
                "is_connected": True,
                "error": res.get("error", "Gönderim başarısız oldu.")
            }

    def get_inbox(self, limit: int = 10, unread_only: bool = False) -> List[Dict[str, Any]]:
        """Retrieves real received messages from WhatsApp inbox."""
        return whatsapp_daemon.get_inbox(limit=limit, unread_only=unread_only)

    def get_chat_history(self, contact_query: str) -> List[Dict[str, Any]]:
        """Returns chronological messages for a specific contact or raw phone number."""
        return whatsapp_daemon.get_chat_history(contact_query)

    def get_latest_incoming_message(self, contact_query: str) -> Optional[Dict[str, Any]]:
        """Returns the most recent incoming message from a contact, regardless of read status."""
        return whatsapp_daemon.get_latest_incoming_message(contact_query)

    def send_message(self, phone: str, text: str) -> Dict[str, Any]:
        """Direct alias for send_message_to_phone."""
        return self.send_message_to_phone(phone, text)

    def send_voice_note(self, phone: str, audio_path: str) -> Dict[str, Any]:
        """Sends native WhatsApp PTT voice note (audio/ogg; codecs=opus)."""
        return whatsapp_daemon.send_voice_note(phone, audio_path)

    def reconnect_and_sync(self) -> Dict[str, Any]:
        """Clears auth tokens and restarts bridge to force full history sync via new QR code."""
        return whatsapp_daemon.reconnect_and_sync()

    def enable_ai_delegate(self, target: Optional[str] = None):
        """Activates AI Delegate (Meşgul Modu)."""
        whatsapp_daemon.enable_ai_delegate(target)

    def disable_ai_delegate(self) -> List[Dict[str, Any]]:
        """Deactivates AI Delegate and returns conversation logs."""
        return whatsapp_daemon.disable_ai_delegate()

    @property
    def ai_delegate_active(self) -> bool:
        return whatsapp_daemon.ai_delegate_active

    @property
    def ai_delegate_targets(self) -> List[str]:
        return whatsapp_daemon.ai_delegate_targets

    @property
    def ai_delegate_logs(self) -> List[Dict[str, Any]]:
        return whatsapp_daemon.ai_delegate_logs
        return whatsapp_daemon.disable_ai_delegate()

    def import_chat_export(self, contact_name: str, file_text: str) -> Dict[str, Any]:
        """Imports exported _chat.txt file into inbox."""
        return whatsapp_daemon.import_chat_export(contact_name, file_text)

    def mark_all_read(self):
        """Marks all incoming messages as read."""
        whatsapp_daemon.mark_all_read()

    def mark_chat_read(self, contact_query: str):
        """Marks all messages for a specific contact as read."""
        whatsapp_daemon.mark_chat_read(contact_query)

whatsapp_tool = WhatsAppTool()
