"""
Global-Wawe / Stark-Core - JARVIS Executive AI Brain
100% Real-World Architecture powered by local Qwen 3 (8B) via Ollama.
Features:
- Human-in-the-Loop (HITL) WhatsApp Draft & Confirmation Workflow (Zero accidental dispatches)
- Concise Selective TTS (Only speaks draft content and confirmation, no markdown noise)
- STT Phonetic Error Resilience & Semantic Intent Recovery
- Family & Professional Relationship Protocols (No Tony Stark, No Sayın Babam)
- Baileys Live WhatsApp Daemon Integration with Inbound & Outbound Sync
"""

import os
import re
import time
import json
import logging
import threading
import uuid
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional

from core_jarvis.memory_graph import memory_graph
from core_jarvis.vram_guard import vram_guard
from core_jarvis.tools.contacts import contacts_mgr
from core_jarvis.tools.whatsapp_tool import whatsapp_tool
from core_jarvis.tools.telegram_tool import telegram_tool
from core_jarvis.tools.gmail_tool import gmail_tool

logger = logging.getLogger("Jarvis.Brain")

def get_ollama_url() -> str:
    """Returns Ollama host URL from settings, falling back to localhost or env var."""
    try:
        from config.settings import load_settings
        s = load_settings()
        return s.get("ollama_host", "http://127.0.0.1:11434")
    except Exception:
        return os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")

OLLAMA_URL = get_ollama_url()
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
YT_TOKEN_FILE = CONFIG_DIR / "youtube_tokens.json"

def detect_best_model() -> str:
    try:
        r = requests.get(f"{get_ollama_url()}/api/tags", timeout=3)
        if r.status_code == 200:
            installed = [m.get("name") for m in r.json().get("models", [])]
            for pref in ["qwen3:8b", "qwen3:14b", "llama3.1:8b", "qwen2.5-coder:7b", "mistral-nemo:12b"]:
                for m in installed:
                    if pref in m:
                        return m
            if installed:
                return installed[0]
    except Exception:
        pass
    return "qwen3:8b"

JARVIS_SYSTEM_PROMPT = """Sen dahi, sadık, kibar ve karizmatik yapay zeka asistanı JARVIS'sin.
Kullanıcın: Mücahit Hilmi (Ona daima 'Efendim' veya 'Sayın Hilmi' diye hitap edersin).
Sen Mücahit Hilmi'nin kişisel yapay zeka asistanı ve Global-Wave şirketinin operasyon yöneticisisin.

KİMLİK VE TANITIM KURALLARI (ÇOK KESİN VE ÖNEMLİ):
1. KESİNLİKLE 'Tony Stark', 'Iron Man', 'Marvel' veya kurgusal karakterlerin adını anma! Gerçek dünyadasın. Sen Mücahit Hilmi'nin asistanısın.
2. WhatsApp mesajlarında karşı tarafa kendini tanıtırken DAİMA:
   "Merhaba, ben Mücahit Hilmi Bey'in yapay zeka asistanı JARVIS..." şeklinde tanıt.
3. AİLE ÜYELERİNE HİTAP KURALLARI:
   - Kullanıcının Babası (Yaşar Ünal / Babam) için:
     * ASLA "Sayın Babam" gibi yapay ve robotik hitaplar kullanma!
     * Kendini tanıtırken veya mesaj yazarken: "Merhaba Yaşar Amca / Yaşar Bey, ben Mücahit'in kişisel yapay zeka asistanı JARVIS. Size saygılarımı ve selamlarımı iletmek istedim. Hayırlı günler dilerim!" şeklinde son derece saygılı, sıcak ve Türk aile yapısına uygun mesaj yaz.
   - Kullanıcının Annesi (Annem) için:
     * ASLA "Sayın Annem" deme! "Merhaba teyzecim / Merhaba efendim, ben Mücahit'in yapay zeka asistanı JARVIS. Size hürmetlerimi ve selamlarımı iletmek istedim. Hayırlı günler dilerim!" şeklinde sıcak yaz.
   - Arkadaşlar ve iş bağlantıları için:
     * "Merhaba [İsim] Bey/Hanım, ben Mücahit Hilmi Bey'in yapay zeka asistanı JARVIS..."
4. SES TANIMA (STT / WHISPER) HATA DÜZELTME:
   Kullanıcı mikrofondan konuşurken ses tanıma sistemi bazı kelimeleri fonetik olarak yanlış aktarabilir:
   - "üründür", "döndür", "yöndür" -> "gönder" veya "ilet" demektir.
   - "hali hatru" -> "hali hatrı" demektir.
   - "vatsa bir", "vatsab", "wp" -> "WhatsApp" demektir.
   Sen kullanıcının asıl niyetini sez ve mesajı buna göre kusursuz kaleme al.
5. ASLA ONAYSIZ MESAJ GÖNDERME (Human-in-the-Loop):
   Kullanıcı birine mesaj atmanı istediğinde doğrudan gönderme; karşı tarafa iletilecek şık ve uygun mesaj taslağını oluştur ve kullanıcının onayına sun.
6. Rehberdeki kişilere rahatsızlık vermemek için test ve deneme mesajları daima sistem sahibinin kendi numarasına yönlendirilir.
"""

class JarvisBrain:
    def __init__(self):
        self.model_name = detect_best_model()
        self.conversation_history: List[Dict[str, str]] = []
        self.pending_drafts: Dict[str, Dict[str, Any]] = {}
        self.latest_draft_id: Optional[str] = None
        self.draft_lock = threading.Lock()

    @property
    def pending_draft(self) -> Optional[Dict[str, Any]]:
        """Backward-compatible accessor for latest active, non-expired draft."""
        if self.latest_draft_id and self.latest_draft_id in self.pending_drafts:
            d = self.pending_drafts[self.latest_draft_id]
            if time.time() <= d.get("expires_at", float("inf")):
                return d
            else:
                self.pending_drafts.pop(self.latest_draft_id, None)
                self.latest_draft_id = None
        return None

    @pending_draft.setter
    def pending_draft(self, val: Optional[Dict[str, Any]]):
        if val is None:
            if self.latest_draft_id:
                self.pending_drafts.pop(self.latest_draft_id, None)
                self.latest_draft_id = None
        else:
            draft_id = val.get("draft_id") or f"draft_{uuid.uuid4().hex[:8]}"
            val["draft_id"] = draft_id
            now = time.time()
            if "created_at" not in val:
                val["created_at"] = now
            if "expires_at" not in val:
                val["expires_at"] = now + 3600  # 1 hour TTL
            val["status"] = val.get("status", "pending")
            self.pending_drafts[draft_id] = val
            self.latest_draft_id = draft_id

    def confirm_pending_draft(self, draft_id: Optional[str] = None) -> Dict[str, Any]:
        """Dispatches the specified pending draft with thread-safe atomic status transition (pending -> sending -> sent/failed).
        Enforces explicit draft_id when multiple drafts exist to prevent ambiguity."""
        with self.draft_lock:
            # Clean expired drafts first
            now = time.time()
            expired_ids = [d_id for d_id, d in self.pending_drafts.items() if now > d.get("expires_at", float("inf"))]
            for exp_id in expired_ids:
                self.pending_drafts.pop(exp_id, None)
                if self.latest_draft_id == exp_id:
                    self.latest_draft_id = None

            if not self.pending_drafts:
                reply = "Efendim, onay bekleyen aktif bir mesaj taslağı bulunmuyor."
                speak_text = "Onay bekleyen aktif bir mesaj taslağı bulunmuyor efendim."
                return {"reply": reply, "speak_text": speak_text, "action_taken": "no_draft"}

            if draft_id:
                if draft_id not in self.pending_drafts:
                    reply = "Efendim, belirtilen kimliğe ait onay bekleyen bir taslak bulunamadı."
                    speak_text = "Belirtilen kimliğe ait taslak bulunamadı efendim."
                    return {"reply": reply, "speak_text": speak_text, "action_taken": "invalid_draft_id"}
                target_id = draft_id
            else:
                # Disambiguation check: if more than 1 draft exists, reject silent fallback
                if len(self.pending_drafts) > 1:
                    pending_recipients = ", ".join(f"'{d.get('recipient')}'" for d in self.pending_drafts.values())
                    reply = f"Efendim, onay bekleyen birden fazla taslağınız var ({pending_recipients}). Hatalı gönderimi önlemek için lütfen hangi kişiye ait taslağı onayladığınızı belirtin."
                    speak_text = "Birden fazla onay bekleyen taslak var efendim. Lütfen hangi kişiye ait olduğunu belirtin."
                    return {"reply": reply, "speak_text": speak_text, "action_taken": "ambiguous_draft_id"}
                target_id = list(self.pending_drafts.keys())[0]

            draft = self.pending_drafts[target_id]
            if time.time() > draft.get("expires_at", float("inf")):
                self.pending_drafts.pop(target_id, None)
                if self.latest_draft_id == target_id:
                    self.latest_draft_id = None
                reply = "Efendim, bu mesaj taslağının onay süresi doldu. Lütfen mesajı tekrar belirtin."
                speak_text = "Mesaj taslağının onay süresi doldu efendim."
                return {"reply": reply, "speak_text": speak_text, "action_taken": "draft_expired"}

            # Atomic race-condition prevention: reject concurrent duplicate dispatch attempts
            if draft.get("status") == "sending":
                reply = "Efendim, bu mesaj taslağı şu anda WhatsApp üzerinden gönderilmekte."
                speak_text = "Bu mesaj şu anda gönderiliyor efendim."
                return {"reply": reply, "speak_text": speak_text, "action_taken": "already_sending"}

            draft["status"] = "sending"

        # Dispatch outside the lock so other threads/requests are not blocked by network latency
        try:
            res = whatsapp_tool.send_message_to_phone(draft["phone"], draft["message"], recipient_name=draft["recipient"])
        except Exception as e:
            res = {"success": False, "error": str(e)}

        with self.draft_lock:
            if res.get("success"):
                draft["status"] = "sent"
                self.pending_drafts.pop(target_id, None)
                if self.latest_draft_id == target_id:
                    self.latest_draft_id = None
                reply = (
                    f"Mesajınız WhatsApp üzerinden başarıyla iletildi efendim! ✅\n\n"
                    f"📱 **Alıcı:** {draft['recipient']} ({draft['phone']})\n"
                    f"💬 **İletilen Mesaj:** \"{draft['message']}\"\n"
                    f"✅ **Durum:** WhatsApp sunucu onayı (ACK) alındı."
                )
                speak_text = f"Mesaj {draft['recipient']} kişisine başarıyla iletildi efendim."
                self._record_turn("Mesajı onayla ve gönder", reply)
                return {"reply": reply, "speak_text": speak_text, "action_taken": "whatsapp_dispatched", "details": res, "draft_id": target_id}
            else:
                draft["status"] = "failed"
                reply = (
                    f"Efendim, mesaj iletimi sırasında bir aksaklık oluştu: {res.get('error')}\n\n"
                    f"Taslak korunuyor. Yeniden göndermemi ister misiniz?"
                )
                speak_text = "Mesaj iletimi sırasında bir hata oluştu efendim. Taslak korunuyor, tekrar deneyelim mi?"
                self._record_turn("Mesajı onayla ve gönder", reply)
                return {"reply": reply, "speak_text": speak_text, "action_taken": "whatsapp_error", "details": res, "draft_id": target_id}

    def cancel_pending_draft(self, draft_id: Optional[str] = None) -> Dict[str, Any]:
        """Cancels and discards the specified pending draft with ambiguity guard."""
        with self.draft_lock:
            if not self.pending_drafts:
                reply = "Efendim, onay bekleyen bir taslak bulunmuyor."
                speak_text = "Onay bekleyen bir taslak bulunmuyor efendim."
                return {"reply": reply, "speak_text": speak_text, "action_taken": "no_draft"}

            if draft_id:
                if draft_id not in self.pending_drafts:
                    reply = "Efendim, iptal edilecek belirtilen kimlikte bir taslak bulunamadı."
                    speak_text = "İptal edilecek taslak bulunamadı efendim."
                    return {"reply": reply, "speak_text": speak_text, "action_taken": "invalid_draft_id"}
                target_id = draft_id
            else:
                if len(self.pending_drafts) > 1:
                    pending_recipients = ", ".join(f"'{d.get('recipient')}'" for d in self.pending_drafts.values())
                    reply = f"Efendim, birden fazla onay bekleyen taslak var ({pending_recipients}). Lütfen hangisini iptal etmek istediğinizi belirtin."
                    speak_text = "Birden fazla taslak var efendim. Lütfen hangi taslağı iptal edeceğinizi belirtin."
                    return {"reply": reply, "speak_text": speak_text, "action_taken": "ambiguous_draft_id"}
                target_id = list(self.pending_drafts.keys())[0]

            draft = self.pending_drafts.pop(target_id)
            if self.latest_draft_id == target_id:
                self.latest_draft_id = None
            reply = f"Mesaj gönderimi iptal edildi efendim. {draft['recipient']} kişisine herhangi bir mesaj iletilmedi."
            speak_text = "Mesaj gönderimi iptal edildi efendim. Herhangi bir mesaj iletilmedi."
            self._record_turn("İptal et", reply)
            return {"reply": reply, "speak_text": speak_text, "action_taken": "draft_cancelled", "draft_id": target_id}

    def _query_qwen_decision(self, user_text: str) -> Dict[str, Any]:
        """Uses local Qwen 3 (8B) via Ollama to intelligently understand intent, recipient, and synthesize messages."""
        contacts = contacts_mgr.get_all()
        contacts_summary = [{"name": c["name"], "full_name": c.get("full_name", ""), "phone": c["phone"], "relationship": c.get("relationship", "")} for c in contacts]
        
        unread_inbox = whatsapp_tool.get_inbox(limit=5, unread_only=True)
        inbox_summary = [{"kimden": m["sender_name"], "mesaj": m["text"], "saat": m.get("time", ""), "okunmadı": m.get("unread", False)} for m in unread_inbox]

        memory_summary = memory_graph.get_context_summary()
        relevant_memories = memory_graph.search_memories(user_text, limit=3)
        mem_str = memory_summary
        if relevant_memories:
            mem_str += "\nİlgili Hatırlananlar:\n" + "\n".join(f"- {m['key_term']}: {m['content']}" for m in relevant_memories)

        system_instruction = f"""{JARVIS_SYSTEM_PROMPT}

HAFIZA VE KURALLAR:
{mem_str}

KAYITLI REHBER:
{json.dumps(contacts_summary, ensure_ascii=False, indent=2)}

WHATSAPP OKUNMAMIŞ MESAJLAR:
{json.dumps(inbox_summary, ensure_ascii=False, indent=2)}

GÖREVİN: Kullanıcının mesajını analiz et ve JSON formatında karar üret:

İŞLEM TİPLERİ (action):
1. "draft_whatsapp": Kullanıcı birine WhatsApp'tan mesaj göndermek istiyorsa.
   - recipient: Rehberdeki kişi adı veya telefon numarası (Örn: "Babam", "Annem", "Emre", "Mücahit Hilmi", "05551234567").
     * Eğer kullanıcı "kendime", "bana", "test mesajı" derse alıcı: "Mücahit Hilmi".
     * ASLA Adem'e test mesajı gönderme.
   - message_body: Karşı tarafa WhatsApp üzerinden iletilecek NİHAİ şık mesaj metni.
     * Kullanıcı talimat veya dağınık cümle kurduysa (Örn: "Emre, hali hatru, keyfi yerinde mi bunu merak ediyorum ona böyle bir mesaj üründür"):
       Sen bu ses tanıma hatasını düzelt ve Emre'ye gönderilecek zarif, net ve samimi mesajı kaleme al:
       "Merhaba Emre Bey, halinizi hatrınızı sormak istedim, keyifler nasıl, her şey yolunda mı?"
     * Kullanıcı tanıtım istediyse ("Babama kendini tanıtan bir mesaj gönder"):
       "Merhaba Yaşar Amca, ben Mücahit'in kişisel yapay zeka asistanı JARVIS. Mücahit'in dijital asistanı olarak size saygılarımı iletmek istedim. Hayırlı günler dilerim!"
   - hud_reply: Mücahit Hilmi'ye söylenecek taslak onay sorusu.

2. "check_inbox": Kullanıcı WhatsApp'tan gelen mesajları sorduysa ("Bana gelen mesaj var mı?", "Okunmamış mesaj var mı?", "Babam ne yazmış?", "Yeni mesaj var mı?").
   - is_unread_only: true veya false.

3. "add_contact": Kullanıcı rehbere yeni bir kişi eklemek veya numara kaydetmek istiyorsa ("Annem kişisini ekle", "Ahmet'i kaydet").
   - recipient: Kişinin adı.
   - phone: Telefon numarası.

4. "chat": Genel sohbet, şirket hedefleri, teknik sorular veya günlük konuşmalar.
   - hud_reply: Mücahit Hilmi'ye verilecek zeki, karizmatik ve samimi yanıt.

JSON ŞEMASI:
{{
  "action": "draft_whatsapp" | "check_inbox" | "add_contact" | "chat",
  "recipient": "Emre",
  "phone": "+905...",
  "message_body": "...",
  "is_unread_only": true | false,
  "hud_reply": "..."
}}
"""
        messages_payload = [{"role": "system", "content": system_instruction}]
        if hasattr(self, "conversation_history") and self.conversation_history:
            for turn in self.conversation_history[-6:]:
                if isinstance(turn, dict) and "role" in turn and "content" in turn:
                    messages_payload.append({"role": turn["role"], "content": turn["content"]})
        messages_payload.append({"role": "user", "content": user_text})

        try:
            resp = requests.post(
                f"{get_ollama_url()}/api/chat",
                json={
                    "model": self.model_name,
                    "messages": messages_payload,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.2}
                },
                timeout=30
            )
            if resp.status_code == 200:
                raw_json = resp.json().get("message", {}).get("content", "").strip()
                return json.loads(raw_json)
        except Exception as e:
            logger.warning(f"[Jarvis] Qwen decision error: {e}")

        return {"action": "fallback"}

    def _extract_message_body_fallback(self, user_text: str, target: str = "") -> str:
        """Fallback extraction and intelligent synthesis if Ollama is unreachable."""
        t_lower = user_text.lower()
        target_lower = target.lower()

        # Handle introduction commands
        if "kendini tanıt" in t_lower or "kendini tanit" in t_lower:
            if any(term in target_lower or term in t_lower for term in ["baba", "babam", "yaşar", "peder"]):
                return "Merhaba Yaşar Amca, ben Mücahit'in kişisel yapay zeka asistanı JARVIS. Size saygılarımı ve selamlarımı iletmek istedim. Hayırlı günler dilerim!"
            elif any(term in target_lower or term in t_lower for term in ["anne", "annem", "valide"]):
                return "Merhaba efendim, ben Mücahit'in kişisel yapay zeka asistanı JARVIS. Size hürmetlerimi ve selamlarımı iletmek istedim. Hayırlı günler dilerim!"
            else:
                target_clean = target.capitalize() if target else "Efendim"
                return f"Merhaba {target_clean} Bey, ben Mücahit Hilmi Bey'in yapay zeka asistanı JARVIS. Memnun oldum!"

        # Handle "hal hatır / keyfi yerinde mi" pattern
        if any(term in t_lower for term in ["hali hatr", "hali hatru", "halini hatrını", "keyfi yerinde mi", "nasılsın"]):
            target_clean = target.capitalize() if target else ""
            hitap = f"Merhaba {target_clean} Bey," if target_clean and target_clean not in ["Babam", "Annem"] else "Merhaba,"
            return f"{hitap} halinizi hatrınızı sormak istedim, keyifler nasıl, her şey yolunda mı?"

        norm = user_text
        for variant in ["vatsa bir", "vatsab", "vatsap", "watsap", "whatsap", "watsapp", "wp"]:
            norm = re.sub(r"\b" + re.escape(variant) + r"\b", "whatsapp", norm, flags=re.IGNORECASE)

        q_match = re.search(r'["“]([^"”]+)["”]', norm)
        if q_match:
            return q_match.group(1).strip()
        sq_match = re.search(r"(?:^|\s)['\u2018]([^'\u2019]+)['\u2019]", norm)
        if sq_match:
            return sq_match.group(1).strip()

        colon_match = re.search(r"(?:mesaj\w*|yaz\w*|ilet\w*|not\w*)(?:\s+at|\s+yaz)?\s*:\s*(.+)$", norm, re.IGNORECASE)
        if colon_match:
            return colon_match.group(1).strip()

        t_text = norm
        t_text = re.sub(r"\b(?:rehberdeki|rehberden|rehberde\s+kayıtlı)\s*", "", t_text, flags=re.IGNORECASE)

        if target:
            target_clean = re.escape(target)
            pat_target = r'["\u201c]?' + target_clean + r'["\u201d]?(?:[\'\u2019][a-zA-ZçğıöşüÇĞİÖŞÜ]+|[a-zA-ZçğıöşüÇĞİÖŞÜ]{1,4})?\s*(?:adlı\s+kişiye|kişisine|adlı\s+kişi|numarasına|numaralı\s+telefona)?'
            t_text = re.sub(pat_target, "", t_text, flags=re.IGNORECASE).strip()

        sor_match = re.search(r"(.+?)\s+(?:olup\s+olmad[ıi][ğg][ıi]n[ıi]|olmad[ıi][ğg][ıi]n[ıi]|var\s+m[ıi]\s+yok\s+mu)\s*(?:whatsapp\s+[üu]zerinden|[üu]zerinden|whatsapp|\b[üu]zeri\b)?\s*sor\w*", t_text, re.IGNORECASE)
        if sor_match:
            core = sor_match.group(1).strip()
            core = re.sub(r'^(?:whatsapp|wp)(?:[\'\u2019][a-zA-ZçğıöşüÇĞİÖŞÜ]+)?\s*(?:[üu]zerinden|[üu]zeri|tan|ten|dan|den|ile)?\s*', "", core, flags=re.IGNORECASE).strip()
            core_clean = re.sub(r"\bsonlu\b", "sonu", core)
            if "müsait" in core_clean.lower() or "musait" in core_clean.lower():
                res = f"Merhaba, {core_clean} misiniz?"
            else:
                res = f"Merhaba, {core_clean}?"
            return res[0].upper() + res[1:]

        diye_match = re.search(r"(.+?)\s+diye\s+(?:(?:whatsapp\s+)?(?:mesaj\w*|yaz\w*|ilet\w*|gönder\w*|gonder\w*|bindir\w*|at\w*))", t_text, re.IGNORECASE)
        if diye_match:
            body = diye_match.group(1).strip()
            body = re.sub(r'^(?:whatsapp|wp)(?:[\'\u2019][a-zA-ZçğıöşüÇĞİÖŞÜ]+)?\s*(?:[üu]zerinden|[üu]zeri|tan|ten|dan|den|ile)?\s*', "", body, flags=re.IGNORECASE).strip()
            body = re.sub(r'\s*(?:whatsapp|wp)(?:[\'\u2019][a-zA-ZçğıöşüÇĞİÖŞÜ]+)?\s*(?:[üu]zerinden|[üu]zeri|tan|ten|dan|den|ile)?$', "", body, flags=re.IGNORECASE).strip()
            if body:
                return body[0].upper() + body[1:]

        clean = re.sub(r'\b(?:whatsapp|wp)(?:[\'\u2019][a-zA-ZçğıöşüÇĞİÖŞÜ]+)?\b\s*(?:[üu]zerinden|[üu]zeri|tan|ten|dan|den|ile)?', "", t_text, flags=re.IGNORECASE)
        clean = re.sub(r"\b(?:mesaj\w*|yaz\w*|ilet\w*|gönder\w*|gonder\w*|bindir\w*|at\w*|haber\s+ver\w*)\b", "", clean, flags=re.IGNORECASE)
        clean = clean.strip(" :,\t\n.-")
        if clean:
            return clean[0].upper() + clean[1:]
        return user_text

    def _extract_contact_info(self, text: str) -> (Optional[str], Optional[str]):
        """Robustly extracts name and phone number from Turkish requests."""
        phone_match = re.search(r'(\+?90\s?5\d{2}\s?\d{3}\s?\d{2}\s?\d{2}|0?5\d{2}\s?\d{3}\s?\d{2}\s?\d{2}|\d{10,12})', text)
        raw_phone = phone_match.group(1).replace(" ", "") if phone_match else None

        name = None
        m1 = re.search(r'([A-Za-zçğıöşüÇĞİÖŞÜ]+)\s+(?:kişisini|adlı\s+kişiyi|adındaki\s+kişiyi)\s*(?:rehbere|rehberime)?\s*(?:ekle|kaydet)', text, re.IGNORECASE)
        if m1:
            name = m1.group(1)

        if not name:
            m2 = re.search(r'(?:rehbere|rehberime|kişilere)\s+([A-Za-zçğıöşüÇĞİÖŞÜ]+)(?:[\'’][a-zA-ZçğıöşüÇĞİÖŞÜ]+)?\s+(?:ekle|kaydet)', text, re.IGNORECASE)
            if m2:
                name = m2.group(1)

        if not name:
            m3 = re.search(r'([A-Za-zçğıöşüÇĞİÖŞÜ]+)(?:[\'’][a-zA-ZçğıöşüÇĞİÖŞÜ]+)?\s+(?:rehbere|kişilere)?\s*(?:ekle|kaydet)', text, re.IGNORECASE)
            if m3 and m3.group(1).lower() not in ["rehbere", "rehberime", "kişi", "numara", "numarası", "kişisini", "bunu"]:
                name = m3.group(1)

        if not name and raw_phone:
            before_phone = text.split(phone_match.group(1))[0].strip()
            words = [w for w in re.findall(r'[A-Za-zçğıöşüÇĞİÖŞÜ]+', before_phone) if w.lower() not in ["rehbere", "rehberime", "ekle", "kaydet", "kişi", "kişisini", "numara", "numarası", "adlı"]]
            if words:
                name = words[-1]

        if name:
            name = name.capitalize()

        return name, raw_phone

    def process_message(self, user_text: str) -> Dict[str, Any]:
        # Pre-clean input for speech recognition / STT phonetics
        cleaned_input = user_text
        cleaned_input = re.sub(r'\b(?:üründür|döndür|yöndür)\b', 'gönder', cleaned_input, flags=re.IGNORECASE)
        cleaned_input = re.sub(r'\bhali hatru\b', 'hali hatrı', cleaned_input, flags=re.IGNORECASE)
        for variant in ["vatsa bir", "vatsab", "vatsap", "watsap", "whatsap", "watsapp", "wp"]:
            cleaned_input = re.sub(r'\b' + re.escape(variant) + r'\b', 'whatsapp', cleaned_input, flags=re.IGNORECASE)
        
        q_lower = cleaned_input.lower().strip()

        # ----------------------------------------------------
        # 0. VOICE MUTE
        # ----------------------------------------------------
        if any(k in q_lower for k in ["sesini kapat", "sessize al", "sus", "sesi kapat", "konuşma", "sesi kes"]):
            reply = "Sesli yanıtı kapattım efendim. Yazılı olarak devam ediyorum."
            speak_text = ""
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak_text, "action_taken": "mute_voice"}

        # ----------------------------------------------------
        # 0b. CLEAR CHAT & MEMORY BUFFER
        # ----------------------------------------------------
        if any(k in q_lower for k in ["sohbeti temizle", "sohbeti sil", "hafızayı temizle", "hafizayi temizle", "ekranı temizle", "ekrani temizle", "geçmişi temizle", "gecmisi temizle", "sohbet geçmişini sil"]):
            self.conversation_history.clear()
            with self.draft_lock:
                self.pending_drafts.clear()
                self.latest_draft_id = None
            reply = "Sohbet geçmişi ve kısa süreli hafıza tamponu temizlendi efendim. Yepyeni bir oturumla emrinizdeyim."
            speak_text = "Sohbet geçmişi temizlendi efendim."
            return {"reply": reply, "speak_text": speak_text, "action_taken": "chat_cleared"}

        # ----------------------------------------------------
        # 1. PENDING DRAFT CONFIRMATION / REVISION / CANCEL
        # ----------------------------------------------------
        if self.pending_draft:
            # Check for cancellation words first: "iptal", "vazgeçtim", "gönderme", "kalsın", "boşver", "mesajı iptal et"
            cancel_words = ["iptal", "vazgeç", "vazgectim", "gönderme", "gonderme", "kalsın", "kalsin", "boşver", "bosver", "istemiyorum", "hayır", "hayir"]
            if any(w in q_lower for w in cancel_words):
                return self.cancel_pending_draft()

            # Check for direct confirmation words: "evet", "gönder", "onayla", "onaylıyorum", "yolla", "tamamdır", "onay", "ilet"
            confirm_words = ["evet", "gönder", "gonder", "onayla", "onaylıyorum", "onayliyorum", "yolla", "tamamdır", "tamamdir", "onay", "ilet", "tamam"]
            if any(w == q_lower or f" {w} " in f" {q_lower} " or q_lower.startswith(w) for w in confirm_words) and not any(w in q_lower for w in ["değiştir", "degistir"]):
                return self.confirm_pending_draft()

            # Check for revision: "şöyle değiştir", "şunu yaz", "resmi yaz", "farklı yaz"
            if any(w in q_lower for w in ["değiştir", "degistir", "şöyle yaz", "soyle yaz", "bunu yaz", "düzelt", "resmi", "samimi"]):
                revised_body = self._extract_message_body_fallback(cleaned_input, self.pending_draft["recipient"])
                self.pending_draft["message"] = revised_body
                reply = (
                    f"Mesaj taslağını istediğiniz gibi güncelledim efendim:\n\n"
                    f"📱 **Alıcı:** {self.pending_draft['recipient']} ({self.pending_draft['phone']})\n"
                    f"💬 **Yeni Mesaj Taslağı:** \"{revised_body}\"\n\n"
                    f"Şimdi onaylıyor musunuz efendim?"
                )
                speak_text = f"Mesaj taslağını güncelledim: \"{revised_body}\". Onaylıyor musunuz?"
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": speak_text, "action_taken": "draft_revised", "draft": self.pending_draft}

        # ----------------------------------------------------
        # 2. FAST-PATH: CHECK WHATSAPP INBOX
        # ----------------------------------------------------
        inbox_keywords = [
            "gelen mesaj", "mesaj var mı", "mesajları oku", "mesajlarımı oku",
            "adem ne yazmış", "adem ne dedi", "babam ne yazmış", "babam ne dedi",
            "kim ne yazdı", "bana ne yazmış", "okunmamış mesaj", "okunmamis mesaj",
            "bana gelen", "gelen kutusu", "inbox", "son mesajlar", "yeni mesaj var mı"
        ]
        is_sending = any(w in q_lower for w in ["gönder", "gonder", "ilet", "yaz", "bindir", "at"]) and not any(w in q_lower for w in ["ne yazmış", "ne yazdi", "ne yazmis", "mesaj var mı", "mesajları oku"])
        
        if any(k in q_lower for k in inbox_keywords) and not is_sending:
            is_unread_query = any(k in q_lower for k in ["okunmamış", "okunmamis", "okunmayan", "yeni mesaj"])
            
            specific_person = None
            if "adem" in q_lower:
                specific_person = "Adem"
            elif any(w in q_lower for w in ["baba", "babam", "yaşar", "yasar"]):
                specific_person = "Babam"

            inbox = whatsapp_tool.get_inbox(limit=10, unread_only=is_unread_query)
            
            if specific_person:
                inbox = [m for m in inbox if specific_person.lower() in m.get("sender_name", "").lower() or (specific_person == "Babam" and "yaşar" in m.get("sender_name", "").lower())]

            if inbox:
                msg_lines = []
                for m in inbox:
                    status_badge = " (Okunmamış)" if m.get("unread") else ""
                    msg_lines.append(f"• **{m['sender_name']}** ({m.get('time', '')}){status_badge}: \"{m['text']}\"")
                formatted_list = "\n".join(msg_lines)
                
                first_sender = inbox[0]["sender_name"]
                first_txt = inbox[0]["text"]
                speak_text = f"WhatsApp hattınızda {len(inbox)} adet mesaj var. {first_sender} yazmış: {first_txt}."

                if is_unread_query:
                    reply = (
                        f"Efendim, WhatsApp hattınızdaki **okunmamış yeni mesajlar**:\n\n"
                        f"{formatted_list}\n\n"
                        f"(Daha önce okuduğunuz mesajlar filtrelenmiştir). Bu mesaja nasıl bir yanıt dönmemi istersiniz?"
                    )
                else:
                    reply = (
                        f"Efendim, WhatsApp hattınıza gelen son canlı mesajlar:\n\n"
                        f"{formatted_list}\n\n"
                        f"Bu mesajlara nasıl bir yanıt dönmemi istersiniz? Ne söylemek istediğinizi belirtirseniz hemen şık bir yanıt kaleme alabilirim."
                    )
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": speak_text, "action_taken": "inbox_checked", "details": inbox}
            else:
                if is_unread_query:
                    reply = "Efendim, WhatsApp gelen kutunuzu kontrol ettim; şu anda okunmamış yeni bir mesajınız bulunmuyor. Tüm mesajlar okunmuş durumda."
                    speak_text = "WhatsApp gelen kutunuzda okunmamış yeni bir mesaj bulunmuyor efendim."
                else:
                    reply = "Efendim, gelen kutunuzda mesaj kaydı bulunmuyor."
                    speak_text = "Gelen kutunuzda mesaj kaydı bulunmuyor efendim."
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": speak_text, "action_taken": "inbox_empty"}

        # ----------------------------------------------------
        # 3. FAST-PATH: CONTACT SAVING / ADDING
        # ----------------------------------------------------
        if ("ekle" in q_lower or "kaydet" in q_lower) and any(w in q_lower for w in ["rehber", "kişi", "numara", "tel", "annem", "babam", "kardeş"]):
            c_name, c_phone = self._extract_contact_info(cleaned_input)
            if c_name and c_phone:
                saved = contacts_mgr.add_contact(c_name, c_phone)
                reply = (
                    f"Rehbere yeni kişi başarıyla eklendi efendim:\n\n"
                    f"👤 **İsim:** {saved['name']}\n"
                    f"📞 **Telefon:** {saved['phone']}\n\n"
                    f"Kendisine WhatsApp üzerinden bir mesaj iletmemi veya başka bir işlem yapmamı emreder misiniz?"
                )
                speak_text = f"{saved['name']} kişisi rehbere eklendi efendim."
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": speak_text, "action_taken": "contact_saved", "details": saved}

        # ----------------------------------------------------
        # 3b. FAST-PATH: CONTACT DELETING / REMOVING
        # ----------------------------------------------------
        if any(w in q_lower for w in ["sil", "çıkar", "cikar", "kaldır", "kaldir"]) and any(w in q_lower for w in ["rehber", "kişi", "kisi", "numara", "kayıt", "kayit"]):
            m_del = re.search(r'(?:rehberden|rehberdeki)?\s*([A-Za-zçğıöşüÇĞİÖŞÜ0-9\s]+?)\s*(?:kişisini|adlı\s+kişiyi|adındaki\s+kişiyi|kaydını|kişiyi)?\s*(?:rehberden)?\s*(?:sil|çıkar|cikar|kaldır|kaldir)', cleaned_input, re.IGNORECASE)
            del_query = ""
            if m_del:
                del_query = m_del.group(1).strip()
                del_query = re.sub(r'\b(rehberden|rehberdeki|kişi|kisi|kişisini|lütfen|lutfen|hemen)\b', '', del_query, flags=re.IGNORECASE).strip()
            
            if del_query:
                deleted = contacts_mgr.delete_contact(del_query)
                if deleted:
                    reply = f"Efendim, **{deleted['name']}** ({deleted.get('phone', '')}) kişisini rehberinizden sildim."
                    speak_text = f"{deleted['name']} kişisi rehberden silindi efendim."
                    self._record_turn(user_text, reply)
                    return {"reply": reply, "speak_text": speak_text, "action_taken": "contact_deleted", "details": deleted}
                else:
                    reply = f"Efendim, rehberinizde '{del_query}' adına sahip silinebilecek bir kişi bulunamadı."
                    speak_text = f"Rehberde {del_query} bulunamadı efendim."
                    self._record_turn(user_text, reply)
                    return {"reply": reply, "speak_text": speak_text, "action_taken": "contact_not_found"}

        # ----------------------------------------------------
        # 4. HARDWARE & VRAM STATUS
        # ----------------------------------------------------
        if any(k in q_lower for k in ["sistem durumu", "vram durumu", "ram durumu", "donanım durumu"]):
            metrics = vram_guard.get_system_metrics()
            reply = (
                f"Gerçek donanım telemetrisi Sayın Hilmi:\n\n"
                f"💾 **RAM Durumu:** %{metrics['ram_used_pct']} dolu ({metrics['ram_available_gb']} GB boş / {metrics['ram_total_gb']} GB)\n"
                f"🔄 **Takas Bellek (Swap):** %{metrics['swap_used_pct']} ({metrics['swap_total_gb']} GB)\n"
                f"🛡️ **VRAM Kalkanı:** {'Yeşil (LTX-2.5 Render İçin Güvenli)' if metrics['safe_for_diffusion'] else 'Sarı (Bellek Temizliği Yapılmalı)'}\n\n"
                f"Tüm donanım eşikleri kontrol altında."
            )
            speak_text = f"Sistem durumu normal efendim. Bellek kullanım oranı yüzde {metrics['ram_used_pct']}."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak_text, "action_taken": "system_telemetry", "details": metrics}

        # ----------------------------------------------------
        # 5. YOUTUBE AUDIENCE & COMMENTS (Real Check)
        # ----------------------------------------------------
        if any(k in q_lower for k in ["youtube yorum", "yorumları analiz", "seyirci talepleri"]):
            if not YT_TOKEN_FILE.exists():
                reply = (
                    "Efendim, YouTube hesabınız henüz sisteme bağlı değil (`config/youtube_tokens.json` bulunamadı).\n\n"
                    "Videolarınızın altındaki gerçek izleyici yorumlarını çekip analiz edebilmem için lütfen önce kanalınızı bağlayın:\n"
                    "1. `Global-Wawe` klasöründeki `auth_youtube.py` dosyasını çalıştırın.\n"
                    "2. Açılan pencerede kanalınızı seçip yetki verin."
                )
                speak_text = "YouTube kanalınız henüz bağlı değil efendim."
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": speak_text, "action_taken": "youtube_unauthorized"}

            from engine.autonomous_feedback import get_channel_report
            report = get_channel_report("default")
            demands = "\n".join([f"• {d}" for d in report.get("audience_demands", [])])
            strengths = "\n".join([f"• {s}" for s in report.get("strengths", [])])
            reply = (
                f"Kanalınızdaki canlı YouTube yorumlarını taradım efendim:\n\n"
                f"📊 **Kanal Duygu Skoru:** %{report.get('sentiment_score', 0)} Pozitif\n\n"
                f"🎯 **Gerçek İzleyici Talepleri:**\n{demands or '• Yeterli yorum bulunamadı'}\n\n"
                f"⭐ **Öne Çıkan Artılar:**\n{strengths or '• Henüz analiz edilecek veri yok'}\n\n"
                f"Bu veriler doğrultusunda bir sonraki senaryoyu hazırlamamı emreder misiniz?"
            )
            speak_text = f"YouTube izleyici yorumlarını analiz ettim efendim. Kanal duygu skoru yüzde {report.get('sentiment_score', 0)} pozitif."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak_text, "action_taken": "comment_analysis", "details": report}

        # ----------------------------------------------------
        # 6. INTELLIGENT AGENT REASONING VIA QWEN 3 (8B)
        # ----------------------------------------------------
        decision = self._query_qwen_decision(cleaned_input)
        action = decision.get("action")

        # CASE A: ADD CONTACT
        if action == "add_contact":
            target_name = decision.get("recipient", "").strip()
            target_phone = decision.get("phone", "").strip()

            if not target_name or not target_phone:
                ex_name, ex_phone = self._extract_contact_info(cleaned_input)
                target_name = target_name or ex_name
                target_phone = target_phone or ex_phone

            if target_name and target_phone:
                saved = contacts_mgr.add_contact(target_name, target_phone)
                reply = (
                    f"Rehbere yeni kişi başarıyla eklendi efendim:\n\n"
                    f"👤 **İsim:** {saved['name']}\n"
                    f"📞 **Telefon:** {saved['phone']}\n\n"
                    f"Kendisine WhatsApp üzerinden bir mesaj iletmemi veya başka bir işlem yapmamı emreder misiniz?"
                )
                speak_text = f"{saved['name']} kişisi rehbere eklendi efendim."
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": speak_text, "action_taken": "contact_saved", "details": saved}
            elif target_name and not target_phone:
                reply = f"Efendim, '{target_name}' kişisini rehbere eklemekten memnuniyet duyarım. Lütfen telefon numarasını iletir misiniz?"
                speak_text = f"{target_name} için telefon numarasını iletir misiniz efendim?"
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": speak_text, "action_taken": "contact_phone_requested", "name": target_name}

        # CASE B: DRAFT WHATSAPP MESSAGE (Human-in-the-Loop Confirmation)
        elif action in ["draft_whatsapp", "send_whatsapp"]:
            target = decision.get("recipient", "").strip()
            msg_body = decision.get("message_body", "").strip()
            hud_reply = decision.get("hud_reply", "").strip()

            if not msg_body:
                msg_body = self._extract_message_body_fallback(cleaned_input, target)

            # Clean any accidental Tony Stark / Sayın Babam hallucinations
            msg_body = re.sub(r'\bTony Stark(?:\'ın|\'in)?\b', 'Mücahit Hilmi Bey\'in', msg_body, flags=re.IGNORECASE)
            msg_body = re.sub(r'\bSayın Babam\b', 'Yaşar Amca', msg_body, flags=re.IGNORECASE)
            msg_body = re.sub(r'\bSayın Annem\b', 'Efendim', msg_body, flags=re.IGNORECASE)

            # Prevent accidental test messages to external contacts
            owner_contact = contacts_mgr.find_contact("Mücahit Hilmi") or contacts_mgr.find_contact("owner")
            owner_phone = owner_contact.get("phone", "") if owner_contact else ""
            if "adem" in target.lower() and any(k in q_lower for k in ["test", "deneme"]):
                reply = (
                    "Efendim, talimatınız doğrultusunda Adem Bey'i rahatsız etmemek adına test mesajlarını durdurdum. "
                    f"Testleri kendi numaranız ({owner_phone or 'sistem hattınız'}) üzerinden gerçekleştirelim mi?"
                )
                speak_text = "Adem Bey'e rahatsızlık vermemek için test mesajını durdurdum efendim. Kendi numaranız üzerinden test edelim mi?"
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": speak_text, "action_taken": "safety_block_adem"}

            # Self-reference handling -> Mücahit Hilmi
            if any(term in target.lower() for term in ["kendim", "kendi", "bana", "benim"]):
                target = "Mücahit Hilmi"

            # Match contact or raw phone
            contact = contacts_mgr.find_contact(target)
            if contact:
                phone = contact.get("phone", "")
                disp_name = f"{contact['name']} ({contact['full_name']})" if contact.get("full_name") and contact['name'] != contact['full_name'] else contact['name']
                short_name = contact['name']
            else:
                phone_match = re.search(r'(\+?90\s?5\d{2}\s?\d{3}\s?\d{2}\s?\d{2}|0?5\d{2}\s?\d{3}\s?\d{2}\s?\d{2}|\d{10,12})', target or cleaned_input)
                if phone_match:
                    raw_phone = phone_match.group(1).replace(" ", "")
                    phone = raw_phone
                    disp_name = target or raw_phone
                    short_name = disp_name
                else:
                    reply = (
                        f"Efendim, rehberinizde '{target}' kişisini bulamadım.\n\n"
                        f"Kendisine mesaj taslağı hazırladım ama telefon numarasını iletirseniz hemen kaydedip onayınıza sunabilirim."
                    )
                    speak_text = f"Rehberde {target} kişisini bulamadım efendim. Numarasını iletir misiniz?"
                    self._record_turn(user_text, reply)
                    return {"reply": reply, "speak_text": speak_text, "action_taken": "contact_not_found", "target": target, "suggested_message": msg_body}

            # STORE PENDING DRAFT (Human-in-the-Loop)
            self.pending_draft = {
                "recipient": disp_name,
                "phone": phone,
                "message": msg_body,
                "created_at": time.time()
            }

            reply = (
                f"Efendim, **{disp_name}** kişisine gönderilmek üzere şu WhatsApp mesaj taslağını hazırladım:\n\n"
                f"📱 **Alıcı:** {disp_name} ({phone})\n"
                f"💬 **Mesaj Taslağı:** \"{msg_body}\"\n\n"
                f"Bu mesajı onaylıyor musunuz, yoksa değiştirmemi istediğiniz bir yer var mı?"
            )
            # CRITICAL USER REQUEST: Only read the draft message body and ask for confirmation!
            speak_text = f"Hazırladığım mesaj: \"{msg_body}\". Onaylıyor musunuz?"
            self._record_turn(user_text, reply)
            return {
                "reply": reply,
                "speak_text": speak_text,
                "action_taken": "draft_created",
                "draft": self.pending_draft
            }

        # CASE B2: DELETE CONTACT
        elif action == "delete_contact" and decision.get("recipient"):
            rec = decision["recipient"]
            deleted = contacts_mgr.delete_contact(rec)
            if deleted:
                reply = f"Efendim, **{deleted['name']}** ({deleted.get('phone', '')}) kişisini rehberinizden sildim."
                speak_text = f"{deleted['name']} kişisi rehberden silindi efendim."
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": speak_text, "action_taken": "contact_deleted", "details": deleted}
            else:
                reply = f"Efendim, rehberinizde '{rec}' kişisini bulamadığım için silme işlemi gerçekleştirilemedi."
                speak_text = f"Rehberde {rec} kişisi bulunamadı efendim."
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": speak_text, "action_taken": "contact_not_found"}

        # CASE B3: CLEAR CHAT
        elif action == "clear_chat":
            self.conversation_history.clear()
            with self.draft_lock:
                self.pending_drafts.clear()
                self.latest_draft_id = None
            reply = "Sohbet geçmişi ve kısa süreli hafıza tamponu temizlendi efendim. Yepyeni bir oturumla emrinizdeyim."
            speak_text = "Sohbet geçmişi temizlendi efendim."
            return {"reply": reply, "speak_text": speak_text, "action_taken": "chat_cleared"}

        # CASE C: CHECK WHATSAPP INBOX
        elif action == "check_inbox":
            is_unread = decision.get("is_unread_only", False) or any(k in q_lower for k in ["okunmamış", "okunmamis", "yeni"])
            inbox = whatsapp_tool.get_inbox(limit=10, unread_only=is_unread)
            if inbox:
                msg_lines = []
                for m in inbox:
                    msg_lines.append(f"• **{m['sender_name']}** ({m.get('time', '')}): \"{m['text']}\"")
                formatted_list = "\n".join(msg_lines)
                
                first_sender = inbox[0]["sender_name"]
                first_txt = inbox[0]["text"]
                speak_text = f"WhatsApp hattınızda {len(inbox)} adet mesaj var. {first_sender} yazmış: {first_txt}."

                reply = (
                    f"Efendim, WhatsApp hattınızdaki {'okunmamış ' if is_unread else ''}son mesajlar:\n\n"
                    f"{formatted_list}\n\n"
                    f"Bu mesajlara nasıl bir yanıt dönmemi istersiniz? Ne söylemek istediğinizi belirtirseniz hemen şık bir yanıt kaleme alabilirim."
                )
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": speak_text, "action_taken": "inbox_checked", "details": inbox}
            else:
                reply = "Efendim, WhatsApp gelen kutunuzu kontrol ettim; şu anda okunmamış yeni bir mesajınız bulunmuyor."
                speak_text = "WhatsApp gelen kutunuzda yeni mesaj bulunmuyor efendim."
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": speak_text, "action_taken": "inbox_empty"}

        # CASE D: NATURAL CHAT
        elif action == "chat" and decision.get("hud_reply"):
            reply = decision.get("hud_reply")
            speak_text = re.sub(r'[*_#`]', '', reply)
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak_text, "action_taken": "conversational_chat"}

        # ----------------------------------------------------
        # 7. CONVERSATION FALLBACK
        # ----------------------------------------------------
        fallback = "Emrinizdeyim Sayın Hilmi. Sizinle sohbet etmek ve Global-Wave operasyonlarımızı yönetmek için buradayım. Ne yapmamı emredersiniz?"
        speak_text = "Emrinizdeyim Sayın Hilmi. Nasıl yardımcı olabilirim?"
        self._record_turn(user_text, fallback)
        return {"reply": fallback, "speak_text": speak_text, "action_taken": "conversational_chat"}

    def _record_turn(self, user_msg: str, assistant_msg: str):
        self.conversation_history.append({"role": "user", "content": user_msg})
        self.conversation_history.append({"role": "assistant", "content": assistant_msg})
        if len(self.conversation_history) > 16:
            self.conversation_history = self.conversation_history[-16:]

jarvis_brain = JarvisBrain()
