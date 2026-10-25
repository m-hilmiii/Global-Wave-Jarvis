"""
Global-Wawe - Real WhatsApp Baileys Bridge Daemon
Manages a SINGLE Node.js Baileys subprocess, prevents zombie processes,
synchronously waits for real delivery confirmation, and maintains the WhatsApp Inbox.
"""

import os
import re
import sys
import json
import time
import logging
import subprocess
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("Jarvis.WhatsAppDaemon")

BRIDGE_DIR = Path(__file__).resolve().parent / "whatsapp_bridge"
AUTH_DIR = Path(__file__).resolve().parent.parent / "data" / "whatsapp_auth"
AUTH_DIR.mkdir(parents=True, exist_ok=True)
INBOX_FILE = AUTH_DIR.parent / "whatsapp_inbox.json"
CONTACTS_FILE = AUTH_DIR.parent / "contacts.json"
STORE_FILE = AUTH_DIR.parent / "baileys_store.json"
PUSHNAMES_FILE = AUTH_DIR.parent / "whatsapp_pushnames.json"
MEDIA_DIR = Path(__file__).resolve().parent.parent / "output" / "whatsapp_media"


def _transcribe_voice_note(media_file: Path) -> str:
    """Safe Whisper transcription of incoming voice note (.ogg/.opus/.wav/.mp3)."""
    if not media_file.exists():
        return ""
    try:
        from engine.subtitle_whisper import get_whisper_model
        model = get_whisper_model()
        segments, _ = model.transcribe(
            str(media_file),
            language="tr",
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False
        )
        return " ".join([s.text for s in segments]).strip()
    except Exception as exc:
        logger.warning(f"[WhatsApp] Voice transcription warning: {exc}")
        return ""


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
        self.latest_qr_image: Optional[str] = None
        self.lock = threading.RLock()
        self.socket_ready = threading.Event()
        self.pending_replies: Dict[str, Dict[str, Any]] = {}
        self.reply_events: Dict[str, threading.Event] = {}

        # Loop prevention for Owner Self-Chat ("Kendime Mesaj")
        self.jarvis_outbound_ids: set = set()
        self.jarvis_outbound_texts: Dict[str, float] = {}

        # AI Delegate (Meşgul Modu / Human-like Assistant Representative)
        self.ai_delegate_active: bool = False
        self.ai_delegate_targets: List[str] = []
        self.ai_delegate_logs: List[Dict[str, Any]] = []

        # Fast lookup maps for Baileys LID <-> PN & pushnames
        self._lid_to_pn: Dict[str, str] = {}
        self._pn_to_lid: Dict[str, str] = {}
        self._pushnames: Dict[str, str] = {}
        self._group_names: Dict[str, str] = {}

        if not self._is_test_mode() and self.is_authenticated():
            self.start_bridge()

    def _is_test_mode(self) -> bool:
        return (
            bool(os.environ.get("PYTEST_CURRENT_TEST")) or
            bool(os.environ.get("JARVIS_TEST_MODE")) or
            any("unittest" in arg.lower() or "pytest" in arg.lower() or "test_" in arg.lower() for arg in sys.argv)
        )

    def _read_inbox_locked(self) -> List[Dict[str, Any]]:
        """Thread-safe read of whatsapp_inbox.json under self.lock."""
        with self.lock:
            if not INBOX_FILE.exists():
                return []
            try:
                with open(INBOX_FILE, "r", encoding="utf-8-sig") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"[WhatsApp] Failed to read inbox file: {e}")
                return []

    def _atomic_write_inbox(self, data: List[Dict[str, Any]]) -> None:
        """Atomically writes inbox using a .tmp file and replace to eliminate race conditions."""
        with self.lock:
            tmp_file = INBOX_FILE.with_suffix(".tmp")
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                tmp_file.replace(INBOX_FILE)
            except Exception as e:
                logger.error(f"[WhatsApp] Atomic inbox write failed: {e}")
                if tmp_file.exists():
                    try:
                        tmp_file.unlink()
                    except Exception:
                        pass

    def is_authenticated(self) -> bool:
        creds = AUTH_DIR / "creds.json"
        return creds.exists() and creds.stat().st_size > 50

    def is_connected(self) -> bool:
        return self.is_authenticated() and self.socket_ready.is_set()

    def _kill_zombies(self):
        """Kills any orphaned bridge processes on Windows to prevent conflict 440."""
        if self._is_test_mode():
            return
        try:
            cmd = 'Get-CimInstance Win32_Process -Filter "Name = \'node.exe\'" | Where-Object { $_.CommandLine -like "*bridge.js*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }'
            subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=5)
        except Exception as e:
            logger.warning(f"Error killing zombie node processes: {e}")

    def start_bridge(self):
        """Starts the single Node.js Baileys bridge subprocess if not running."""
        if self._is_test_mode():
            return
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
                    self.latest_qr_image = ev.get("qr_image") or None
                    self.status = "qr_ready"
                    self.socket_ready.clear()
                    logger.info("[WhatsApp] New QR code generated for pairing.")

                elif ev_type == "status":
                    st = ev.get("status", "disconnected")
                    self.status = st
                    if st == "connected":
                        self.latest_qr = None
                        self.latest_qr_image = None
                        self.socket_ready.set()
                        logger.info("[WhatsApp] Socket is OPEN and ready!")
                    else:
                        self.socket_ready.clear()
                        logger.info(f"[WhatsApp] Status: {self.status}")

                elif ev_type == "sent":
                    req_id = ev.get("request_id")
                    jid = ev.get("jid", "")
                    sent_mid = ev.get("message_id")
                    with self.lock:
                        if sent_mid:
                            self.jarvis_outbound_ids.add(sent_mid)
                        if req_id and req_id in self.reply_events:
                            self.pending_replies[req_id] = {
                                "success": True,
                                "status": "sent",
                                "message_id": sent_mid,
                                "jid": jid
                            }
                            self.reply_events[req_id].set()
                        elif jid in self.reply_events:
                            self.pending_replies[jid] = {
                                "success": True,
                                "status": "sent",
                                "message_id": sent_mid,
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

                elif ev_type == "history_batch":
                    self._handle_history_batch(ev.get("messages", []))

            except json.JSONDecodeError:
                pass  # Ignore non-JSON stdout logs from node process
            except Exception as e:
                logger.error(f"[WhatsApp Daemon Stdout Error] {e}")

    def _stderr_reader(self):
        for line in iter(self.process.stderr.readline, ''):
            if not line:
                break
            try:
                if sys.stderr:
                    print(line, end='', file=sys.stderr)
            except Exception:
                pass

    def _load_lid_and_pushname_maps(self) -> tuple:
        """Loads Baileys v7 LID<->PN mappings from data/whatsapp_auth/ and PushNames/GroupNames from whatsapp_pushnames.json."""
        lid_to_pn: Dict[str, str] = {}
        pn_to_lid: Dict[str, str] = {}
        pushnames: Dict[str, str] = {}
        group_names: Dict[str, str] = {}

        if AUTH_DIR.exists():
            try:
                for p in AUTH_DIR.glob("lid-mapping-*.json"):
                    fname = p.name
                    key = fname.replace("lid-mapping-", "").replace(".json", "")
                    val = str(json.loads(p.read_text(encoding="utf-8-sig"))).strip()
                    if not val:
                        continue
                    if key.endswith("_reverse"):
                        lid = key.replace("_reverse", "")
                        lid_to_pn[lid] = val
                        pn_to_lid[val] = lid
                    else:
                        pn = key
                        pn_to_lid[pn] = val
                        lid_to_pn[val] = pn
            except Exception as e:
                logger.debug(f"[Daemon] LID map load warning: {e}")

        if PUSHNAMES_FILE.exists():
            try:
                pdata = json.loads(PUSHNAMES_FILE.read_text(encoding="utf-8-sig"))
                pushnames = pdata.get("pushnames", {}) or {}
                group_names = pdata.get("group_names", {}) or {}
                for k_lid, v_pn in (pdata.get("lid_to_pn", {}) or {}).items():
                    lid_to_pn.setdefault(k_lid, v_pn)
                    pn_to_lid.setdefault(v_pn, k_lid)
            except Exception:
                pass

        self._lid_to_pn = lid_to_pn
        self._pn_to_lid = pn_to_lid
        self._pushnames = pushnames
        self._group_names = group_names
        return lid_to_pn, pn_to_lid, pushnames, group_names

    @staticmethod
    def _format_local_phone(pn_digits: str) -> str:
        d = "".join(c for c in str(pn_digits) if c.isdigit())
        if d.startswith("90") and len(d) == 12:
            return "0" + d[2:]
        return d

    def _resolve_target_jid(self, phone_or_jid: str) -> tuple:
        """Resolves a phone number, LID, or JID into (whatsapp_jid, clean_phone_or_lid)."""
        s = str(phone_or_jid or "").strip()
        if "@g.us" in s or "@newsletter" in s:
            return s, s
        lid_to_pn, pn_to_lid, _, _ = self._load_lid_and_pushname_maps()
        user_part = s.split("@")[0].split(":")[0]
        digits = "".join(c for c in user_part if c.isdigit())
        if "@lid" in s or (len(digits) >= 13 and digits in lid_to_pn):
            mapped_pn = lid_to_pn.get(digits, "")
            if mapped_pn:
                return f"{mapped_pn}@s.whatsapp.net", mapped_pn
            return f"{digits}@lid", digits
        if digits.startswith("0") and len(digits) == 11:
            digits = "90" + digits[1:]
        elif len(digits) == 10:
            digits = "90" + digits
        jid = s if "@" in s else f"{digits}@s.whatsapp.net"
        return jid, digits

    def _resolve_sender_name(self, sender_jid: str, push_name: str = "") -> (str, str):
        lid_to_pn, pn_to_lid, pushnames, group_names = self._load_lid_and_pushname_maps()
        if "@g.us" in sender_jid:
            g_name = group_names.get(sender_jid) or push_name or sender_jid.split("@")[0]
            if g_name and "(Grup)" not in g_name:
                g_name = f"{g_name} (Grup)"
            return g_name, sender_jid

        user_part = sender_jid.split("@")[0].split(":")[0]
        raw_num = "".join([c for c in user_part if c.isdigit()])
        is_lid = "@lid" in sender_jid or (len(raw_num) >= 13 and not raw_num.startswith("90"))

        mapped_pn = lid_to_pn.get(raw_num, "") if is_lid else raw_num
        mapped_lid = raw_num if is_lid else pn_to_lid.get(raw_num, "")

        if not push_name or push_name == "." or push_name.isdigit():
            push_name = (
                pushnames.get(sender_jid)
                or (pushnames.get(f"{mapped_lid}@lid") if mapped_lid else "")
                or (pushnames.get(f"{mapped_pn}@s.whatsapp.net") if mapped_pn else "")
                or push_name
            )
        if push_name == ".":
            push_name = ""

        effective_phone = self._format_local_phone(mapped_pn) if mapped_pn else raw_num

        if CONTACTS_FILE.exists():
            try:
                with open(CONTACTS_FILE, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                    contacts = data.get("contacts", [])
                    updated = False

                    # Pass 1: Strict Phone (last 10 digits on primary or alt_phones) or Exact LID match
                    for c in contacts:
                        c_phones = [c.get("phone", "")] + list(c.get("alt_phones", []) or [])
                        phone_matches = False
                        if mapped_pn and len(mapped_pn) >= 10:
                            target_last10 = mapped_pn[-10:]
                            for cp in c_phones:
                                cp_digits = "".join([x for x in str(cp) if x.isdigit()])
                                if len(cp_digits) >= 10 and not cp_digits.startswith("9696") and cp_digits[-10:] == target_last10:
                                    phone_matches = True
                                    break

                        c_lid_str = str(c.get("lid", "")).strip()
                        lid_matches = bool(
                            c_lid_str and len(c_lid_str) >= 8 and (
                                c_lid_str == raw_num or (mapped_lid and c_lid_str == mapped_lid)
                            )
                        )
                        if phone_matches or lid_matches:
                            learn_lid = mapped_lid or (raw_num if is_lid else "")
                            if learn_lid and (not c.get("lid") or c.get("lid") != learn_lid):
                                c["lid"] = learn_lid
                                updated = True
                            disp = f"{c['name']} ({c['full_name']})" if c.get("full_name") and c['name'] != c['full_name'] else c["name"]
                            if updated:
                                try:
                                    with open(CONTACTS_FILE, "w", encoding="utf-8") as fw:
                                        json.dump(data, fw, indent=2, ensure_ascii=False)
                                except Exception as err:
                                    logger.warning(f"[Daemon] Failed to persist learned LID: {err}")
                            return disp, c.get("phone") or effective_phone

                    # Pass 2: PushName / Relationship fallback (primarily for unmapped @lid JIDs)
                    push_lower = (push_name or "").lower().strip()
                    if push_lower and len(push_lower) >= 2:
                        for c in contacts:
                            c_full_lower = c.get("full_name", "").lower().strip()
                            c_name_lower = c.get("name", "").lower().strip()
                            c_rel_lower = c.get("relationship", "").lower().strip()

                            name_or_rel_matches = False
                            if c_full_lower and c_full_lower == push_lower:
                                name_or_rel_matches = True
                            elif c_name_lower and c_name_lower == push_lower:
                                name_or_rel_matches = True
                            elif c_rel_lower in ["anne", "annem"] and any(w in push_lower for w in ["gülhan", "gulhan", "anne", "annem"]):
                                name_or_rel_matches = True
                            elif c_rel_lower in ["baba", "babam"] and any(w in push_lower for w in ["yaşar ünal", "yasar unal", "babam"]):
                                name_or_rel_matches = True

                            if name_or_rel_matches:
                                learn_lid = mapped_lid or (raw_num if is_lid else "")
                                if learn_lid and (not c.get("lid") or c.get("lid") != learn_lid):
                                    c["lid"] = learn_lid
                                    updated = True
                                disp = f"{c['name']} ({c['full_name']})" if c.get("full_name") and c['name'] != c['full_name'] else c["name"]
                                if updated:
                                    try:
                                        with open(CONTACTS_FILE, "w", encoding="utf-8") as fw:
                                            json.dump(data, fw, indent=2, ensure_ascii=False)
                                    except Exception as err:
                                        logger.warning(f"[Daemon] Failed to persist learned LID: {err}")
                                return disp, c.get("phone") or effective_phone
            except Exception as e:
                logger.error(f"[Daemon Contact Resolve Error] {e}")
        return push_name or effective_phone or raw_num or "Bilinmeyen Numara", effective_phone or raw_num

    def send_presence(self, phone_or_jid: str, status: str = "composing") -> None:
        """Sends presence update (composing / paused) to WhatsApp bridge."""
        if not self.process or self.process.poll() is not None:
            return
        jid, _ = self._resolve_target_jid(phone_or_jid)

        try:
            cmd = json.dumps({"type": "presence", "jid": jid, "status": status}) + "\n"
            if self.process.stdin:
                self.process.stdin.write(cmd.encode("utf-8"))
                self.process.stdin.flush()
        except Exception as e:
            logger.debug(f"[WhatsApp] send_presence failed: {e}")

    def _execute_fast_system_command(self, cmd_type: str, user_text: str) -> str:
        """Executes fast system commands directly without waiting for 14B model (Revision 4)."""
        try:
            if cmd_type == "lock_workstation":
                from core_jarvis.tools.system_tool import system_tool
                res = system_tool.lock_workstation()
                if res.get("success"):
                    return "🔒 **Bilgisayar Ekranı Kilitlendi:**\n\nEkran Windows + L komutuyla güvenli şekilde anında kilitlendi efendim. Güvenlik protokolü devrede."
                return f"⚠️ Ekran kilitlenirken hata oluştu: {res.get('error')}"

            elif cmd_type == "keyboard_shortcut":
                from core_jarvis.tools.system_tool import system_tool
                res = system_tool.send_keyboard_shortcut(user_text)
                return res.get("message", "Klavyeden istenen tuş kombinasyonu yürütüldü efendim.")

            elif cmd_type == "screen_inspect":
                from core_jarvis.tools.vision_tool import vision_tool
                res = vision_tool.analyze_screen(prompt="Ekrandaki aktif durumu ve hataları incele", mode="general")
                return f"🖥️ **Ekran Analizi (JARVIS Vision):**\n\n{res.get('analysis', 'Ekran görüntüsü alındı ancak analiz edilemedi.')}"

            elif cmd_type == "system_telemetry":
                from core_jarvis.tools.system_tool import system_tool
                t = system_tool.get_hardware_telemetry()
                return (
                    f"⚡ **Sistem Telemetrisi (i5-14400F + RX 9060 XT):**\n\n"
                    f"• **CPU Yükü:** %{t['cpu']['usage_percent']}\n"
                    f"• **RAM:** %{t['ram']['usage_percent']} ({t['ram']['used_gb']}GB / {t['ram']['total_gb']}GB)\n"
                    f"• **C: Sürücüsü:** %{t['disk']['usage_percent']} dolu\n"
                    f"• **GPU Durumu:** {t['gpu']['status']}\n\n"
                    f"Sistem stabil çalışıyor efendim."
                )

            elif cmd_type == "daily_briefing":
                from core_jarvis.personal_assistant import personal_assistant
                b = personal_assistant.get_daily_briefing()
                return f"📋 **Günlük Yönetici Brifingi:**\n\n{b.get('speak_text') or b.get('executive_briefing_text')}"

            elif cmd_type == "run_tests":
                from core_jarvis.orchestrator import orchestrator
                res = orchestrator.code.run_tests()
                return f"🧪 **Test Sonucu:**\n\n{'✅ Tüm testler başarıyla geçti.' if res.get('success') else '❌ Testlerde hata tespit edildi: ' + res.get('error', '')}"

            elif cmd_type == "git_diff":
                from core_jarvis.orchestrator import orchestrator
                diff = orchestrator.code.get_git_diff()
                return f"📝 **Git Değişiklikleri:**\n\n{diff.get('output', 'Çalışma alanında kaydedilmemiş değişiklik yok.')}"

            elif cmd_type == "play_youtube":
                from core_jarvis.tools.system_tool import system_tool
                res = system_tool.open_youtube_video(raw_text)
                return f"▶️ **YouTube Başlatıldı:**\n\n`{res.get('query')}` videosu bilgisayarınızda açıldı balım!"

            elif cmd_type == "browser_search":
                from core_jarvis.tools.system_tool import system_tool
                clean_search = re.sub(
                    r"^(tarayıcıda|tarayicida|tarayıcıyı\s+açıp|tarayiciyi\s+acip|google['\w]*\s+(?:da\s+|de\s+)?|webde|internette)\s+(ara\s+|aç\s+|bul\s+)?",
                    "",
                    raw_text,
                    flags=re.IGNORECASE
                ).strip(" '\".,:-")
                res = system_tool.open_browser_search(clean_search or raw_text, engine="google")
                return f"🌐 **Tarayıcıda Arama Başlatıldı:**\n\n`{clean_search or raw_text}` araması bilgisayarınızda açıldı balım!"

            elif cmd_type == "watch_series":
                from core_jarvis.tools.system_tool import system_tool
                m_ep = re.search(r"(\d+)\.?\s*sezon\s*(\d+)\.?\s*bölüm", raw_text, re.I)
                s_num = int(m_ep.group(1)) if m_ep else None
                e_num = int(m_ep.group(2)) if m_ep else None
                clean_series = re.sub(
                    r"\s*(\d+\.?\s*sezon\s*\d+\.?\s*bölüm|\bdizisind?e?\b|\bson\s+kaldığım\s+bölüm[üu]?\b|\bkaldığım\s+bölüm[üu]?\b|\baç\b|\bizle\b)",
                    "",
                    raw_text,
                    flags=re.IGNORECASE
                ).strip(" '\".,:-")
                res = system_tool.open_series_episode(clean_series or raw_text, season=s_num, episode=e_num, from_history=True)
                return f"🎬 **Dizi Oynatıcı:**\n\n{res.get('message', 'Dizi bilgisayarınızda açıldı balım.')}"

            elif cmd_type == "live_weather":
                from core_jarvis.tools.system_tool import system_tool
                w_live = system_tool.get_live_weather("Eskişehir")
                return f"🌤️ **Canlı Hava Durumu:**\n\n{w_live.get('summary_text')}"

            elif cmd_type == "ltx_status":
                from core_jarvis.tools.studio_bridge import studio_bridge
                return studio_bridge.get_ltx_status_summary()

            elif cmd_type == "ltx_video":
                from core_jarvis.tools.studio_bridge import studio_bridge
                if any(w in raw_text.lower() for w in ["hikaye", "senaryo", "film", "45", "siberpunk", "tüm sahneler"]):
                    res = studio_bridge.trigger_story_generator(all_scenes=True)
                else:
                    clean_p = re.sub(r"\b(ltx-2|ltx|ile|video|üret|yap|başlat|lütfen)\b", "", raw_text, flags=re.IGNORECASE).strip(" '\".,:-")
                    res = studio_bridge.trigger_ltx_video(prompt=clean_p or "A cinematic drone shot of a futuristic cyberpunk city at night with neon lights, photorealistic, 4k")
                return res.get("message", "LTX-2 video üretimi başlatıldı balım.")

        except Exception as exc:
            logger.error(f"[FastCommand Error] {exc}", exc_info=True)
            return f"Efendim, komut yürütülürken bir hata oluştu: {exc}"
        return "Komut yürütülemedi efendim."

    def _process_owner_message(
        self,
        jid: str,
        phone: str,
        text: str,
        is_audio: bool,
        raw_voice_text: str,
        media_info: Optional[Dict[str, Any]] = None,
        from_self_chat: bool = False
    ):
        """Processes messages from Sayın Hilmi with Hybrid Session & Self-Chat Companion support."""
        from core_jarvis.owner_session import owner_session

        effective_msg = raw_voice_text if (is_audio and raw_voice_text) else text
        if not effective_msg:
            return

        reply_target = owner_session.owner_phone if (phone == "me" or not phone or owner_session.is_owner(phone)) else phone

        # Revision 4: Trigger instant composing indicator
        self.send_presence(jid, "composing")

        try:
            # Revision 2: Strict match for closing session
            if owner_session.check_strict_close(effective_msg):
                owner_session.close_session()
                self.send_message(reply_target, "Oturum sonlandırıldı Sayın Hilmi. İyi çalışmalar dilerim. 🛡️")
                return

            # Revision 2: Strict match for clearing buffer
            if owner_session.check_buffer_clear(effective_msg):
                owner_session.clear_history()
                self.send_message(reply_target, "Oturum belleği temizlendi efendim. Sohbetimize veya yeni bir konuya devam edebiliriz.")
                return

            # Check if session is currently active
            is_active = owner_session.is_session_active()

            if not is_active:
                # Revision 1: If session is closed, voice note requires 'Jarvis' wake-word (unless in active self-chat text)
                if is_audio and not from_self_chat:
                    is_trig, clean_cmd = owner_session.is_trigger_message(raw_voice_text)
                    if not is_trig:
                        logger.info("[OwnerSession] Voice note without wake word while closed; not starting session.")
                        return
                    owner_session.start_session()
                    task_text = clean_cmd or "Emrinizdeyim efendim, oturum açıldı."
                elif from_self_chat:
                    # In 'Message Yourself' (Kendime Mesaj) chat, any message or voice note from Sayın Hilmi activates JARVIS directly
                    is_trig, clean_cmd = owner_session.is_trigger_message(effective_msg)
                    owner_session.start_session()
                    task_text = (clean_cmd if is_trig and clean_cmd else effective_msg) or "Selam Jarvis"
                else:
                    is_trig, clean_cmd = owner_session.is_trigger_message(effective_msg)
                    if not is_trig:
                        # Session closed and no trigger -> Standby
                        return
                    owner_session.start_session()
                    task_text = clean_cmd or "Selam Jarvis"
            else:
                # Session is already open: Touch 10-minute countdown
                owner_session.touch()
                is_trig, clean_cmd = owner_session.is_trigger_message(effective_msg)
                task_text = (clean_cmd if is_trig and clean_cmd else effective_msg)

            # Multimodal Image Inspection via VisionTool if owner sent an image
            if media_info and media_info.get("media_type") == "image":
                from core_jarvis.tools.vision_tool import vision_tool
                img_path = MEDIA_DIR / media_info.get("file_name", "")
                vis_res = vision_tool.analyze_image(str(img_path), prompt=task_text or "Bu görseli analiz et")
                vis_reply = f"🖼️ **Görsel Analizi (JARVIS Vision):**\n\n{vis_res.get('analysis')}"
                self.send_message(reply_target, vis_reply)
                return

            # Revision 4: Fast system command bypass
            is_fast, cmd_type = owner_session.is_fast_system_command(task_text)
            if is_fast:
                fast_reply = self._execute_fast_system_command(cmd_type, task_text)
                self.send_message(reply_target, fast_reply)
                # Revision 5: System command output is isolated from chat history!
                return

            # Conversational Chat / Unified Brain
            from core_jarvis.jarvis_brain import jarvis_brain
            brain_res = jarvis_brain.process_message(task_text, session_history=owner_session.chat_history)
            reply_text = brain_res.get("reply", "Emrinizdeyim Sayın Hilmi.")

            # Send message to owner on WhatsApp
            self.send_message(reply_target, reply_text)

            # If owner sent audio or asked for voice reply, also synthesize and send native WhatsApp voice note (PTT)
            if is_audio or any(w in effective_msg.lower() for w in ["sesli", "ses kaydı", "sesle anlat", "seslendir"]):
                try:
                    from core_jarvis.tools.voice_tool import voice_tool
                    v_res = voice_tool.synthesize_speech(reply_text, voice_name="tr-TR-AhmetNeural")
                    if v_res.get("success") and v_res.get("file_path"):
                        self.send_voice_note(reply_target, v_res["file_path"])
                except Exception as v_err:
                    logger.warning(f"[OwnerSession] Voice note synthesis warning: {v_err}")

            # Record turn in session memory
            owner_session.add_turn(task_text, reply_text)

        except Exception as exc:
            logger.error(f"[OwnerSession Error] {exc}", exc_info=True)
            self.send_message(reply_target, f"Efendim, bir aksilik oluştu: {exc}")
        finally:
            self.send_presence(jid, "paused")

    def _is_jarvis_outbound_echo(self, msg_id: str, text: str, ev: Dict[str, Any]) -> bool:
        """Detects if an incoming from_me message in self-chat was actually sent by JARVIS to prevent loops."""
        if ev.get("sent_by_jarvis"):
            return True
        if msg_id and msg_id in self.jarvis_outbound_ids:
            return True
        clean_t = (text or "").strip()
        if not clean_t:
            return False
        now = time.time()
        with self.lock:
            expired = [k for k, ts in self.jarvis_outbound_texts.items() if now - ts > 45]
            for k in expired:
                self.jarvis_outbound_texts.pop(k, None)
            if clean_t in self.jarvis_outbound_texts:
                return True
        jarvis_prefixes = (
            "🤖", "🖥️", "⚡ **", "📋 **", "🧪 **", "📝 **", "🛡️ **", "🖼️ **",
            "🎮 **", "🎵 **", "🧭 **", "🩺 **", "🎬 **", "📁 **", "🔔 **", "⚙️ **",
            "Oturum sonlandırıldı Sayın Hilmi",
            "Oturum belleği temizlendi efendim",
            "Efendim, bir aksilik oluştu:",
            "Mesajınız WhatsApp üzerinden başarıyla iletildi",
        )
        if clean_t.startswith(jarvis_prefixes):
            return True
        return False

    def _handle_incoming_message(self, ev: Dict[str, Any]):
        chat_jid = ev.get("jid", "")
        sender_jid = ev.get("sender", chat_jid)
        text = ev.get("text", "").strip()
        msg_id = ev.get("message_id", "")
        push_name = ev.get("pushName", "")
        media_info = ev.get("media")  # Multimodal attachment dict (image, pdf, zip, audio, etc.)

        if not text and not media_info:
            return

        from_me = bool(ev.get("from_me", False))
        is_history = bool(ev.get("is_history", False))
        is_jarvis_echo = from_me and self._is_jarvis_outbound_echo(msg_id, text, ev)

        # Automatic Voice Note (PTT) Transcription via Faster-Whisper (skip if JARVIS's own outbound voice note)
        raw_voice_text = ""
        is_audio = False
        if media_info and media_info.get("media_type") == "audio":
            is_audio = True
            if not is_jarvis_echo:
                fname = media_info.get("file_name", "")
                media_path = MEDIA_DIR / fname
                transcribed = _transcribe_voice_note(media_path)
                if transcribed:
                    raw_voice_text = transcribed
                    text = f"🎤 [Sesli Mesaj Transkripti]: {transcribed}"
                    logger.info(f"[WhatsApp] Transcribed voice note: '{transcribed}'")
                elif not text:
                    text = "🎤 [Sesli Mesaj]"

        raw_ts = ev.get("timestamp")
        msg_time = time.time() if not raw_ts else float(raw_ts)
        now_str = datetime.fromtimestamp(msg_time).strftime("%H:%M")

        primary_jid = chat_jid if ("@s.whatsapp.net" in chat_jid or "@lid" in chat_jid or "@g.us" in chat_jid) else sender_jid
        if from_me:
            sender_name = "JARVIS Core" if is_jarvis_echo else "Mücahit Hilmi (Ben)"
            phone = "me"
        else:
            sender_name, phone = self._resolve_sender_name(primary_jid, push_name)

        with self.lock:
            inbox = self._read_inbox_locked()

            # Prevent duplicate entries
            if any(m.get("id") == msg_id for m in inbox):
                return

            entry: Dict[str, Any] = {
                "id": msg_id,
                "chat_jid": chat_jid,
                "sender_jid": sender_jid,
                "sender_name": sender_name,
                "phone": phone,
                "text": text,
                "time": now_str,
                "timestamp": msg_time,
                "unread": False if (from_me or is_history) else True,
                "from_me": from_me,
                "media": media_info  # Persists url, media_type, file_name, file_size, mime_type
            }
            inbox.append(entry)
            inbox = inbox[-5000:]  # Keep latest 5000 messages across all chats
            self._atomic_write_inbox(inbox)
            logger.info(
                f"[WhatsApp] {'Outgoing to' if from_me else 'Incoming from'} {chat_jid} ({sender_name}): '{text}' "
                f"{'(+Media: ' + media_info.get('file_name', '') + ')' if media_info else ''}"
            )

        if is_history or is_jarvis_echo:
            return

        from core_jarvis.owner_session import owner_session
        is_self_chat = owner_session.is_owner_self_chat(chat_jid, sender_jid)

        # 1. Self-Chat ("Kendime Mesaj Atarak") or Direct Owner Message -> Route to JARVIS Owner Session
        if is_self_chat or (not from_me and (owner_session.is_owner(primary_jid) or owner_session.is_owner(phone))):
            threading.Thread(
                target=self._process_owner_message,
                args=(chat_jid or primary_jid, owner_session.owner_phone, text, is_audio, raw_voice_text, media_info, is_self_chat),
                daemon=True
            ).start()
        # 2. External Incoming Message while AI Delegate (Meşgul Modu) is active
        elif not from_me and self.ai_delegate_active and self.is_target_delegated(sender_name, phone):
            threading.Thread(
                target=self._process_delegate_message,
                args=(primary_jid, phone, sender_name, text),
                daemon=True
            ).start()

    def _handle_history_batch(self, raw_messages: List[Dict[str, Any]]):
        """Processes bulk history messages from Baileys messaging-history.set in a single atomic write."""
        if not raw_messages or not isinstance(raw_messages, list):
            return
        with self.lock:
            inbox = self._read_inbox_locked()
            existing_ids = {m.get("id") for m in inbox if m.get("id")}
            added = 0
            for ev in raw_messages:
                msg_id = ev.get("message_id", "")
                if not msg_id or msg_id in existing_ids:
                    continue
                chat_jid = ev.get("jid", "")
                sender_jid = ev.get("sender", chat_jid)
                text = ev.get("text", "").strip()
                if not text or not chat_jid or chat_jid == "status@broadcast":
                    continue
                from_me = bool(ev.get("from_me", False))
                push_name = ev.get("pushName", "")
                raw_ts = ev.get("timestamp")
                msg_time = time.time() if not raw_ts else float(raw_ts)
                now_str = datetime.fromtimestamp(msg_time).strftime("%H:%M")

                primary_jid = chat_jid if ("@s.whatsapp.net" in chat_jid or "@lid" in chat_jid or "@g.us" in chat_jid) else sender_jid
                if from_me:
                    sender_name = "Mücahit Hilmi (Ben)"
                    phone = "me"
                else:
                    sender_name, phone = self._resolve_sender_name(primary_jid, push_name)

                inbox.append({
                    "id": msg_id,
                    "chat_jid": chat_jid,
                    "sender_jid": sender_jid,
                    "sender_name": sender_name,
                    "phone": phone,
                    "text": text,
                    "time": now_str,
                    "timestamp": msg_time,
                    "unread": False,
                    "from_me": from_me,
                    "media": None
                })
                existing_ids.add(msg_id)
                added += 1

            if added > 0:
                inbox.sort(key=lambda x: x.get("timestamp", 0))
                inbox = inbox[-5000:]
                self._atomic_write_inbox(inbox)
                logger.info(f"[WhatsApp] Synced {added} historical messages into inbox.")

    def get_inbox(self, limit: int = 10, unread_only: bool = False) -> List[Dict[str, Any]]:
        messages = self._read_inbox_locked()
        if unread_only:
            messages = [m for m in messages if m.get("unread", True)]
        return messages[-limit:]

    def mark_all_read(self):
        with self.lock:
            messages = self._read_inbox_locked()
            if not messages:
                return
            for m in messages:
                m["unread"] = False
            self._atomic_write_inbox(messages)

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

        jid, clean_num = self._resolve_target_jid(phone)

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
            if text and text.strip():
                self.jarvis_outbound_texts[text.strip()] = time.time()

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
                with self.lock:
                    self.jarvis_outbound_ids.add(out_msg_id)
                out_entry = {
                    "id": out_msg_id,
                    "sender_jid": "me",
                    "chat_jid": jid,
                    "sender_name": "Mücahit Hilmi (Ben)",
                    "phone": clean_num,
                    "text": text,
                    "time": datetime.now().strftime("%H:%M"),
                    "timestamp": time.time(),
                    "unread": False,
                    "from_me": True
                }
                with self.lock:
                    inbox = self._read_inbox_locked()
                    if not any(m.get("id") == out_msg_id for m in inbox):
                        inbox.append(out_entry)
                        inbox = inbox[-5000:]
                        self._atomic_write_inbox(inbox)

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

            clean_jid, _ = self._resolve_target_jid(jid)
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
                        inbox = self._read_inbox_locked()
                        inbox = [m for m in inbox if m.get("id") != message_id]
                        self._atomic_write_inbox(inbox)
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
            inbox = self._read_inbox_locked()
            inbox = [m for m in inbox if m.get("id") != message_id]
            self._atomic_write_inbox(inbox)
        return {"success": True, "message": "Mesaj yerel sohbet geçmişinden silindi."}

    def send_voice_note(self, phone: str, audio_path: str) -> Dict[str, Any]:
        """
        Sends native WhatsApp PTT voice note (audio/ogg; codecs=opus).
        Converts .wav/.mp3 to mono opus .ogg if needed via ffmpeg.
        """
        if not self.is_authenticated():
            self.start_bridge()
            return {
                "success": False,
                "status": self.status,
                "qr": self.latest_qr,
                "error": "WhatsApp oturumu henüz bağlı değil."
            }

        jid, clean_num = self._resolve_target_jid(phone)

        src_path = Path(audio_path)
        if not src_path.exists():
            return {"success": False, "error": f"Ses dosyası bulunamadı: {audio_path}"}

        # Convert to .ogg with libopus if not already .ogg
        final_file = str(src_path)
        if src_path.suffix.lower() != ".ogg":
            ogg_dest = src_path.with_suffix(".ogg")
            try:
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(src_path), "-c:a", "libopus", "-b:a", "32k", "-ac", "1", str(ogg_dest)],
                    capture_output=True, text=True, timeout=15
                )
                if ogg_dest.exists() and ogg_dest.stat().st_size > 100:
                    final_file = str(ogg_dest)
            except Exception as fe:
                logger.warning(f"[WhatsApp] ffmpeg voice conversion warning: {fe}")

        if not self.process or self.process.poll() is not None:
            self.start_bridge()

        if not self.socket_ready.is_set():
            ready = self.socket_ready.wait(timeout=15)
            if not ready:
                return {"success": False, "error": "WhatsApp bağlantısı kuruluyor, lütfen birazdan tekrar deneyin."}

        request_id = str(uuid.uuid4())
        ack_event = threading.Event()
        with self.lock:
            self.reply_events[request_id] = ack_event
            self.pending_replies[request_id] = None
            self.jarvis_outbound_texts["🎤 [Sesli Mesaj]"] = time.time()

        payload = json.dumps({
            "type": "send_voice",
            "jid": jid,
            "file_path": final_file,
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

            confirmed = ack_event.wait(timeout=20)
            with self.lock:
                result = self.pending_replies.pop(request_id, None)
                self.reply_events.pop(request_id, None)

            if confirmed and result and result.get("success"):
                out_msg_id = result.get("message_id") or f"OUT_VOICE_{int(time.time()*1000)}"
                with self.lock:
                    self.jarvis_outbound_ids.add(out_msg_id)
                out_entry = {
                    "id": out_msg_id,
                    "sender_jid": "me",
                    "chat_jid": jid,
                    "sender_name": "Mücahit Hilmi (Ben)",
                    "phone": clean_num,
                    "text": "🎤 [Giden Sesli Mesaj]",
                    "time": datetime.now().strftime("%H:%M"),
                    "timestamp": time.time(),
                    "unread": False,
                    "from_me": True,
                    "media": {
                        "media_type": "audio",
                        "mime_type": "audio/ogg; codecs=opus",
                        "file_name": Path(final_file).name,
                        "local_path": final_file
                    }
                }
                with self.lock:
                    inbox = self._read_inbox_locked()
                    if not any(m.get("id") == out_msg_id for m in inbox):
                        inbox.append(out_entry)
                        inbox = inbox[-5000:]
                        self._atomic_write_inbox(inbox)

                return {
                    "success": True,
                    "recipient_jid": jid,
                    "status": "sent",
                    "request_id": request_id,
                    "message_id": out_msg_id,
                    "file_path": final_file
                }
            elif result and not result.get("success"):
                return {"success": False, "status": "failed", "error": f"WhatsApp ses iletim hatası: {result.get('error')}"}
            else:
                return {"success": False, "status": "unknown", "error": "WhatsApp sunucusundan ses iletim onayı zaman aşımına uğradı."}
        except Exception as e:
            with self.lock:
                self.reply_events.pop(request_id, None)
                self.pending_replies.pop(request_id, None)
            return {"success": False, "status": "failed", "error": str(e)}

    def reconnect_and_sync(self) -> Dict[str, Any]:
        """
        Clears existing WhatsApp auth tokens, terminates bridge,
        restarts fresh to trigger QR code generation and force full chat history synchronization.
        """
        with self.lock:
            try:
                if self.process and self.process.poll() is None:
                    try:
                        self.process.terminate()
                        self.process.wait(timeout=2)
                    except Exception:
                        try:
                            self.process.kill()
                        except Exception:
                            pass
                self.process = None
                self._kill_zombies()
                time.sleep(0.4)

                if AUTH_DIR.exists():
                    for item in AUTH_DIR.glob("*"):
                        try:
                            if item.is_file():
                                item.unlink()
                        except Exception:
                            pass

                qr_status_file = MEDIA_DIR / "qr_status.json"
                if qr_status_file.exists():
                    try:
                        qr_status_file.unlink()
                    except Exception:
                        pass

                self.status = "connecting"
                self.latest_qr = None
                self.latest_qr_image = None
                self.socket_ready.clear()

                self.start_bridge()
                logger.info("[WhatsApp] Reconnect & sync initiated. Session reset, awaiting new QR code.")
                return {
                    "success": True,
                    "message": "WhatsApp oturumu sıfırlandı. Yeni QR kodu oluşturuluyor, lütfen QR kodu telefonunuzla okutun.",
                    "status": self.status,
                    "qr_image": self.latest_qr_image
                }
            except Exception as e:
                logger.error(f"[WhatsApp] Reconnect & sync failed: {e}")
                return {"success": False, "error": str(e)}

    def enable_ai_delegate(self, target: Optional[str] = None):
        """Activates AI Delegate (Meşgul Modu). Target can be contact name/phone or None for all."""
        self.ai_delegate_active = True
        if target:
            clean_t = target.strip()
            if clean_t.lower() not in [x.lower() for x in self.ai_delegate_targets]:
                self.ai_delegate_targets.append(clean_t)
        logger.info(f"[WhatsApp] AI Delegate activated. Targets: {self.ai_delegate_targets or 'ALL'}")

    def disable_ai_delegate(self) -> List[Dict[str, Any]]:
        """Deactivates AI Delegate and returns conversation logs."""
        self.ai_delegate_active = False
        logs = list(self.ai_delegate_logs)
        self.ai_delegate_targets.clear()
        self.ai_delegate_logs.clear()
        logger.info(f"[WhatsApp] AI Delegate deactivated. Logged conversations: {len(logs)}")
        return logs

    def is_target_delegated(self, sender_name: str, phone: str) -> bool:
        """Checks if incoming sender is covered by AI Delegate."""
        if not self.ai_delegate_active:
            return False
        if not self.ai_delegate_targets:
            return True  # If no specific targets set, all incoming contacts are delegated
        s_low = sender_name.lower().strip()
        p_clean = "".join([c for c in phone if c.isdigit()])
        for t in self.ai_delegate_targets:
            t_low = t.lower().strip()
            t_digits = "".join([c for c in t if c.isdigit()])
            if t_low in s_low or s_low in t_low:
                return True
            if t_digits and p_clean and (t_digits.endswith(p_clean) or p_clean.endswith(t_digits)):
                return True
        return False

    def _process_delegate_message(self, jid: str, phone: str, sender_name: str, text: str):
        """Processes incoming message in AI Delegate mode, replying authentically as JARVIS."""
        self.send_presence(jid, "composing")
        try:
            # Auto-record notes / reminders into Personal Assistant
            try:
                low_text = (text or "").lower()
                if any(k in low_text for k in ["randevu", "ilet", "söyle", "soyle", "haber ver", "not al", "saat "]):
                    from core_jarvis.personal_assistant import personal_assistant
                    personal_assistant.add_note(
                        title=f"WhatsApp İletisi ({sender_name})",
                        content=text,
                        tags=["whatsapp", "ai_delegate", sender_name.lower()]
                    )
                    logger.info(f"[AIDelegate] Auto-recorded note from {sender_name}: '{text}'")
            except Exception as n_err:
                logger.debug(f"[AIDelegate] Note recording error: {n_err}")

            from core_jarvis.jarvis_brain import jarvis_brain
            history = self.get_chat_history(sender_name)
            reply = jarvis_brain.generate_delegate_reply(sender_name, text, history)
            if reply:
                self.send_message(phone, reply)
                log_entry = {
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "sender_name": sender_name,
                    "phone": phone,
                    "incoming_text": text,
                    "jarvis_reply": reply
                }
                self.ai_delegate_logs.append(log_entry)
                logger.info(f"[AIDelegate] Handled message from {sender_name}: '{text}' -> '{reply}'")
        except Exception as exc:
            logger.error(f"[AIDelegate Error] {exc}", exc_info=True)
        finally:
            self.send_presence(jid, "paused")

    def import_chat_export(self, contact_name: str, file_text: str) -> Dict[str, Any]:
        """
        Parses WhatsApp exported _chat.txt file format and populates whatsapp_inbox.json.
        """
        if not file_text:
            return {"success": False, "count": 0, "error": "Boş metin."}

        import re
        from core_jarvis.tools.contacts import contacts_mgr
        contact = contacts_mgr.find_contact(contact_name)
        c_name = contact["name"] if contact else contact_name
        c_phone = contact.get("phone", "") if contact else ""
        c_jid = f"{''.join([c for c in c_phone if c.isdigit()])}@s.whatsapp.net" if c_phone else f"{c_name.lower()}@s.whatsapp.net"

        lines = file_text.splitlines()
        imported = []
        p1 = re.compile(r"^\[(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\]\s+([^:]+):\s+(.*)$")
        p2 = re.compile(r"^(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4}),?\s+(\d{1,2}:\d{2}(?:\s*[APap][Mm])?)\s+-\s+([^:]+):\s+(.*)$")

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            m = p1.match(line_str) or p2.match(line_str)
            if m:
                d_str, t_str, s_name, body = m.groups()
                s_name = s_name.strip()
                is_me = any(k in s_name.lower() for k in ["mücahit", "mucahit", "sen", "ben", "hilmi"])
                msg_id = f"EXP_{abs(hash(f'{d_str}_{t_str}_{s_name}_{body}'))}"
                entry = {
                    "id": msg_id,
                    "chat_jid": c_jid,
                    "sender_jid": "me" if is_me else c_jid,
                    "sender_name": "Mücahit Hilmi (Ben)" if is_me else (contact.get("full_name") or c_name if contact else s_name),
                    "phone": "me" if is_me else c_phone,
                    "text": body,
                    "time": t_str[:5],
                    "timestamp": time.time(),
                    "unread": False,
                    "from_me": is_me,
                    "media": None
                }
                imported.append(entry)
            elif imported:
                imported[-1]["text"] += "\n" + line_str

        if not imported:
            return {"success": False, "count": 0, "error": "Geçerli WhatsApp sohbet satırı tespit edilemedi."}

        with self.lock:
            inbox = self._read_inbox_locked()
            existing_ids = {x.get("id") for x in inbox}
            added = 0
            for item in imported:
                if item["id"] not in existing_ids:
                    inbox.append(item)
                    existing_ids.add(item["id"])
                    added += 1
            inbox = inbox[-1000:]
            self._atomic_write_inbox(inbox)

        logger.info(f"[WhatsApp] Imported {added} messages from chat export for '{contact_name}'")
        return {"success": True, "count": added, "contact": c_name}

    def _load_messages_from_store(self, target_jid: str, raw_num: str = "", target_lid: str = "") -> List[Dict[str, Any]]:
        """Safely extracts historical messages from Baileys in-memory store JSON file."""
        if not STORE_FILE.exists():
            return []
        try:
            with open(STORE_FILE, "r", encoding="utf-8-sig") as f:
                store_data = json.load(f)
            msgs_dict = store_data.get("messages", {})
            raw_list = []
            norm_10 = raw_num[-10:] if raw_num and len(raw_num) >= 10 else raw_num
            for jid_key, msg_arr in msgs_dict.items():
                if (
                    (target_jid and target_jid in jid_key)
                    or (norm_10 and len(norm_10) >= 10 and norm_10 in jid_key)
                    or (target_lid and len(target_lid) >= 8 and target_lid in jid_key)
                ):
                    if isinstance(msg_arr, list):
                        raw_list.extend(msg_arr)

            parsed = []
            for item in raw_list:
                key = item.get("key", {})
                m_id = key.get("id", "")
                from_me = bool(key.get("fromMe", False))
                remote_jid = key.get("remoteJid") or target_jid
                ts = item.get("messageTimestamp", 0)
                if isinstance(ts, dict):
                    ts = ts.get("low", 0)
                try:
                    ts_float = float(ts)
                except Exception:
                    ts_float = 0.0
                t_str = datetime.fromtimestamp(ts_float).strftime("%H:%M") if ts_float else ""

                msg_obj = item.get("message")
                if not isinstance(msg_obj, dict) or "protocolMessage" in msg_obj:
                    continue
                text = msg_obj.get("conversation") or ""
                if not text and isinstance(msg_obj.get("extendedTextMessage"), dict):
                    text = msg_obj["extendedTextMessage"].get("text", "")
                if not text and isinstance(msg_obj.get("imageMessage"), dict):
                    text = msg_obj["imageMessage"].get("caption", "")
                if not text and isinstance(msg_obj.get("videoMessage"), dict):
                    text = msg_obj["videoMessage"].get("caption", "")

                if text and m_id:
                    parsed.append({
                        "id": m_id,
                        "chat_jid": remote_jid or target_jid,
                        "sender_jid": "me" if from_me else (remote_jid or target_jid),
                        "sender_name": "Mücahit Hilmi (Ben)" if from_me else (item.get("pushName") or ""),
                        "phone": "me" if from_me else raw_num,
                        "text": text.strip(),
                        "time": t_str,
                        "timestamp": ts_float,
                        "unread": False,
                        "from_me": from_me,
                        "media": None
                    })
            return parsed
        except Exception as e:
            logger.debug(f"[WhatsApp] Failed to read from baileys_store.json: {e}")
            return []

    def _extract_msg_identity(self, m: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts normalized counterparty phone (10-digit), LID, chat_jid, and counterparty sender name."""
        c_jid = str(m.get("chat_jid", "")).strip()
        s_jid = str(m.get("sender_jid", "")).strip()
        c_user = c_jid.split("@")[0].split(":")[0] if "@" in c_jid else c_jid
        s_user = s_jid.split("@")[0].split(":")[0] if "@" in s_jid else s_jid

        is_self_chat = bool(
            c_user in ("905518477838", "187055053267193")
            or (not c_jid and s_user in ("905518477838", "187055053267193"))
        )

        m_lid = ""
        if c_jid.endswith("@lid"):
            m_lid = c_user
        elif s_jid.endswith("@lid"):
            m_lid = s_user

        m_p10 = ""
        raw_phone = "".join(ch for ch in str(m.get("phone", "")) if ch.isdigit())
        if raw_phone:
            if raw_phone in self._lid_to_pn:
                m_lid = m_lid or raw_phone
                m_p10 = self._lid_to_pn[raw_phone][-10:]
            elif 10 <= len(raw_phone) <= 13:
                m_p10 = raw_phone[-10:]
            elif len(raw_phone) >= 14:
                m_lid = m_lid or raw_phone

        if not m_p10 and c_jid.endswith("@s.whatsapp.net"):
            jid_digits = "".join(ch for ch in c_user if ch.isdigit())
            if 10 <= len(jid_digits) <= 13:
                m_p10 = jid_digits[-10:]

        if not m_p10 and m_lid and m_lid in self._lid_to_pn:
            m_p10 = self._lid_to_pn[m_lid][-10:]

        if not m_lid and m_p10:
            m_lid = self._pn_to_lid.get("90" + m_p10, "")

        raw_sname = str(m.get("sender_name", "")).strip()
        counterparty_name = ""
        if raw_sname and raw_sname.lower() != "mücahit hilmi (ben)":
            counterparty_name = raw_sname.lower()

        return {
            "chat_jid": c_jid,
            "is_self_chat": is_self_chat,
            "p10": m_p10,
            "lid": m_lid,
            "counterparty_name": counterparty_name,
        }

    def _get_contact_keys(self, c: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts normalized 10-digit phones, LIDs, exact names, and owner flag for a contact."""
        c_id = str(c.get("id", "")).strip()
        c_name = str(c.get("name", "")).strip()
        c_full = str(c.get("full_name", "")).strip()
        c_rel = str(c.get("relationship", "")).strip().lower()
        c_lid = str(c.get("lid", "")).strip()

        phones10 = set()
        for raw_p in [c.get("phone", "")] + list(c.get("alt_phones") or []):
            digits = "".join(ch for ch in str(raw_p) if ch.isdigit())
            if digits.startswith("9696"):
                continue
            if len(digits) >= 10:
                phones10.add(digits[-10:])

        is_owner_contact = bool(
            c_id == "c_owner"
            or "5518477838" in phones10
            or c_lid == "187055053267193"
            or c_name.lower() in ("mücahit hilmi", "mücahit hilmi ünal")
        )

        lids = set()
        if c_lid:
            lids.add(c_lid)
        for p10 in phones10:
            mapped_lid = self._pn_to_lid.get("90" + p10)
            if mapped_lid:
                lids.add(mapped_lid)

        exact_names = set()
        if c_name:
            exact_names.add(c_name.lower())
        if c_full:
            exact_names.add(c_full.lower())
        if c_name and c_full:
            exact_names.add(f"{c_name.lower()} ({c_full.lower()})")

        if c_rel in ("anne", "annem") or c_id == "c_annem":
            exact_names.update({"anne", "annem", "gülhan ünal", "annem (gülhan ünal)"})
            phones10.add("5364138433")
            phones10.add("5366138433")
        elif c_rel in ("baba", "babam") or c_id == "c_babam":
            exact_names.update({"baba", "babam", "yaşar ünal", "babam (yaşar ünal)"})

        return {
            "id": c_id,
            "is_owner": is_owner_contact,
            "phones10": phones10,
            "lids": lids,
            "exact_names": exact_names,
            "rel": c_rel,
        }

    @staticmethod
    def _normalize_timestamp(ts: Any) -> float:
        """Normalizes timestamps from seconds, milliseconds, or strings to seconds float."""
        if not ts:
            return 0.0
        try:
            val = float(ts)
            return val / 1000.0 if val > 1e11 else val
        except Exception:
            return 0.0

    @classmethod
    def format_chat_time(cls, ts: float, now_dt: Optional[datetime] = None) -> str:
        """Formats message timestamp for the WhatsApp chat list:
        - Today: 'HH:MM'
        - Yesterday: 'Dün'
        - Within 7 days: 'Pazartesi', 'Salı', etc.
        - Older: 'DD.MM.YYYY'
        """
        if not ts:
            return ""
        try:
            norm_ts = cls._normalize_timestamp(ts)
            if norm_ts <= 0:
                return ""
            msg_dt = datetime.fromtimestamp(norm_ts)
            curr = now_dt or datetime.now()
            diff_days = (curr.date() - msg_dt.date()).days
            if diff_days == 0:
                return msg_dt.strftime("%H:%M")
            elif diff_days == 1:
                return "Dün"
            elif 1 < diff_days < 7:
                days_tr = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
                return days_tr[msg_dt.weekday()]
            else:
                return msg_dt.strftime("%d.%m.%Y")
        except Exception:
            return ""

    def get_chats_overview(self) -> List[Dict[str, Any]]:
        """Returns active contacts with their latest message, timestamp, and unread count."""
        self._load_lid_and_pushname_maps()
        contacts = []
        if CONTACTS_FILE.exists():
            try:
                with open(CONTACTS_FILE, "r", encoding="utf-8-sig") as f:
                    contacts = json.load(f).get("contacts", [])
            except Exception:
                contacts = []

        inbox = self._read_inbox_locked()

        # Pre-index inbox messages in a single O(M) pass for instant O(1) contact lookup
        by_p10: Dict[str, List[Dict[str, Any]]] = {}
        by_lid: Dict[str, List[Dict[str, Any]]] = {}
        by_jid: Dict[str, List[Dict[str, Any]]] = {}
        by_name: Dict[str, List[Tuple[Dict[str, Any], str]]] = {}
        self_chat_msgs: List[Dict[str, Any]] = []

        for m in inbox:
            ident = self._extract_msg_identity(m)
            if ident["is_self_chat"]:
                self_chat_msgs.append(m)
                continue
            if ident["p10"]:
                by_p10.setdefault(ident["p10"], []).append(m)
            if ident["lid"]:
                by_lid.setdefault(ident["lid"], []).append(m)
            if ident["chat_jid"]:
                by_jid.setdefault(ident["chat_jid"], []).append(m)
            if ident["counterparty_name"]:
                by_name.setdefault(ident["counterparty_name"], []).append((m, ident["p10"]))

        overview = []
        all_matched_msg_ids = set()

        for c in contacts:
            ck = self._get_contact_keys(c)
            matched_map: Dict[int, Dict[str, Any]] = {}

            if ck["is_owner"]:
                for m in self_chat_msgs:
                    matched_map[id(m)] = m
            else:
                for p10 in ck["phones10"]:
                    for m in by_p10.get(p10, ()):
                        matched_map[id(m)] = m
                for lid in ck["lids"]:
                    for m in by_lid.get(lid, ()):
                        matched_map[id(m)] = m
                if ck["id"] and "@" in ck["id"]:
                    for m in by_jid.get(ck["id"], ()):
                        matched_map[id(m)] = m
                for ename in ck["exact_names"]:
                    for m, m_p10 in by_name.get(ename, ()):
                        if not (m_p10 and ck["phones10"] and m_p10 not in ck["phones10"]):
                            matched_map[id(m)] = m

            matched_msgs = list(matched_map.values())
            matched_msgs.sort(key=lambda x: self._normalize_timestamp(x.get("timestamp", 0)))
            for m in matched_msgs:
                if m.get("id"):
                    all_matched_msg_ids.add(m.get("id"))

            last_msg = matched_msgs[-1] if matched_msgs else None
            unread_count = sum(1 for m in matched_msgs if m.get("unread") and not m.get("from_me"))

            last_ts = self._normalize_timestamp(last_msg.get("timestamp", 0)) if last_msg else 0.0
            last_time_formatted = self.format_chat_time(last_ts) if last_ts else (last_msg.get("time", "") if last_msg else "")

            disp_name = f"{c['name']} ({c['full_name']})" if c.get("full_name") and c["name"] != c["full_name"] else c["name"]
            overview.append({
                "id": c.get("id", c["name"]),
                "name": disp_name,
                "short_name": c["name"],
                "phone": c.get("phone", ""),
                "relationship": c.get("relationship", ""),
                "last_text": last_msg.get("text", "Henüz mesaj yok") if last_msg else "Henüz mesaj yok",
                "last_time": last_time_formatted,
                "timestamp": last_ts,
                "unread_count": unread_count
            })

        # Collect any remaining active chats from inbox not mapped to contacts.json
        unmatched = [
            m for m in inbox
            if m.get("id") and m.get("id") not in all_matched_msg_ids and m.get("chat_jid") != "status@broadcast"
        ]
        seen_unmatched_jids = set()
        for m in reversed(unmatched):
            c_jid = m.get("chat_jid", "")
            if not c_jid or c_jid in seen_unmatched_jids:
                continue
            seen_unmatched_jids.add(c_jid)

            chat_msgs = [x for x in unmatched if x.get("chat_jid") == c_jid]
            chat_msgs.sort(key=lambda x: self._normalize_timestamp(x.get("timestamp", 0)))
            last_m = chat_msgs[-1] if chat_msgs else m
            ident = self._extract_msg_identity(last_m)

            # Find best non-owner sender name across chat_msgs or resolve via LID/PushName maps
            s_name = ""
            for cm in reversed(chat_msgs):
                cand = str(cm.get("sender_name", "")).strip()
                if cand and cand != "Mücahit Hilmi (Ben)" and not cand.isdigit():
                    s_name = cand
                    break
            if not s_name:
                raw_p = ("0" + ident["p10"]) if ident["p10"] else c_jid.split("@")[0]
                s_name = self._resolve_sender_name(c_jid, raw_p, "")
                if s_name == "Mücahit Hilmi (Ben)":
                    s_name = raw_p

            disp_phone = ("0" + ident["p10"]) if ident["p10"] else str(last_m.get("phone", ""))
            if disp_phone == "me" or len(disp_phone) >= 14:
                disp_phone = ("0" + ident["p10"]) if ident["p10"] else ""

            unread = sum(1 for x in chat_msgs if x.get("unread") and not x.get("from_me"))
            last_ts = self._normalize_timestamp(last_m.get("timestamp", 0))
            last_time_formatted = self.format_chat_time(last_ts) if last_ts else (last_m.get("time", "") or "")

            overview.append({
                "id": c_jid,
                "name": s_name,
                "short_name": s_name,
                "phone": disp_phone,
                "relationship": "WhatsApp Grubu" if c_jid.endswith("@g.us") else "WhatsApp Sohbeti",
                "last_text": last_m.get("text", "Henüz mesaj yok"),
                "last_time": last_time_formatted,
                "timestamp": last_ts,
                "unread_count": unread
            })

        # Sort so contacts with recent messages are strictly at the top
        overview.sort(key=lambda x: self._normalize_timestamp(x.get("timestamp", 0)), reverse=True)
        return overview

    def get_chat_history(self, contact_query: str) -> List[Dict[str, Any]]:
        """Returns all chronological messages for a specific contact with strict multi-pass resolution."""
        if not contact_query or not contact_query.strip():
            return []
        self._load_lid_and_pushname_maps()
        q = contact_query.lower().strip()
        q_digits = "".join(ch for ch in q if ch.isdigit())
        q_p10 = q_digits[-10:] if len(q_digits) >= 10 else ""
        if q_digits in self._lid_to_pn:
            q_p10 = self._lid_to_pn[q_digits][-10:]

        contacts = []
        if CONTACTS_FILE.exists():
            try:
                with open(CONTACTS_FILE, "r", encoding="utf-8-sig") as f:
                    contacts = json.load(f).get("contacts", [])
            except Exception:
                contacts = []

        target_contact = None
        # Pass 1: Exact match by ID, Name, Full Name, Display Name, LID, or 10-digit Phone
        for c in contacts:
            ck = self._get_contact_keys(c)
            if (
                q == ck["id"].lower()
                or q in ck["exact_names"]
                or (q_digits and q_digits in ck["lids"])
                or (q_p10 and q_p10 in ck["phones10"])
            ):
                target_contact = c
                break

        # Pass 2: Family & Self Aliases (strict word match)
        if not target_contact:
            q_words = set(re.findall(r"[a-zçğıöşü0-9]+", q))
            if q_words & {"anne", "annem", "anneme", "annemin", "annemle", "gülhan", "gulhan"}:
                for c in contacts:
                    if c.get("id") == "c_annem" or c.get("relationship", "").lower() in ("anne", "annem") or c.get("name", "").lower() == "annem":
                        target_contact = c
                        break
            elif q_words & {"baba", "babam", "babama", "babamın", "babamla", "yaşar", "yasar"}:
                for c in contacts:
                    if c.get("id") == "c_babam" or c.get("relationship", "").lower() in ("baba", "babam") or c.get("name", "").lower() == "babam":
                        target_contact = c
                        break

        # Pass 3: Word-boundary match then substring match (preferring contacts with LID/activity and shorter names)
        if not target_contact:
            word_pat = re.compile(r"\b" + re.escape(q) + r"\b", re.IGNORECASE)
            candidates = []
            for c in contacts:
                c_name = c.get("name", "").lower()
                c_full = c.get("full_name", "").lower()
                disp = f"{c_name} ({c_full})" if c_full else c_name
                if word_pat.search(c_name) or word_pat.search(c_full):
                    candidates.append((0 if c.get("lid") else 1, len(c_name), c))
                elif len(q) >= 3 and (q in disp or (q_digits and len(q_digits) >= 7 and q_digits in str(c.get("phone", "")))):
                    candidates.append((2 if c.get("lid") else 3, len(c_name), c))
            if candidates:
                candidates.sort(key=lambda item: (item[0], item[1]))
                target_contact = candidates[0][2]

        inbox = self._read_inbox_locked()

        if target_contact:
            ck = self._get_contact_keys(target_contact)
            history = []
            for m in inbox:
                ident = self._extract_msg_identity(m)
                if ck["is_owner"]:
                    if ident["is_self_chat"]:
                        history.append(m)
                    continue
                if ident["is_self_chat"]:
                    continue
                matched = bool(
                    (ident["p10"] and ident["p10"] in ck["phones10"])
                    or (ident["lid"] and ident["lid"] in ck["lids"])
                    or (ck["id"] and "@" in ck["id"] and ident["chat_jid"] == ck["id"])
                    or (
                        ident["counterparty_name"]
                        and ident["counterparty_name"] in ck["exact_names"]
                        and not (ident["p10"] and ck["phones10"] and ident["p10"] not in ck["phones10"])
                    )
                )
                if matched:
                    history.append(m)

            # Merge additional past messages from Baileys in-memory store if available
            primary_p10 = next(iter(ck["phones10"]), "")
            clean_num = ("90" + primary_p10) if primary_p10 else ""
            t_jid = f"{clean_num}@s.whatsapp.net" if clean_num else ""
            primary_lid = next(iter(ck["lids"]), "")
            store_msgs = self._load_messages_from_store(t_jid, clean_num, target_lid=primary_lid)
            if store_msgs:
                existing_ids = {x.get("id") for x in history if x.get("id")}
                disp_name = (
                    f"{target_contact['name']} ({target_contact['full_name']})"
                    if target_contact.get("full_name") and target_contact["name"] != target_contact["full_name"]
                    else target_contact.get("name", "")
                )
                for sm in store_msgs:
                    if sm.get("id") and sm.get("id") not in existing_ids:
                        if not sm.get("from_me") and not sm.get("sender_name"):
                            sm["sender_name"] = disp_name
                        history.append(sm)
                        existing_ids.add(sm.get("id"))

            history.sort(key=lambda x: self._normalize_timestamp(x.get("timestamp", 0)))
            for m in history:
                norm_ts = self._normalize_timestamp(m.get("timestamp", 0))
                m["timestamp"] = norm_ts
                if norm_ts > 0:
                    dt = datetime.fromtimestamp(norm_ts)
                    m["time"] = dt.strftime("%H:%M")
                    m["date"] = dt.strftime("%d.%m.%Y")
            return history

        # Fallback for unsaved WhatsApp chats (by JID, resolved LID/PushName, sender_name, or phone)
        matched = []
        q_jid_base = q.split("@")[0].split(":")[0]
        for m in inbox:
            ident = self._extract_msg_identity(m)
            m_c_jid = ident["chat_jid"].lower()
            m_sender = ident["counterparty_name"]
            resolved_label = self._resolve_sender_name(ident["chat_jid"], ident["p10"], "").lower()
            if (
                q == m_c_jid
                or (q_jid_base and len(q_jid_base) >= 5 and q_jid_base == m_c_jid.split("@")[0])
                or (q_p10 and ident["p10"] == q_p10)
                or (q_digits and len(q_digits) >= 8 and ident["lid"] == q_digits)
                or (m_sender and q in m_sender)
                or (resolved_label and q in resolved_label)
            ):
                matched.append(m)

        matched.sort(key=lambda x: self._normalize_timestamp(x.get("timestamp", 0)))
        for m in matched:
            norm_ts = self._normalize_timestamp(m.get("timestamp", 0))
            m["timestamp"] = norm_ts
            if norm_ts > 0:
                dt = datetime.fromtimestamp(norm_ts)
                m["time"] = dt.strftime("%H:%M")
                m["date"] = dt.strftime("%d.%m.%Y")
        return matched

    def get_latest_incoming_message(self, contact_query: str) -> Optional[Dict[str, Any]]:
        """Returns the most recent incoming message from a contact, regardless of read status."""
        history = self.get_chat_history(contact_query)
        incoming = [m for m in history if not m.get("from_me")]
        return incoming[-1] if incoming else None

    def mark_chat_read(self, contact_query: str):
        """Marks all unread messages for a specific contact as read."""
        history = self.get_chat_history(contact_query)
        msg_ids = {m.get("id") for m in history if m.get("unread")}
        if not msg_ids:
            return

        with self.lock:
            inbox = self._read_inbox_locked()
            for m in inbox:
                if m.get("id") in msg_ids:
                    m["unread"] = False
            self._atomic_write_inbox(inbox)

    def clear_chat(self, contact_query: str) -> int:
        """Removes all messages for a specific contact from local inbox cache."""
        history = self.get_chat_history(contact_query)
        msg_ids = {m.get("id") for m in history if m.get("id")}
        if not msg_ids:
            return 0

        with self.lock:
            inbox = self._read_inbox_locked()
            remaining = [m for m in inbox if m.get("id") not in msg_ids]
            cleared_count = len(inbox) - len(remaining)
            self._atomic_write_inbox(remaining)
            logger.info(f"[Daemon] Cleared {cleared_count} messages for chat '{contact_query}'")
            return cleared_count

    def clear_all_chats(self) -> int:
        """Clears all messages from inbox cache."""
        with self.lock:
            inbox = self._read_inbox_locked()
            count = len(inbox)
            self._atomic_write_inbox([])
            logger.info(f"[Daemon] Cleared all {count} messages from inbox cache")
            return count

    def get_status(self) -> Dict[str, Any]:
        qr_img = self.latest_qr_image
        if not qr_img and not self.socket_ready.is_set():
            qr_status_file = MEDIA_DIR / "qr_status.json"
            if qr_status_file.exists():
                try:
                    st_data = json.loads(qr_status_file.read_text(encoding="utf-8"))
                    if st_data.get("qr_image"):
                        qr_img = st_data["qr_image"]
                except Exception:
                    pass
        if not qr_img and not self.socket_ready.is_set():
            qr_html_file = AUTH_DIR / "qr.html"
            if qr_html_file.exists():
                try:
                    import re
                    content = qr_html_file.read_text(encoding="utf-8")
                    m = re.search(r'src="(data:image/png;base64,[^"]+)"', content)
                    if m:
                        qr_img = m.group(1)
                except Exception:
                    pass
        return {
            "is_connected": self.is_connected(),
            "status": "connected" if self.socket_ready.is_set() else self.status,
            "has_qr": bool(self.latest_qr or qr_img),
            "qr_data": self.latest_qr,
            "qr_image": qr_img
        }

whatsapp_daemon = WhatsAppDaemon()
