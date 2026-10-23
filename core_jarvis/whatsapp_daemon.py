"""
Global-Wawe - Real WhatsApp Baileys Bridge Daemon
Manages a SINGLE Node.js Baileys subprocess, prevents zombie processes,
synchronously waits for real delivery confirmation, and maintains the WhatsApp Inbox.
"""

import os
import sys
import json
import time
import logging
import subprocess
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("Jarvis.WhatsAppDaemon")

BRIDGE_DIR = Path(__file__).resolve().parent / "whatsapp_bridge"
AUTH_DIR = Path(__file__).resolve().parent.parent / "data" / "whatsapp_auth"
AUTH_DIR.mkdir(parents=True, exist_ok=True)
INBOX_FILE = AUTH_DIR.parent / "whatsapp_inbox.json"
CONTACTS_FILE = AUTH_DIR.parent / "contacts.json"

class WhatsAppDaemon:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WhatsAppDaemon, cls).__new__(cls)
            cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        self.process: Optional[subprocess.Popen] = None
        self.status = "disconnected"
        self.latest_qr: Optional[str] = None
        self.lock = threading.Lock()
        self.socket_ready = threading.Event()
        self.pending_replies: Dict[str, Dict[str, Any]] = {}
        self.reply_events: Dict[str, threading.Event] = {}

        if self.is_authenticated():
            self.start_bridge()

    def is_authenticated(self) -> bool:
        creds = AUTH_DIR / "creds.json"
        return creds.exists() and creds.stat().st_size > 50

    def is_connected(self) -> bool:
        return self.is_authenticated() and self.socket_ready.is_set()

    def _kill_zombies(self):
        """Kills any orphaned bridge processes on Windows to prevent conflict 440."""
        try:
            cmd = 'Get-CimInstance Win32_Process -Filter "Name = \'node.exe\'" | Where-Object { $_.CommandLine -like "*bridge.js*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }'
            subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=5)
        except Exception as e:
            logger.warning(f"Error killing zombie node processes: {e}")

    def start_bridge(self):
        """Starts the single Node.js Baileys bridge subprocess if not running."""
        with self.lock:
            if self.process and self.process.poll() is None:
                return  # already running

            dist_bridge = BRIDGE_DIR / "dist" / "bridge.js"
            if not dist_bridge.exists():
                logger.error(f"[WhatsApp] Bridge not built at {dist_bridge}")
                return

            self._kill_zombies()
            self.socket_ready.clear()
            self.status = "connecting"

            cmd = ["node", str(dist_bridge), "--auth-dir", str(AUTH_DIR)]
            logger.info(f"[WhatsApp] Spawning single Baileys bridge: {' '.join(cmd)}")

            try:
                self.process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    bufsize=1,
                    cwd=str(BRIDGE_DIR)
                )
                threading.Thread(target=self._stdout_reader, daemon=True).start()
                threading.Thread(target=self._stderr_reader, daemon=True).start()
            except Exception as e:
                logger.error(f"[WhatsApp] Failed to start bridge process: {e}")
                self.status = "disconnected"

    def _stdout_reader(self):
        for line in iter(self.process.stdout.readline, ''):
            if not line:
                break
            try:
                ev = json.loads(line.strip())
                ev_type = ev.get("type")

                if ev_type == "qr":
                    self.latest_qr = ev.get("data")
                    self.status = "qr_ready"
                    self.socket_ready.clear()
                    logger.info("[WhatsApp] New QR code generated for pairing.")

                elif ev_type == "status":
                    st = ev.get("status", "disconnected")
                    self.status = st
                    if st == "connected":
                        self.latest_qr = None
                        self.socket_ready.set()
                        logger.info("[WhatsApp] Socket is OPEN and ready!")
                    else:
                        self.socket_ready.clear()
                        logger.info(f"[WhatsApp] Status: {self.status}")

                elif ev_type == "sent":
                    req_id = ev.get("request_id")
                    jid = ev.get("jid", "")
                    with self.lock:
                        if req_id and req_id in self.reply_events:
                            self.pending_replies[req_id] = {
                                "success": True,
                                "status": "sent",
                                "message_id": ev.get("message_id"),
                                "jid": jid
                            }
                            self.reply_events[req_id].set()
                        elif jid in self.reply_events:
                            self.pending_replies[jid] = {
                                "success": True,
                                "status": "sent",
                                "message_id": ev.get("message_id"),
                                "jid": jid
                            }
                            self.reply_events[jid].set()

                elif ev_type == "deleted":
                    req_id = ev.get("request_id")
                    jid = ev.get("jid", "")
                    with self.lock:
                        if req_id and req_id in self.reply_events:
                            self.pending_replies[req_id] = {
                                "success": True,
                                "status": "deleted",
                                "message_id": ev.get("message_id"),
                                "jid": jid
                            }
                            self.reply_events[req_id].set()
                        elif jid in self.reply_events:
                            self.pending_replies[jid] = {
                                "success": True,
                                "status": "deleted",
                                "message_id": ev.get("message_id"),
                                "jid": jid
                            }
                            self.reply_events[jid].set()

                elif ev_type == "error":
                    req_id = ev.get("request_id")
                    err_msg = ev.get("message", "Bilinmeyen hata")
                    with self.lock:
                        if req_id and req_id in self.reply_events:
                            self.pending_replies[req_id] = {"success": False, "status": "failed", "error": err_msg}
                            self.reply_events[req_id].set()
                        else:
                            # If no specific request_id, do not fail unrelated operations
                            logger.warning(f"[WhatsApp Bridge Warning] {err_msg}")

                elif ev_type == "message":
                    self._handle_incoming_message(ev)

            except json.JSONDecodeError:
                pass  # Ignore non-JSON stdout logs from node process
            except Exception as e:
                logger.error(f"[WhatsApp Daemon Stdout Error] {e}")

    def _stderr_reader(self):
        for line in iter(self.process.stderr.readline, ''):
            if not line:
                break
            print(line, end='', file=sys.stderr)

    def _resolve_sender_name(self, sender_jid: str, push_name: str = "") -> (str, str):
        raw_num = "".join([c for c in sender_jid.split("@")[0] if c.isdigit()])
        if CONTACTS_FILE.exists():
            try:
                with open(CONTACTS_FILE, "r", encoding="utf-8-sig") as f:
                    contacts = json.load(f).get("contacts", [])
                    for c in contacts:
                        c_num = "".join([x for x in c.get("phone", "") if x.isdigit()])
                        if c_num and raw_num and (c_num.endswith(raw_num) or raw_num.endswith(c_num)):
                            return c["name"], c.get("phone", raw_num)
                        if c.get("lid") and (c.get("lid") in sender_jid or c.get("lid") in raw_num):
                            disp = f"{c['name']} ({c['full_name']})" if c.get("full_name") else c["name"]
                            return disp, c.get("phone", raw_num)
                        if push_name and (
                            (c.get("full_name") and c.get("full_name").lower() in push_name.lower()) or
                            (c.get("name") and c.get("name").lower() in push_name.lower()) or
                            (c.get("relationship", "").lower() == "baba" and "yaşar" in push_name.lower())
                        ):
                            disp = f"{c['name']} ({c['full_name']})" if c.get("full_name") else f"{c['name']} ({push_name})"
                            return disp, c.get("phone", raw_num)
            except Exception as e:
                logger.error(f"[Daemon Contact Resolve Error] {e}")
        return push_name or raw_num or "Bilinmeyen Numara", raw_num

    def _handle_incoming_message(self, ev: Dict[str, Any]):
        chat_jid = ev.get("jid", "")
        sender_jid = ev.get("sender", chat_jid)
        text = ev.get("text", "").strip()
        msg_id = ev.get("message_id", "")
        push_name = ev.get("pushName", "")

        if not text:
            return

        # Prefer chat_jid if it contains the phone number (@s.whatsapp.net) over lid
        primary_jid = chat_jid if "@s.whatsapp.net" in chat_jid else sender_jid
        sender_name, phone = self._resolve_sender_name(primary_jid, push_name)
        now_str = datetime.now().strftime("%H:%M")

        with self.lock:
            inbox = []
            if INBOX_FILE.exists():
                try:
                    with open(INBOX_FILE, "r", encoding="utf-8-sig") as f:
                        inbox = json.load(f)
                except Exception:
                    inbox = []

            # Avoid duplicates
            if any(m.get("id") == msg_id for m in inbox):
                return

            entry = {
                "id": msg_id,
                "sender_jid": sender_jid,
                "sender_name": sender_name,
                "phone": phone,
                "text": text,
                "time": now_str,
                "timestamp": time.time(),
                "unread": True
            }
            inbox.append(entry)
            inbox = inbox[-100:]  # Keep latest 100 messages

            try:
                with open(INBOX_FILE, "w", encoding="utf-8") as f:
                    json.dump(inbox, f, ensure_ascii=False, indent=2)
                logger.info(f"[WhatsApp] Incoming from {sender_name}: '{text}'")
            except Exception as e:
                logger.error(f"[WhatsApp] Error saving inbox: {e}")

    def get_inbox(self, limit: int = 10, unread_only: bool = False) -> List[Dict[str, Any]]:
        with self.lock:
            if not INBOX_FILE.exists():
                return []
            try:
                with open(INBOX_FILE, "r", encoding="utf-8-sig") as f:
                    messages = json.load(f)
            except Exception:
                return []

            if unread_only:
                messages = [m for m in messages if m.get("unread", True)]

            return messages[-limit:]

    def mark_all_read(self):
        with self.lock:
            if not INBOX_FILE.exists():
                return
            try:
                with open(INBOX_FILE, "r", encoding="utf-8-sig") as f:
                    messages = json.load(f)
                for m in messages:
                    m["unread"] = False
                with open(INBOX_FILE, "w", encoding="utf-8") as f:
                    json.dump(messages, f, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                pass  # Ignore non-JSON stdout logs from node process
            except Exception as e:
                logger.error(f"[WhatsApp Daemon Stdout Error] {e}")

    def send_message(self, phone: str, text: str) -> Dict[str, Any]:
        """Sends a real WhatsApp message with a unique request_id and synchronously waits for server delivery confirmation."""
        if not self.is_authenticated():
            self.start_bridge()
            return {
                "success": False,
                "status": self.status,
                "qr": self.latest_qr,
                "error": "WhatsApp oturumu henüz bağlı değil. Lütfen ekrandaki QR kodunu okutun."
            }

        # Clean phone to WhatsApp JID format
        clean_num = "".join([c for c in phone if c.isdigit()])
        if clean_num.startswith("0"):
            clean_num = "90" + clean_num[1:]
        elif len(clean_num) == 10:
            clean_num = "90" + clean_num

        jid = f"{clean_num}@s.whatsapp.net"

        # Ensure process is alive
        if not self.process or self.process.poll() is not None:
            self.start_bridge()

        # Wait up to 15 seconds for WebSocket to be open
        if not self.socket_ready.is_set():
            logger.info("[WhatsApp] Waiting for socket connection to open...")
            ready = self.socket_ready.wait(timeout=15)
            if not ready:
                return {
                    "success": False,
                    "error": "WhatsApp bağlantısı kuruluyor, lütfen 5 saniye sonra tekrar deneyin."
                }

        request_id = str(uuid.uuid4())
        ack_event = threading.Event()
        with self.lock:
            self.reply_events[request_id] = ack_event
            self.pending_replies[request_id] = None

        payload = json.dumps({
            "type": "send",
            "jid": jid,
            "text": text,
            "request_id": request_id
        }) + "\n"

        try:
            if not self.process or not self.process.stdin:
                with self.lock:
                    self.reply_events.pop(request_id, None)
                    self.pending_replies.pop(request_id, None)
                return {"success": False, "error": "WhatsApp köprü işlemi çalışmıyor."}

            self.process.stdin.write(payload)
            self.process.stdin.flush()

            # Wait up to 15 seconds for WhatsApp server ACK
            confirmed = ack_event.wait(timeout=15)

            with self.lock:
                result = self.pending_replies.pop(request_id, None)
                self.reply_events.pop(request_id, None)

            if confirmed and result and result.get("success"):
                out_msg_id = result.get("message_id") or f"OUT_{int(time.time()*1000)}"
                out_entry = {
                    "id": out_msg_id,
                    "sender_jid": "me",
                    "chat_jid": jid,
                    "sender_name": "Mücahit Hilmi",
                    "phone": clean_num,
                    "text": text,
                    "time": datetime.now().strftime("%H:%M"),
                    "timestamp": time.time(),
                    "unread": False,
                    "from_me": True
                }
                with self.lock:
                    inbox = []
                    if INBOX_FILE.exists():
                        try:
                            with open(INBOX_FILE, "r", encoding="utf-8-sig") as f:
                                inbox = json.load(f)
                        except Exception:
                            inbox = []
                    inbox.append(out_entry)
                    inbox = inbox[-150:]
                    try:
                        with open(INBOX_FILE, "w", encoding="utf-8") as f:
                            json.dump(inbox, f, ensure_ascii=False, indent=2)
                    except Exception:
                        pass

                return {
                    "success": True,
                    "recipient_jid": jid,
                    "text": text,
                    "status": "sent",
                    "request_id": request_id,
                    "message_id": out_msg_id,
                    "entry": out_entry
                }
            elif result and not result.get("success"):
                return {
                    "success": False,
                    "status": "failed",
                    "request_id": request_id,
                    "error": f"WhatsApp iletim hatası: {result.get('error')}"
                }
            else:
                # Timed out: return status unknown without blind resend to prevent duplicates
                return {
                    "success": False,
                    "status": "unknown",
                    "request_id": request_id,
                    "error": "WhatsApp sunucusundan iletim onayı zaman aşımına uğradı."
                }

        except Exception as e:
            with self.lock:
                self.reply_events.pop(request_id, None)
                self.pending_replies.pop(request_id, None)
            return {"success": False, "status": "failed", "error": str(e)}


    def delete_message(self, jid: str, message_id: str, everyone: bool = True) -> Dict[str, Any]:
        """Deletes a message from WhatsApp (everyone) with verified server ACK, or removes from local thread (me)."""
        if everyone:
            if not self.process or not self.process.stdin:
                return {"success": False, "error": "WhatsApp köprü işlemi çalışmıyor."}

            digits = "".join([c for c in jid if c.isdigit()])
            clean_jid = jid if "@" in jid else f"{digits}@s.whatsapp.net"
            request_id = str(uuid.uuid4())
            ack_event = threading.Event()
            with self.lock:
                self.reply_events[request_id] = ack_event
                self.pending_replies[request_id] = None

            payload = json.dumps({
                "type": "delete",
                "jid": clean_jid,
                "message_id": message_id,
                "fromMe": True,
                "request_id": request_id
            }) + "\n"

            try:
                self.process.stdin.write(payload)
                self.process.stdin.flush()

                confirmed = ack_event.wait(timeout=10)
                with self.lock:
                    result = self.pending_replies.pop(request_id, None)
                    self.reply_events.pop(request_id, None)

                if confirmed and result and result.get("success"):
                    # Confirmed by Baileys: Now clean up local inbox
                    with self.lock:
                        if INBOX_FILE.exists():
                            try:
                                with open(INBOX_FILE, "r", encoding="utf-8-sig") as f:
                                    inbox = json.load(f)
                                inbox = [m for m in inbox if m.get("id") != message_id]
                                with open(INBOX_FILE, "w", encoding="utf-8") as f:
                                    json.dump(inbox, f, ensure_ascii=False, indent=2)
                            except Exception:
                                pass
                    return {"success": True, "status": "delete_requested", "message": "Silme talebi WhatsApp sunucusuna iletildi (delete_requested).", "request_id": request_id}
                elif result and not result.get("success"):
                    return {"success": False, "error": f"WhatsApp silme hatası: {result.get('error')}", "request_id": request_id}
                else:
                    return {"success": False, "error": "WhatsApp sunucusundan silme teyidi zaman aşımına uğradı.", "request_id": request_id}
            except Exception as e:
                with self.lock:
                    self.reply_events.pop(request_id, None)
                    self.pending_replies.pop(request_id, None)
                return {"success": False, "error": str(e)}

        # Local deletion only ("Benden Sil")
        with self.lock:
            if INBOX_FILE.exists():
                try:
                    with open(INBOX_FILE, "r", encoding="utf-8-sig") as f:
                        inbox = json.load(f)
                    inbox = [m for m in inbox if m.get("id") != message_id]
                    with open(INBOX_FILE, "w", encoding="utf-8") as f:
                        json.dump(inbox, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
        return {"success": True, "message": "Mesaj yerel sohbet geçmişinden silindi."}

    def get_chats_overview(self) -> List[Dict[str, Any]]:
        """Returns active contacts with their latest message, timestamp, and unread count."""
        contacts = []
        if CONTACTS_FILE.exists():
            try:
                with open(CONTACTS_FILE, "r", encoding="utf-8-sig") as f:
                    contacts = json.load(f).get("contacts", [])
            except Exception:
                contacts = []

        inbox = []
        if INBOX_FILE.exists():
            try:
                with open(INBOX_FILE, "r", encoding="utf-8-sig") as f:
                    inbox = json.load(f)
            except Exception:
                inbox = []

        overview = []
        for c in contacts:
            c_phone = "".join([x for x in c.get("phone", "") if x.isdigit()])
            c_name = c.get("name", "").lower()
            c_full = c.get("full_name", "").lower()
            c_lid = str(c.get("lid", ""))

            # Find all messages related to this contact
            matched_msgs = []
            for m in inbox:
                m_phone = "".join([x for x in str(m.get("phone", "")) if x.isdigit()])
                m_sender = str(m.get("sender_name", "")).lower()
                m_jid = str(m.get("chat_jid", "")) + str(m.get("sender_jid", ""))

                # Strict identity resolution: normalized phone, exact JID, or exact LID
                # Suffix matching and fuzzy substrings are eliminated to prevent cross-contact leaks
                norm_c = "".join([x for x in c_phone if x.isdigit()])
                if norm_c.startswith("0") and len(norm_c) == 11: norm_c = "90" + norm_c[1:]
                elif len(norm_c) == 10: norm_c = "90" + norm_c

                norm_m = "".join([x for x in m_phone if x.isdigit()])
                if norm_m.startswith("0") and len(norm_m) == 11: norm_m = "90" + norm_m[1:]
                elif len(norm_m) == 10: norm_m = "90" + norm_m

                phone_matched = bool(norm_c and norm_m and len(norm_c) >= 10 and len(norm_m) >= 10 and norm_c == norm_m)
                target_jid = f"{norm_c}@s.whatsapp.net" if norm_c else ""
                jid_matched = bool(target_jid and (target_jid == str(m.get("chat_jid", "")) or target_jid == str(m.get("sender_jid", ""))))
                lid_matched = bool(c_lid and len(c_lid) >= 8 and (c_lid in str(m.get("chat_jid", "")) or c_lid in str(m.get("sender_jid", ""))))

                if phone_matched or jid_matched or lid_matched:
                    matched_msgs.append(m)

            last_msg = matched_msgs[-1] if matched_msgs else None
            unread_count = sum(1 for m in matched_msgs if m.get("unread") and not m.get("from_me"))

            disp_name = f"{c['name']} ({c['full_name']})" if c.get("full_name") and c['name'] != c['full_name'] else c['name']
            overview.append({
                "id": c.get("id", c["name"]),
                "name": disp_name,
                "short_name": c["name"],
                "phone": c.get("phone", ""),
                "relationship": c.get("relationship", ""),
                "last_text": last_msg.get("text", "Henüz mesaj yok") if last_msg else "Henüz mesaj yok",
                "last_time": last_msg.get("time", "") if last_msg else "",
                "timestamp": last_msg.get("timestamp", 0) if last_msg else 0,
                "unread_count": unread_count
            })

        # Sort so contacts with recent messages are at top
        overview.sort(key=lambda x: x["timestamp"], reverse=True)
        return overview

    def get_chat_history(self, contact_query: str) -> List[Dict[str, Any]]:
        """Returns all chronological messages for a specific contact."""
        overview = self.get_chats_overview()
        target = None
        q = contact_query.lower().strip()
        for c in overview:
            if q == c["short_name"].lower() or q in c["name"].lower() or (c["phone"] and q in c["phone"]):
                target = c
                break

        if not target:
            # Do NOT fallback to first chat if contact not found; prevent private message leaks
            return []

        c_phone = "".join([x for x in target.get("phone", "") if x.isdigit()])
        c_name = target.get("short_name", "").lower()
        c_lid = ""
        # Check LID from contacts.json
        if CONTACTS_FILE.exists():
            try:
                with open(CONTACTS_FILE, "r", encoding="utf-8-sig") as f:
                    for item in json.load(f).get("contacts", []):
                        if item.get("name") == target["short_name"]:
                            c_lid = str(item.get("lid", ""))
                            break
            except Exception:
                pass

        inbox = []
        if INBOX_FILE.exists():
            try:
                with open(INBOX_FILE, "r", encoding="utf-8-sig") as f:
                    inbox = json.load(f)
            except Exception:
                inbox = []

        history = []
        for m in inbox:
            m_phone = "".join([x for x in str(m.get("phone", "")) if x.isdigit()])
            m_sender = str(m.get("sender_name", "")).lower()
            m_jid = str(m.get("chat_jid", "")) + str(m.get("sender_jid", ""))

            norm_c = "".join([x for x in c_phone if x.isdigit()])
            if norm_c.startswith("0") and len(norm_c) == 11: norm_c = "90" + norm_c[1:]
            elif len(norm_c) == 10: norm_c = "90" + norm_c

            norm_m = "".join([x for x in m_phone if x.isdigit()])
            if norm_m.startswith("0") and len(norm_m) == 11: norm_m = "90" + norm_m[1:]
            elif len(norm_m) == 10: norm_m = "90" + norm_m

            phone_matched = bool(norm_c and norm_m and len(norm_c) >= 10 and len(norm_m) >= 10 and norm_c == norm_m)
            target_jid = f"{norm_c}@s.whatsapp.net" if norm_c else ""
            jid_matched = bool(target_jid and (target_jid == str(m.get("chat_jid", "")) or target_jid == str(m.get("sender_jid", ""))))
            lid_matched = bool(c_lid and len(c_lid) >= 8 and (c_lid in str(m.get("chat_jid", "")) or c_lid in str(m.get("sender_jid", ""))))

            if phone_matched or jid_matched or lid_matched:
                history.append(m)

        history.sort(key=lambda x: x.get("timestamp", 0))
        return history

    def mark_chat_read(self, contact_query: str):
        """Marks all unread messages for a specific contact as read."""
        history = self.get_chat_history(contact_query)
        msg_ids = {m.get("id") for m in history if m.get("unread")}
        if not msg_ids:
            return

        with self.lock:
            if INBOX_FILE.exists():
                try:
                    with open(INBOX_FILE, "r", encoding="utf-8-sig") as f:
                        inbox = json.load(f)
                    for m in inbox:
                        if m.get("id") in msg_ids:
                            m["unread"] = False
                    with open(INBOX_FILE, "w", encoding="utf-8") as f:
                        json.dump(inbox, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_connected": self.is_connected(),
            "status": "connected" if self.socket_ready.is_set() else self.status,
            "has_qr": bool(self.latest_qr),
            "qr_data": self.latest_qr
        }

whatsapp_daemon = WhatsAppDaemon()
