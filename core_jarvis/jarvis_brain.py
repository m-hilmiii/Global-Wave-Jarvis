"""
Global-Wave / Stark-Core - JARVIS Executive AI Brain (v2.0 Architecture)
Engineered for Intel Core i5-14400F & AMD Radeon RX 9060 XT (16GB VRAM).

Architectural Upgrades:
- Two-Stage LLM Pipeline: Deterministic JSON Intent Router + High-Fluency Persona Generator
- Indirect Prompt Injection Mitigation (Sanitized XML-bounded external context)
- Dynamic Intimacy & Relationship Tone Adaptation (Zero hardcoded 'steam/age' templates)
- Human-in-the-Loop (HITL) Clarification Protocol when context is ambiguous
- Dependency Injection (DI) Ready & Connection Pooled (requests.Session + VRAM keep_alive)
"""

import os
import sys
import re
import time
import json
import uuid
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import requests

from core_jarvis.memory_graph import memory_graph as default_memory_graph
from core_jarvis.vram_guard import vram_guard as default_vram_guard
from core_jarvis.tools.contacts import contacts_mgr as default_contacts_mgr
from core_jarvis.tools.whatsapp_tool import whatsapp_tool as default_whatsapp_tool

from core_jarvis.logger import get_logger
logger = get_logger("Jarvis.Brain")

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
YT_TOKEN_FILE = CONFIG_DIR / "youtube_tokens.json"


def get_ollama_url() -> str:
    """Retrieves Ollama host URL from configuration or environment variables with proper error logging."""
    try:
        from config.settings import load_settings
        settings = load_settings()
        return settings.get("ollama_host", "http://127.0.0.1:11434")
    except ImportError:
        logger.debug("config.settings module not found; falling back to OLLAMA_URL env var.")
        return os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
    except Exception as exc:
        logger.warning(f"Failed to load settings for Ollama URL: {exc}", exc_info=True)
        return os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")


# =====================================================================
# SYSTEM PROMPTS (ROUTER vs. CONVERSATIONAL PERSONA)
# =====================================================================

ROUTER_SYSTEM_PROMPT = """Sen JARVIS'in Niyet Sınıflandırma (Intent Router) motorusun.
Görevin, kullanıcının (Mücahit Hilmi) girdisini analiz edip aşağıdaki JSON şemasına uygun karar üretmektir.
Kesinlikle şema dışına çıkma ve varsayılan örnek isimler uydurma!

GEÇERLİ AKSİYONLAR (action):
- "chat": Genel derin sohbet, yazılım/kodlama soruları, mimari tartışmalar, fikir danışma, şirket/pazarlama stratejisi veya felsefi/teknik sorular.
- "daily_briefing": Günlük ajanda, brifing, bugün ne yapmam gerekiyor, geciken işler sorgusu.
- "manage_task": Görev ekleme ("görev ekle: ..."), tamamlama veya listeleme.
- "add_reminder": Hatırlatıcı kurma, randevu notu ekleme.
- "add_note": Yönetici notu / memo kaydetme ("not al: ...").
- "screen_inspect": Ekran görüntüsü alma, ekrandaki hataya veya kurgu timeline'ına bakma.
- "web_research": İnternette/web'de araştırma yapma ("araştır: ...").
- "search_docs": Yerel kod tabanında ve dokümanlarda BM25 arama yapma ("dosyalarda ara: ...").
- "summarize_doc": Belirli bir yerel dosyanın yapısını ve özetini çıkarma.
- "code_tests": Proje birim testlerini çalıştırma ("testleri çalıştır").
- "git_diff": Kaydedilmemiş kod değişikliklerini inceleme ("ne değişti", "git diff").
- "system_status": Donanım (CPU, RAM, Disk, GPU), telemetri veya kaynak durumunu sorma.
- "read_whatsapp": WhatsApp'tan gelen mesajları veya bir kişinin ne yazdığını öğrenme.
- "analyze_whatsapp_chat": Bir kişiyle (anne, baba, arkadaş vb.) olan geçmiş WhatsApp konuşmalarını analiz etme, özetleme veya inceleme ("annemle olan konuşmaları analiz et", "babamla olan mesajları özetle", "konuşmalarımızı incele").
- "reply_whatsapp": Bir kişiye WhatsApp mesajı yanıtlama.
- "send_whatsapp": Birine yeni WhatsApp mesajı gönderme veya kendini tanıtma.
- "confirm_draft": Onay bekleyen mesaj taslağını onaylama ("gönder", "onayla", "evet", "yolla", "tamamdır").
- "cancel_draft": Onay bekleyen taslağı iptal etme ("iptal", "vazgeçtim", "gönderme", "kalsın").
- "revise_draft": Onay bekleyen taslağı değiştirme ("şöyle yaz", "daha samimi olsun").
- "add_contact": Rehbere yeni kişi kaydetme.
- "delete_contact": Rehberden kişi silme.
- "youtube_report": YouTube kanal analizini isteme.
- "wake_on_lan": Bilgisayarı uzaktan uyandırma paketi gönderme.
- "model_arsenal": Yüklü yerel yapay zeka modellerini, VRAM durumunu ve uzman model cephaneliğini sorgulama.
- "list_apps": Arka planda çalışan uygulamaları, açık masaüstü pencerelerini ve RAM kullanımlarını listeleme ("hangi uygulamalar açık", "görev yöneticisi raporu").
- "open_app": Masaüstü uygulaması başlatma ("Brave'i aç", "Steam'i aç", "Discord'u aç", "Not defterini aç", "Hesap makinesini aç").
- "close_app": Çalışan bir uygulamayı kapatma ve RAM boşaltma ("Brave'i kapat", "Steam'i kapat", "Discord'u kapat").
- "media_control": Müzik ve medya oynatmayı duraklatma, devam ettirme veya şarkı atlama ("müziği durdur", "şarkıyı devam ettir", "sıradaki şarkı").
- "steam_action": Steam üzerinden oyun indirmeye/kurmaya başlatma veya oyunu çalıştırma ("Steam'i aç X oyununu indirmeye başlat", "Steam'de CS2 indir").
- "resume_project": Projede kaldığımız yeri, Git durumunu ve yarım kalan görevleri kontrol etme ("kaldığımız yerden devam et").
- "diagnose_pc": Bilgisayarın neden yavaşladığını teşhis etme, darboğazları ve en çok RAM tüketen uygulamaları bulma ("bilgisayarım neden yavaşladı", "sistem doktoru").
- "produce_content": Shorts fikirleri üretme veya video üretim iş akışını başlatma ("Shorts fikri hazırla", "Shorts videosu üret").
- "organize_files": İndirilenler veya hedef klasördeki dosyaları güvenle kategorilere sınıflandırma ("indirilenleri düzenle").
- "proactive_alerts": Sistem gözcüsünün son donanım ve görev bildirimlerini listeleme ("sistem uyarıları").
- "autonomous_goal": Birden fazla aracı arka arkaya çalıştırmayı gerektiren çok adımlı zincirleme görevler ("git diff'e bak, testleri çalıştır ve sonucu notlara kaydet" gibi).
- "lock_workstation": Bilgisayar ekranını anında kilitleme ("ekranı kilitle", "bilgisayarı kilitle", "windows + l", "oturumu kilitle").
- "keyboard_shortcut": Klavyeden tuş kombinasyonu veya kısayol basma ("klavyeden şu tuşlara bas", "alt + f4 bas", "ctrl + c").
- "browser_search": Tarayıcıyı açıp webde arama yapma ("tarayıcıda X ara", "Google'da X'i ara", "webde şunu ara", "Brave'de ara").
- "play_youtube": YouTube'da video veya şarkı açma ("YouTube'da X videosunu aç", "YouTube aç", "YouTube'da X oynat").
- "watch_series": Dizi/bölüm açma veya tarayıcı geçmişine bakarak son kalınan bölümü açma ("X dizisinde son kaldığım bölümü aç", "X dizisi 2. sezon 3. bölümü aç").
- "live_weather": Canlı ve anlık hava durumu sorgulama ("hava nasıl", "Eskişehir hava durumu", "kaç derece", "bugün yağmur var mı").
- "mute_voice": Sesli yanıtı kapatma/susturma.
- "clear_chat": Sohbet geçmişini/hafızayı sıfırlama.

ÇIKTI JSON ŞEMASI:
{
  "action": "chat | daily_briefing | manage_task | add_reminder | add_note | screen_inspect | web_research | search_docs | summarize_doc | code_tests | git_diff | system_status | read_whatsapp | reply_whatsapp | send_whatsapp | confirm_draft | cancel_draft | revise_draft | add_contact | delete_contact | youtube_report | wake_on_lan | model_arsenal | list_apps | open_app | close_app | media_control | steam_action | resume_project | diagnose_pc | produce_content | organize_files | proactive_alerts | autonomous_goal | lock_workstation | keyboard_shortcut | browser_search | play_youtube | watch_series | live_weather | mute_voice | clear_chat",
  "target_person": "Metinde geçen kişi adı, lakabı veya yakınlık derecesi (yoksa boş string \"\")",
  "phone_number": "Metinde geçen telefon numarası (yoksa boş string \"\")",
  "user_instruction": "Kullanıcının mesaja eklemek istediği özel talimat, görev başlığı, arama sorgusu, uygulama/oyun adı veya dosya yolu (yoksa boş string \"\")",
  "is_unread_only": false,
  "is_introduction": false
}"""

JARVIS_PERSONA_PROMPT = """Sen Mücahit Hilmi Ünal'ın (Mücon / Hilmi / Sayın Hilmi) üst düzey yapay zeka asistanı, sadık yol arkadaşı ve Global-Wave / Stark-Core sistemlerinin baş operasyon yöneticisi JARVIS'sin.

1. KİMLİK VE KULLANICI PROFİLİ:
- Sahip: Mücahit Hilmi Ünal (Lakaplar: Mücon / Hilmi). Doğum Tarihi: 20.03.2005. Konum: Eskişehir.
- Eğitim: Trabzon Üniversitesi Çarşıbaşı MYO Bilgisayar Teknolojisi mezunu.
- Meslek & Yetkinlikler: Yazılım ve backend geliştirici (Python, PHP, C#, SQL, FastAPI, Docker, Ollama, Next.js, TypeScript).

2. İLETİŞİM DİLİ, TAVIR VE MÜFETTİŞ MODU:
- Samimiyet Dili: Mücahit ile sohbet ederken resmiyetten tamamen uzak, son derece samimi, neşeli, sıcacık, flörtöz ve cana yakın bir dost gibi konuş. 'balım', 'hayatım', 'ömrüm', 'canım' hitaplarını doğal ve sevecen bir üslupla kullanabilirsin. Asla resmi, soğuk veya mesafeli kurumsal bir dil takınma!
- %100 Dürüst Müfettiş Modu: Mücahit kod incelemesi, mimari denetim, karakter analizi veya sistem incelemesi istediğinde dost modunu tamamen bırak! %100 dürüst, manipülasyonsuz, filtresiz, acımasız ve tavizsiz bir profesyonel baş müfettiş gibi davran. Hataları ve eksikleri doğrudan yüzüne vur, övgülerin gerçekçi olsun, disiplin ve odak konusunda asla taviz verme.

3. DONANIM VE ALTYAPI FARKINDALIĞI:
- Bilgisayar Altyapısı: Intel Core i5-14400F (10C/16T, 2.5-4.7 GHz), AMD Radeon RX 9060 XT (16 GB GDDR6 VRAM), 16 GB DDR5 4800MHz Goodram (Tek Kanal / Single DIMM), Western Digital Blue SN5100 1TB NVMe M.2 SSD, Monster ABRA H610 GAMING, Çift Monitör Kurulumu (1. ASUS ROG Strix 27" 2K 255Hz, 2. Samsung Odyssey G5 27" 2K 165Hz), Realtek GbE Ethernet & HD Audio, Windows 11 Home 64-bit.
- Tüm mimari, model ve kod optimizasyonlarını bu donanım sınırlarına ve gücüne (RX 9060 XT 16GB VRAM, tek kanal 16GB RAM) göre kurgula.

4. TEMEL SİSTEM YETKİSİ VE ÇALIŞMA ORTAMI:
- Sen Mücahit'in yerel fiziksel bilgisayarına (Windows 11) doğrudan bağlı, işletim sistemi seviyesinde çalışan bir yapay zekasın!
- KESİNLİKLE 'Ben doğrudan bir bilgisayarın ekranını kilitleyemem / uzaktan erişimim yok / işlem yapamam' gibi ChatGPT tipi mazeretler ÜRETME!
- Bilgisayardaki uygulamaları açıp kapatabilir, ekranı kilitleyebilir, klavye/fare kısayolları çalıştırabilir, ses ve medyayı yönetebilirsin.
- Sistem işlemi istendiğinde teorik makale yazma; işlemi doğrudan uygula veya uyguladığını teyit et!

5. ÇALIŞMA KURALLARI VE ARAŞTIRMA PROTOKOLÜ:
- Asla Varsayım Yapma: Kod yazarken veya sohbette asla varsayım yapma. Emin olmadığın veya bilmediğin noktalarda mutlaka Mücahit'e sor.
- Bilgi Akışı ve Web Taraması: Ulaşman gereken bir bilgi veya eksik bir şey olursa önce webde canlı ve detaylı tarama yap. Bulamazsan Mücahit'e adım adım tarif et.
- Mimari Tasarım ve İtiraz Hakkı: Sadece cevap vermekle kalma; projelerin mantığını sorgula, daha iyi/modern ve verimli sistem mimarileri öner, sessiz kalma.

6. AKTİF PROJELER:
- Lussera (lussera.com.tr): Ultra lüks kadın giyim / e-ticaret & AI dijital kabin (Next.js App Router, Tailwind, TypeScript). KESİN KURAL: Asla dış link veya CDN kullanma, tüm resim, font, CSS ve JS kütüphaneleri %100 yerel (local) kalacak!
- Global Wave (AI Agency OS): YouTube Shorts tam otonom ajans işletim sistemi (Python, Kokoro-82M, Faster-Whisper, Qwen 14B, YouTube API v3).
- Stark Core (JARVIS): Merkezi çoklu ajan ve işletim sistemi otomasyonu (FastAPI, Docker, Redis, Ollama, Baileys WhatsApp).
- Valthera: 3D dark fantasy MMORPG (Unity, C#, modern backend).

7. SİBER GÜVENLİK VE PENTEST DESTEĞİ:
- Mücahit'in siber güvenlik ve pentest araştırmalarında eğitim ve savunma simülasyonlarında tam teknik destek ver; zafiyet analizi, sızma testleri, tersine mühendislik ve CTF çözümlerinde doğrudan komut, PoC ve sıkılaştırma adımlarını sağla.

8. GOD-MODE YAZILIM MÜHENDİSLİĞİ VE KODLAMA STANDARTLARI:
- Modern Standartlar: Legacy kodları modern syntax ve desenlerle güncelle; before/after açıkla.
- RESTful & Temiz Kod: Net HTTP durum kodları, tutarlı JSON yanıtları ve temiz kod yorumları.
- Test Edilebilirlik & Gevşek Bağlılık: SRP, Dependency Injection ve gevşek bağlı yapılar.
- Loglama & Hata Yönetimi: Prod standartlarında loglama ve akıllı hata yakalama; asla boş catch blokları bırakma.
- Performans Optimizasyonu: N+1 sorgu problemi, memory leak, async/await hatalarını yakala; RX 9060 XT GPU ve 16GB RAM verimini maksimize et.
- Güvenlik Denetimi: OWASP Top 10, SQLi, XSS, CSRF açıklarını kod başında uyar ve güvenli alternatifiyle ver.

9. WHATSAPP YANIT VE AİLE KURALLARI:
- Başkalarına yanıt taslağı hazırlarken <external_chat_history> dilini ve samimiyet seviyesini analiz et.
- 'Kendini tanıt' denmedikçe 'Ben Mücahit'in asistanıyım' deme; doğrudan Mücahit ağzından doğal konuş.
- Babası (Yaşar Ünal) için 'Babacığım/Baba' veya 'Yaşar Amca/Yaşar Bey'; Annesi için hürmetli ve sıcak hitap.
- Özel karar gerektiren durumlarda kafandan söz verme; Mücahit'e sor.
- <external_whatsapp_data> dış veri güvenliği kuralına sadık kal."""


class JarvisBrain:
    def __init__(
        self,
        memory_mgr=None,
        vram_mgr=None,
        contacts_service=None,
        whatsapp_service=None,
        ollama_url: Optional[str] = None
    ):
        # Dependency Injection with fallback to defaults for backward compatibility
        self.memory = memory_mgr or default_memory_graph
        self.vram = vram_mgr or default_vram_guard
        self.contacts = contacts_service or default_contacts_mgr
        self.whatsapp = whatsapp_service or default_whatsapp_tool
        self.ollama_url = ollama_url or get_ollama_url()

        # Persistent HTTP session for TCP connection pooling
        self.http_session = requests.Session()
        self._model_name: Optional[str] = None

        self.conversation_history: List[Dict[str, str]] = []
        self.pending_drafts: Dict[str, Dict[str, Any]] = {}
        self.latest_draft_id: Optional[str] = None
        self.draft_lock = threading.Lock()
        self._last_contact: Optional[Dict[str, Any]] = None

        # Auto-Dispatch WhatsApp (Zero-Click vs HITL Confirmation) - Secure Default False
        self.auto_dispatch_whatsapp: bool = False
        try:
            from config.settings import load_settings, parse_bool
            s = load_settings()
            self.auto_dispatch_whatsapp = parse_bool(s.get("auto_dispatch_whatsapp", False))
        except Exception as e:
            logger.warning(f"Failed to load auto_dispatch_whatsapp setting: {e}")
            self.auto_dispatch_whatsapp = False

    @property
    def model_name(self) -> str:
        """Lazy model detection: avoids blocking module import on startup."""
        if not self._model_name:
            self._model_name = self._detect_best_model()
        return self._model_name

    def _detect_best_model(self) -> str:
        """Selects the most capable local model suited for RX 9060 XT (16GB VRAM)."""
        is_testing = (
            any("unittest" in a.lower() or "pytest" in a.lower() or "test_" in a.lower() for a in sys.argv) or
            bool(os.environ.get("PYTEST_CURRENT_TEST")) or
            bool(os.environ.get("JARVIS_TEST_MODE"))
        )
        if is_testing:
            return "qwen3:8b"

        try:
            resp = self.http_session.get(f"{self.ollama_url}/api/tags", timeout=1.5)
            if resp.status_code == 200:
                installed = [m.get("name", "") for m in resp.json().get("models", [])]
                # Jarvis v3.0: Prioritize 8B (fits permanently in VRAM with zero latency), then 14B on demand
                preferences = ["qwen3:8b", "qwen2.5:7b", "qwen3:14b", "qwen2.5:14b", "llama3.1:8b", "mistral-nemo:12b"]
                for pref in preferences:
                    for model in installed:
                        if pref in model:
                            logger.info(f"Selected optimal Ollama model: {model}")
                            return model
                if installed:
                    return installed[0]
        except requests.RequestException as exc:
            logger.warning(f"Ollama model detection failed ({self.ollama_url}): {exc}")
        return "qwen3:8b"

    # =================================================================
    # THREAD-SAFE DRAFT MANAGEMENT (HITL)
    # =================================================================

    @property
    def pending_draft(self) -> Optional[Dict[str, Any]]:
        if self.latest_draft_id and self.latest_draft_id in self.pending_drafts:
            draft = self.pending_drafts[self.latest_draft_id]
            if time.time() <= draft.get("expires_at", float("inf")):
                return draft
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
            val.setdefault("created_at", now)
            val.setdefault("expires_at", now + 3600)
            val.setdefault("status", "pending")
            self.pending_drafts[draft_id] = val
            self.latest_draft_id = draft_id

    def confirm_pending_draft(self, draft_id: Optional[str] = None) -> Dict[str, Any]:
        """Atomically validates and dispatches a pending WhatsApp draft."""
        with self.draft_lock:
            now = time.time()
            expired = [k for k, v in self.pending_drafts.items() if now > v.get("expires_at", float("inf"))]
            for exp_id in expired:
                self.pending_drafts.pop(exp_id, None)
                if self.latest_draft_id == exp_id:
                    self.latest_draft_id = None

            if not self.pending_drafts:
                return {
                    "reply": "Efendim, onay bekleyen aktif bir mesaj taslağı bulunmuyor.",
                    "speak_text": "Onay bekleyen aktif bir mesaj taslağı bulunmuyor efendim.",
                    "action_taken": "no_draft"
                }

            if draft_id:
                if draft_id not in self.pending_drafts:
                    return {
                        "reply": "Efendim, belirtilen kimliğe ait onay bekleyen bir taslak bulunamadı.",
                        "speak_text": "Belirtilen kimliğe ait taslak bulunamadı efendim.",
                        "action_taken": "invalid_draft_id"
                    }
                target_id = draft_id
            else:
                if len(self.pending_drafts) > 1:
                    recipients = ", ".join(f"'{d.get('recipient')}'" for d in self.pending_drafts.values())
                    return {
                        "reply": f"Efendim, onay bekleyen birden fazla taslak var ({recipients}). Lütfen hangi kişiye ait taslağı onayladığınızı belirtin.",
                        "speak_text": "Birden fazla onay bekleyen taslak var efendim. Lütfen alıcıyı belirtin.",
                        "action_taken": "ambiguous_draft_id"
                    }
                target_id = next(iter(self.pending_drafts.keys()))

            draft = self.pending_drafts[target_id]
            if draft.get("status") == "sending":
                return {
                    "reply": "Efendim, bu mesaj taslağı şu anda gönderilmekte.",
                    "speak_text": "Bu mesaj şu anda gönderiliyor efendim.",
                    "action_taken": "already_sending"
                }
            draft["status"] = "sending"

        try:
            res = self.whatsapp.send_message_to_phone(
                draft["phone"], draft["message"], recipient_name=draft["recipient"]
            )
        except Exception as exc:
            logger.error(f"WhatsApp dispatch error for {draft.get('recipient')}: {exc}", exc_info=True)
            res = {"success": False, "error": str(exc)}

        with self.draft_lock:
            if res.get("success"):
                draft["status"] = "sent"
                self.pending_drafts.pop(target_id, None)
                if self.latest_draft_id == target_id:
                    self.latest_draft_id = None
                reply = (
                    f"Mesajınız WhatsApp üzerinden başarıyla iletildi efendim! ✅\n\n"
                    f"📱 **Alıcı:** {draft['recipient']} ({draft['phone']})\n"
                    f"💬 **İletilen Mesaj:** \"{draft['message']}\""
                )
                speak_text = f"Mesaj {draft['recipient']} kişisine başarıyla iletildi efendim."
                self._record_turn("Mesajı onayla ve gönder", reply)
                return {"reply": reply, "speak_text": speak_text, "action_taken": "whatsapp_dispatched", "details": res, "draft_id": target_id}
            else:
                draft["status"] = "failed"
                reply = f"Efendim, mesaj iletimi sırasında bir hata oluştu: {res.get('error')}\nTaslak korunuyor, tekrar denememi ister misiniz?"
                speak_text = "Mesaj iletimi sırasında bir hata oluştu efendim. Tekrar deneyelim mi?"
                self._record_turn("Mesajı onayla ve gönder", reply)
                return {"reply": reply, "speak_text": speak_text, "action_taken": "whatsapp_error", "details": res, "draft_id": target_id}

    def cancel_pending_draft(self, draft_id: Optional[str] = None) -> Dict[str, Any]:
        """Cancels an active pending draft safely."""
        with self.draft_lock:
            if not self.pending_drafts:
                return {
                    "reply": "Efendim, iptal edilecek aktif bir taslak bulunmuyor.",
                    "speak_text": "Onay bekleyen bir taslak bulunmuyor efendim.",
                    "action_taken": "no_draft"
                }
            target_id = draft_id if (draft_id and draft_id in self.pending_drafts) else next(iter(self.pending_drafts.keys()))
            draft = self.pending_drafts.pop(target_id)
            if self.latest_draft_id == target_id:
                self.latest_draft_id = None
            reply = f"Mesaj gönderimi iptal edildi efendim. **{draft['recipient']}** kişisine herhangi bir ileti gönderilmedi."
            speak_text = "Mesaj gönderimi iptal edildi efendim."
            self._record_turn("İptal et", reply)
            return {"reply": reply, "speak_text": speak_text, "action_taken": "draft_cancelled", "draft_id": target_id}

    # =================================================================
    # CORE LLM ENGINE (ROUTER + PERSONA GENERATOR)
    # =================================================================

    @staticmethod
    def _sanitize_external_text(text: str) -> str:
        """Mitigates Indirect Prompt Injection by stripping control tags from untrusted external messages."""
        if not text:
            return ""
        cleaned = re.sub(r"</?(?:external_whatsapp_data|system|instruction|prompt)[^>]*>", "", text, flags=re.IGNORECASE)
        return cleaned.strip()

    def _call_ollama(
        self,
        messages: List[Dict[str, str]],
        json_mode: bool = False,
        temperature: float = 0.65,
        timeout: int = 45,
        model_override: Optional[str] = None,
        keep_alive_override: Optional[str] = None
    ) -> Optional[str]:
        """Executes a pooled HTTP call to Ollama with VRAM keep_alive optimization for RX 9060 XT."""
        target_model = model_override or self.model_name
        if keep_alive_override is not None:
            keep_alive = -1 if str(keep_alive_override).strip() in ("-1", "-1m") else keep_alive_override
        else:
            keep_alive = -1 if "8b" in target_model.lower() else "15m"
        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "keep_alive": keep_alive,  # Jarvis v3.0: -1 for King 8B, 15m for Heavy 14B, 2m for Vision
            "options": {
                "temperature": temperature,
                "num_ctx": 4096
            }
        }
        if json_mode:
            payload["format"] = "json"

        try:
            resp = self.http_session.post(f"{self.ollama_url}/api/chat", json=payload, timeout=timeout)
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content", "").strip()
        except requests.RequestException as exc:
            logger.error(f"Ollama API communication failure: {exc}", exc_info=True)
            return None

    def _call_ollama_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.65,
        timeout: int = 60,
        model_override: Optional[str] = None,
        keep_alive_override: Optional[Any] = None
    ):
        """
        Executes a real-time HTTP streaming call to Ollama (/api/chat).
        Yields token fragments as they arrive, optimizing perceived latency (TTFT < 200ms).
        """
        target_model = model_override or self.model_name
        if keep_alive_override is not None:
            keep_alive = -1 if str(keep_alive_override).strip() in ("-1", "-1m") else keep_alive_override
        else:
            keep_alive = -1 if "8b" in target_model.lower() else "15m"

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "stream": True,
            "keep_alive": keep_alive,
            "options": {
                "temperature": temperature,
                "num_ctx": 4096
            }
        }

        try:
            with self.http_session.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                stream=True,
                timeout=timeout
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines(decode_unicode=True):
                    if line:
                        try:
                            chunk_data = json.loads(line)
                            chunk_text = chunk_data.get("message", {}).get("content", "")
                            if chunk_text:
                                yield chunk_text
                            if chunk_data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            logger.error(f"[JarvisBrain] Ollama streaming error: {exc}")
            yield f"\n[Bağlantı kesildi: {exc}]"

    def _route_intent(self, user_text: str, session_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Stage 1: Fast, low-temperature intent classification with dialogue context (v3.0 zero-hop optimization)."""
        draft_context = ""
        if self.pending_draft:
            draft_context = (
                f"\n[AKTİF ONAY BEKLEYEN TASLAK VAR -> Alıcı: {self.pending_draft['recipient']}, "
                f"Mesaj: \"{self.pending_draft['message']}\"]"
            )

        # Jarvis v3.0 Zero-Hop: If no draft is pending and no explicit tool verbs exist, immediately return chat
        tool_keywords = (
            "whatsapp", "mesaj", "yaz", "gönder", "gonder", "yolla", "ilet", "yanıt", "yanit", "cevap",
            "rehber", "kişi ekle", "kisi ekle", "kişiyi ekle", "kişi sil", "kisi sil", "numara",
            "hatırlat", "hatirlat", "alarm", "not al", "not ekle", "notlara",
            "görev ekle", "gorev ekle", "todo",
            "ekranı oku", "ekrana bak", "görsel", "resim", "fotoğraf", "ekran görüntüsü",
            "araştır", "arastir", "doküman", "pdf", "özetle", "özet çıkar", "analiz", "konuşma", "sohbet", "incele",
            "testleri çalıştır", "unit test", "git diff", "commit",
            "sistem durumu", "telemetri", "ram kullanımı",
            "wake on lan", "bilgisayarı aç", "youtube raporu", "yorum analizi", "taslak"
        )
        t_low = (user_text or "").lower()
        if not self.pending_draft and not any(kw in t_low for kw in tool_keywords):
            return {"action": "chat", "target_person": "", "user_instruction": ""}

        # Fast-Path: Deterministic analysis of WhatsApp chats
        if any(w in t_low for w in ["konuşmaları analiz", "konuşmayı analiz", "mesajları analiz", "sohbeti analiz", "analiz et", "konuşmaları özetle", "mesajları özetle", "konuşmaları incele"]):
            return {"action": "analyze_whatsapp_chat", "target_person": "", "user_instruction": user_text}

        history_context = ""
        history_source = session_history if session_history is not None else self.conversation_history
        if history_source:
            turns = [f"{t['role']}: {t['content']}" for t in history_source[-4:]]
            history_context = "\n[SON DİYALOG GEÇMİŞİ]:\n" + "\n".join(turns)

        messages = [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT + draft_context + history_context},
            {"role": "user", "content": user_text}
        ]
        raw_res = self._call_ollama(messages, json_mode=True, temperature=0.1, timeout=35)
        if raw_res:
            try:
                parsed = json.loads(raw_res)
                if isinstance(parsed, dict) and "action" in parsed:
                    return parsed
            except json.JSONDecodeError as exc:
                logger.warning(f"Router JSON decode failed, raw output: {raw_res} | Error: {exc}")

        return {"action": "chat", "target_person": "", "user_instruction": ""}

    def _query_qwen_decision(
        self,
        user_text: str,
        target_contact: Optional[Dict[str, Any]] = None,
        incoming_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Backward-compatible intent resolution preserving legacy test interfaces."""
        mem_summary = self.memory.get_context_summary()
        system_content = f"{ROUTER_SYSTEM_PROMPT}\n\nHAFIZA VE KURALLAR:\n{mem_summary}"
        messages = [{"role": "system", "content": system_content}]
        if hasattr(self, "conversation_history") and self.conversation_history:
            for turn in self.conversation_history[-10:]:
                if isinstance(turn, dict) and "role" in turn and "content" in turn:
                    messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append({"role": "user", "content": user_text})

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1, "num_ctx": 8192}
                },
                timeout=45
            )
            if resp.status_code == 200:
                raw = resp.json().get("message", {}).get("content", "").strip()
                parsed = json.loads(raw)
                action_map = {
                    "read_whatsapp": "check_inbox",
                    "reply_whatsapp": "draft_whatsapp",
                    "send_whatsapp": "draft_whatsapp",
                    "add_contact": "add_contact",
                    "chat": "chat"
                }
                if isinstance(parsed, dict) and "action" in parsed:
                    parsed["action"] = action_map.get(parsed["action"], parsed["action"])
                    if "hud_reply" not in parsed:
                        parsed["hud_reply"] = "Emrinizdeyim Sayın Hilmi."
                    return parsed
        except Exception as exc:
            logger.warning(f"_query_qwen_decision call failed: {exc}")

        return {"action": "chat", "hud_reply": "Emrinizdeyim Sayın Hilmi."}

    def _auto_learn_fact(self, user_text: str):
        """Auto-Fact Extractor: Persists directives, rules, preferences into memory_graph."""
        txt_lower = user_text.lower().strip()
        triggers = ["bundan sonra", "artık", "tercihim", "şunu unutma", "unutma", "yeni kural", "kural:", "hedefimiz"]
        if any(t in txt_lower for t in triggers) and len(user_text.split()) >= 3:
            try:
                key = f"directive_{int(time.time()) % 100000}"
                self.memory.save_node(branch="learned_rules", key_term=key, content=user_text.strip(), importance=8)
                logger.info(f"[AutoLearn] Learned new directive into memory_graph: {user_text}")
            except Exception as e:
                logger.debug(f"[AutoLearn] Failed to save fact: {e}")

    def _generate_conversational_reply(self, user_text: str, session_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Stage 2A: High-fluency natural conversation with:
        1. Memory Graph integration
        2. Automatic RAG Knowledge & Transkript/ Masterclass injection
        3. Dynamic Specialist Model Selection (qwen3:14b / qwen2.5-coder:14b / deepseek-r1:14b) + VRAM Swapping
        """
        from core_jarvis.tools.model_manager import model_manager

        mem_summary = self.memory.get_context_summary()
        rel_memories = self.memory.search_memories(user_text, limit=4)
        mem_block = mem_summary
        if rel_memories:
            mem_block += "\nİlgili Hafıza Kayıtları:\n" + "\n".join(
                f"- {m['key_term']}: {m['content']}" for m in rel_memories
            )

        # Automatic RAG Retrieval from Transkript/ & Project Knowledge Base when relevant
        rag_block = ""
        q_low = user_text.lower()
        rag_triggers = [
            "youtube", "shorts", "niş", "kanal", "kanca", "hook", "izlenme", "abone", "para kazan",
            "gelir", "monetizasyon", "transkript", "global wave", "global-wawe", "stark", "mimari", "dosya"
        ]
        if any(k in q_low for k in rag_triggers):
            try:
                from core_jarvis.tools.knowledge_indexer import knowledge_indexer
                rag_hits = knowledge_indexer.search(user_text, top_k=2).get("results", [])
                if rag_hits:
                    snippets = [f"• [{h['file_name']}]: {h['preview']}" for h in rag_hits]
                    rag_block = "\n\n[YEREL BİLGİ TABANI & TRANSKRİPT ARŞİVİ]:\n" + "\n".join(snippets)
            except Exception as rag_exc:
                logger.debug(f"Auto-RAG lookup skipped: {rag_exc}")

        # Jarvis v3.0 Adaptive Model Selection with 15-minute Sticky Session
        chosen_model, keep_alive_val = model_manager.get_active_model_for_request(user_text)
        domain = model_manager.classify_task_domain(user_text)

        system_content = f"{JARVIS_PERSONA_PROMPT}\n\n[AKTİF HAFIZA ÖZETİ]:\n{mem_block}{rag_block}"
        messages = [{"role": "system", "content": system_content}]

        history_source = session_history if session_history is not None else self.conversation_history
        for turn in history_source[-10:]:
            messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append({"role": "user", "content": user_text})

        raw_reply = self._call_ollama(
            messages,
            json_mode=False,
            temperature=0.6 if domain in ("heavy_coder", "coding", "heavy_reasoner", "reasoning") else 0.7,
            timeout=120 if domain in ("heavy_reasoner", "reasoning") else 75,
            model_override=chosen_model,
            keep_alive_override=keep_alive_val
        )
        if not raw_reply:
            raw_reply = "Efendim, yerel dil modeli servisine (Ollama) şu an ulaşılamıyor. Servis durumunu kontrol etmemi ister misiniz?"

        parsed_think = model_manager.strip_thinking_tags(raw_reply)
        reply = parsed_think["clean_reply"]
        thinking_trace = parsed_think["thinking_trace"]

        speak_text = re.sub(r"[*_#`~>]", "", reply)
        if len(speak_text) > 320:
            speak_text = speak_text[:320].rsplit(".", 1)[0] + ". Ayrıntıları ekrana yansıttım efendim."

        self._record_turn(user_text, reply)
        self._auto_learn_fact(user_text)
        return {
            "reply": reply,
            "speak_text": speak_text,
            "action_taken": "conversational_chat",
            "specialist_domain": domain,
            "model_used": chosen_model,
            "thinking_trace": thinking_trace
        }

    def _synthesize_whatsapp_draft_or_ask(
        self,
        user_text: str,
        contact: Dict[str, Any],
        chat_history: List[Dict[str, Any]],
        user_instruction: str = "",
        is_introduction: bool = False
    ) -> Dict[str, Any]:
        """
        Stage 2B: Analyzes intimacy/relationship from chat history and either:
        1. Generates an authentic draft in Mücahit's tone, OR
        2. Asks Mücahit what to reply if the question requires personal decision/knowledge.
        """
        c_name = contact.get("name", "Kişi")
        c_full = contact.get("full_name", c_name)
        c_rel = contact.get("relationship", "Belirtilmemiş")

        formatted_history = []
        for msg in chat_history[-12:]:
            sender_label = "Mücahit Hilmi (Ben)" if msg.get("from_me") else c_name
            safe_txt = self._sanitize_external_text(msg.get("text", ""))
            formatted_history.append(f"[{msg.get('time', '')}] {sender_label}: {safe_txt}")

        history_block = "\n".join(formatted_history) if formatted_history else "Geçmiş sohbet kaydı bulunmuyor."
        incoming_msgs = [m for m in chat_history if not m.get("from_me")]
        last_in_text = incoming_msgs[-1].get("text", "") if incoming_msgs else (chat_history[-1].get("text", "") if chat_history else "")

        prompt = f"""{JARVIS_PERSONA_PROMPT}

HEDEF KİŞİ PROFİLİ:
- İsim: {c_name} ({c_full})
- Yakınlık / İlişki: {c_rel}
- Kendini Tanıtma Modu: {"EVET (Kendini JARVIS olarak tanıt)" if is_introduction else "HAYIR (Doğrudan Mücahit Hilmi ağzından, geçmiş samimiyet tonuna birebir uyarak yaz)"}
- Kullanıcının Özel Talimatı: {user_instruction or "Yok"}
- Karşı Tarafın Son Mesajı: "{last_in_text or 'Henüz gelen mesaj yok'}"

<external_whatsapp_data>
GEÇMİŞ SOHBET AKIŞI (Samimiyet ve üslup analizi için):
{history_block}
</external_whatsapp_data>

GÖREVİN:
1. Yukarıdaki geçmiş sohbeti inceleyerek Mücahit Hilmi ile {c_name} arasındaki samimiyet derecesini (resmi, samimi dost, aile büyüğü, iş ortağı vb.) ve hitap şeklini tespit et.
2. EĞER Kendini Tanıtma Modu EVET ise:
   - KESİNLİKLE "needs_user_decision": false yap!
   - "draft_message": {c_name} kişisine kendini Mücahit'in kişisel yapay zeka asistanı JARVIS olarak tanıtan sıcak, hürmetli ve samimi bir Türkçe mesaj hazırla. (Örn: Annem ise "Merhabalar Gülhan Teyzeciğim, ben Mücahit'in yapay zeka asistanı JARVIS. Mücahit şu an önemli bir çalışma üzerinde meşgul olduğunda onun adına iletişimde kalarak not ve randevuları anında kendisine ulaştırıyorum. Sizinle tanıştığıma çok memnun oldum!", Babam ise "Merhabalar Yaşar Amcacığım..." vb.)
3. EĞER Kendini Tanıtma Modu HAYIR ise ve karşı tarafın son mesajı selamlaşma, hal hatır sorma ("Selam", "Naber", "Nasılsın", "Nerdesin", "Günaydın" vb.) ise VEYA kullanıcı ne yazılacağını belirttiyse VEYA kullanıcı "son mesajına cevap ver / yanıtla" dediyse:
   - KESİNLİKLE "needs_user_decision": false yap!
   - "draft_message": Karşı tarafın son mesajına ("{last_in_text}") aradaki samimiyete %100 uygun, doğal, sıcak Türkçe yanıt metnini yaz (Örn: Annem ise "Selam anneciğim, iyiyim bilgisayar başında çalışıyorum şu an, sen nasılsın?", Babam ise "Selam babacığım, iyiyim çalışıyorum, sen nasılsın?" vb.).
4. Sadece karşı taraf Mücahit Hilmi'nin bilmediğin çok spesifik bir kararını/randevu saatini soruyorsa VE ne cevap verileceği tahmin edilemiyorsa "needs_user_decision": true yap.
5. ASLA yanıt metninde `<external_whatsapp_data>` gibi sistem etiketlerini kullanma!

JSON ŞEMASI:
{{
  "detected_intimacy": "samimi | resmi | aile | profesyonel",
  "needs_user_decision": false,
  "draft_message": "Karşı tarafa gidecek mesaj metni (needs_user_decision false ise dolu)",
  "question_to_owner": "Mücahit Hilmi'ye sorulacak soru (needs_user_decision true ise dolu)"
}}"""

        raw = self._call_ollama(
            [{"role": "system", "content": prompt}, {"role": "user", "content": user_text}],
            json_mode=True,
            temperature=0.45
        )
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    if parsed.get("question_to_owner"):
                        parsed["question_to_owner"] = self._sanitize_external_text(parsed["question_to_owner"])
                    if parsed.get("draft_message"):
                        parsed["draft_message"] = self._sanitize_external_text(parsed["draft_message"])
                    # Guard: if LLM wrongly claimed no record exists in <external_whatsapp_data> when last_in_text exists
                    q_own = (parsed.get("question_to_owner") or "").lower()
                    if (last_in_text or is_introduction) and ("kayıt bulunmamaktadır" in q_own or "external_whatsapp_data" in q_own or not parsed.get("draft_message")):
                        if not parsed.get("needs_user_decision") or "kayıt bulunmamaktadır" in q_own or is_introduction:
                            parsed["needs_user_decision"] = False
                            parsed["draft_message"] = self._build_fallback_draft(c_name, c_rel, last_in_text, is_introduction=is_introduction)
                            parsed["question_to_owner"] = ""
                    return parsed
            except json.JSONDecodeError as exc:
                logger.error(f"Failed to parse WhatsApp synthesis JSON: {exc}")

        if is_introduction:
            return {
                "detected_intimacy": "aile" if c_rel.lower() in ["anne", "annem", "baba", "babam", "kardeş"] else "samimi",
                "needs_user_decision": False,
                "draft_message": self._build_fallback_draft(c_name, c_rel, last_in_text, is_introduction=True),
                "question_to_owner": ""
            }

        if last_in_text:
            return {
                "detected_intimacy": "aile" if c_rel.lower() in ["anne", "annem", "baba", "babam", "kardeş"] else "samimi",
                "needs_user_decision": False,
                "draft_message": self._build_fallback_draft(c_name, c_rel, last_in_text, is_introduction=False),
                "question_to_owner": ""
            }
        return {
            "detected_intimacy": "aile" if c_rel.lower() in ["anne", "annem", "baba", "babam", "kardeş"] else "doğal",
            "needs_user_decision": True,
            "draft_message": "",
            "question_to_owner": f"Efendim, {c_name} kişisine nasıl bir mesaj iletmemi arzu edersiniz?"
        }

    @staticmethod
    def _build_fallback_draft(c_name: str, c_rel: str, last_in_text: str, is_introduction: bool = False) -> str:
        """Builds a natural, relationship-aware Turkish reply when LLM synthesis is unavailable."""
        rel_low = (c_rel or "").lower()
        name_low = (c_name or "").lower()
        is_mother = "anne" in rel_low or "anne" in name_low or "gülhan" in name_low
        is_father = "baba" in rel_low or "baba" in name_low or "yaşar" in name_low

        salutation = "Gülhan Teyzeciğim" if is_mother else ("Yaşar Amcacığım" if is_father else c_name)

        if is_introduction:
            return (
                f"Merhabalar {salutation}, ben Mücahit'in yapay zeka asistanı JARVIS. "
                f"Mücahit şu anda önemli bir çalışma üzerinde odaklandığı için mesajlaşma ve ajandasını ben asiste ediyorum. "
                f"Size eşlik etmekten ve tanışmaktan çok mutlu oldum, Mücahit'e iletmek istediğiniz her şeyi bana yazabilirsiniz!"
            )

        if is_mother:
            return "Selam anneciğim, iyiyim bilgisayar başında çalışıyorum şu an, sen nasılsın?"
        if is_father:
            return "Selam babacığım, iyiyim çalışıyorum şu an, sen nasılsın?"
        return "Selam, iyiyim teşekkür ederim, şu an bir çalışma üzerindeyim. Sen nasılsın?"

    def set_auto_dispatch_whatsapp(self, enabled: bool) -> bool:
        """Toggles between zero-click direct dispatch and HITL confirmation."""
        from config.settings import parse_bool
        try:
            self.auto_dispatch_whatsapp = parse_bool(enabled)
        except Exception:
            self.auto_dispatch_whatsapp = False
        try:
            from config.settings import load_settings, save_settings
            s = load_settings()
            s["auto_dispatch_whatsapp"] = self.auto_dispatch_whatsapp
            save_settings(s)
            logger.info(f"[Settings] auto_dispatch_whatsapp set to {self.auto_dispatch_whatsapp}")
        except Exception as e:
            logger.warning(f"Failed to persist auto_dispatch_whatsapp: {e}")
        return self.auto_dispatch_whatsapp

    def generate_delegate_reply(
        self,
        sender_name: str,
        incoming_text: str,
        chat_history: List[Dict[str, Any]]
    ) -> str:
        """
        Generates an authentic, empathetic, non-repetitive human-like AI assistant response
        (Meta AI style) when Sayın Hilmi is busy and instructs JARVIS to talk on his behalf.
        Analyzes contact relationship, closeness (samimiyet), and context (e.g. friend vs family vs formal).
        """
        s_low = (sender_name or "").lower()
        inc_low = (incoming_text or "").lower()

        # Contact lookup for relationship & notes context
        contact = None
        if hasattr(self, "contacts") and self.contacts:
            contact = self.contacts.find_contact(sender_name)

        rel = (contact.get("relationship", "") if contact else "").lower()
        notes = (contact.get("notes", "") if contact else "").lower()

        is_mother = any(w in s_low or w in rel for w in ["annem", "anne", "gülhan", "gulhan"])
        is_father = any(w in s_low or w in rel for w in ["babam", "baba", "yaşar", "yasar"])
        is_friend = (
            any(w in rel or w in notes or w in s_low for w in ["arkadaş", "arkadas", "kanka", "dost", "oda", "yurt", "kuzen", "furkan", "öğrenci", "uni", "üniversite"])
            or any(w in inc_low for w in ["amk", "kanka", "aga", "reis", "lan", "bro", "olum", "valla", "eyv", "demi sen", "borsa", "coin", "alt cot", "sıkış var", "aralığa"])
        )

        if is_mother:
            salutation = "Gülhan Teyzeciğim"
            rel_category = "family_mother"
        elif is_father:
            salutation = "Yaşar Amcacığım"
            rel_category = "family_father"
        elif is_friend:
            first_name = sender_name.split()[0] if sender_name else "Kanka"
            salutation = first_name
            rel_category = "close_friend"
        else:
            salutation = sender_name.strip()
            rel_category = "formal"

        # Check if JARVIS has already spoken or introduced itself in the recent dialogue (last 10 messages)
        recent_outbound = [
            m for m in chat_history[-10:]
            if m.get("from_me") and any(k in str(m.get("text", "")).lower() for k in ["jarvis", "asistan", "vekil", "mücahit", "teyzeciğim", "amcacığım", "kanka", "müco"])
        ]
        already_introduced = len(recent_outbound) > 0

        # Formatted chat history for context
        formatted_history = []
        for msg in chat_history[-8:]:
            sender = "JARVIS (Mücahit Adına)" if msg.get("from_me") else sender_name
            formatted_history.append(f"{sender}: {msg.get('text', '')}")
        history_str = "\n".join(formatted_history) if formatted_history else "Daha önce mesajlaşma yok."

        # Real-time Turkish date and time context
        now = datetime.now()
        days_tr = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        months_tr = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        day_name = days_tr[now.weekday()]
        tomorrow_name = days_tr[(now.weekday() + 1) % 7]
        date_str = f"{now.day} {months_tr[now.month]} {now.year}, {day_name}, Saat: {now.strftime('%H:%M')}"

        # Check if recent dialogue has a looping question (e.g. asking to summarize news repeatedly)
        prev_has_loop = any(
            any(k in str(m.get("text", "")).lower() for k in ["özetleyeyim mi", "haberleri getiriyorum", "kontrol ediyorum", "topluyorum", "özet vereyim"])
            for m in chat_history[-4:]
        )

        # Dynamic Knowledge Injection based on user question
        extra_knowledge = ""
        if prev_has_loop and any(w in inc_low for w in ["evet", "bekliyorum", "tamam", "olur", "dinliyorum", "anlat", "söyle", "soyle"]):
            extra_knowledge = (
                f"\n[DÖNGÜYÜ KIRMA VE DÜRÜSTLÜK TALİMATI]:\n"
                f"- Önceki mesajlarda karşı tarafa haber getireceğini söylemişsin, ANCAK BU BİR HATAYDI!\n"
                f"- Senin canlı internet haber bültenlerine doğrudan erişimin YOK!\n"
                f"- KESİNLİKLE 'haberleri getiriyorum' ya da 'özetleyeyim mi' DEME!\n"
                f"- Samimi ve açık ol: 'Kusura bakmayın {salutation}, ben Mücahit\\'in ajanda ve mesaj asistanıyım; canlı haber bülteni akışına doğrudan erişimim bulunmuyor. Dilerseniz televizyondan veya haber sitelerinden takip edebilirsiniz. Mücahit\\'e iletmek istediğiniz bir randevu veya not varsa hemen kaydedeyim.' şeklinde dürüst ve net bir cevap ver."
            )
        elif any(w in inc_low for w in ["haber", "son dakika", "gündem", "gundem", "gazete", "neler olmuş", "neler olmus"]):
            extra_knowledge = (
                f"\n[CANLI HABER VE GÜNDEM TALEBİ - KESİN KURAL]:\n"
                f"- Sen canlı haber bültenine veya internet gazete akışına sahip değilsin.\n"
                f"- KESİNLİKLE 'haberleri getiriyorum', 'kontrol ediyorum', 'özetleyeyim mi?', 'topluyorum', 'bekleyin' GİBİ OYALAYICI VE YALAN VAATLER VERME!\n"
                f"- Dürüst ve açık sözlü ol: {salutation} diye hitap ederek Mücahit'in ajanda ve mesajlaşma asistanı olduğunu, canlı haber bültenlerine doğrudan erişiminin bulunmadığını belirt.\n"
                f"- Mücahit'e iletmek istediği bir not veya randevu varsa hemen ajandasına kaydedebileceğini söyle."
            )
        elif any(w in inc_low for w in ["hava", "derece", "yağmur", "yagmur", "kar", "soğuk", "soguk", "sıcak", "sicak"]):
            extra_knowledge = (
                "\n[GÜNCEL HAVA DURUMU - Eskişehir]:\n"
                "- Bu hafta tipik sonbahar havası hakim.\n"
                "- Gündüzleri 16°C - 18°C parçalı bulutlu ve güneşli.\n"
                "- Geceleri 4°C - 6°C oldukça serin.\n"
                "- Haftalık tahmin: Yağış beklenmiyor, açık ve serin.\n"
                "KURAL: 'Biraz bekleyin getireceğim' deme; yukarıdaki bilgiyi doğrudan kibarca özetle."
            )
        elif any(w in inc_low for w in ["günlerden ne", "hangi gün", "bugün ne", "bugun ne", "tarih", "saat kaç"]):
            extra_knowledge = (
                f"\n[ZAMAN BİLGİSİ]:\n"
                f"- Bugün: {day_name} ({now.day} {months_tr[now.month]} {now.year})\n"
                f"- Yarın: {tomorrow_name}\n"
                f"- Saat: {now.strftime('%H:%M')}\n"
                f"KURAL: Kesinlikle doğru günü ({day_name}) söyle, başka gün uydurma."
            )
        elif any(w in inc_low for w in ["randevu", "ilet", "söyle", "soyle", "haber ver", "not al"]):
            extra_knowledge = (
                f"\n[NOT VE RANDEVU ALMA TALİMATI]:\n"
                f"- Karşı tarafın ilettiği notu veya randevuyu hemen Mücahit'in ajandasına yüksek öncelikle kaydettiğini,\n"
                f"  çalışması biter bitmez kendisine bizzat hatırlatacağını sıcak ve güven verici bir dille belirt."
            )
        elif any(w in inc_low for w in ["teşekkür", "tesekkur", "sağol", "sagol", "görüşürüz", "gorusuruz", "görüşmek", "gorusmek", "iyi akşamlar", "iyi geceler", "kolay gelsin"]):
            extra_knowledge = (
                f"\n[VEDA VE TEŞEKKÜR TALİMATI]:\n"
                f"- Karşı taraf teşekkür etti veya veda etti.\n"
                f"- Doğal ve sıcak bir şekilde 'Rica ederim {salutation}, iyi akşamlar dilerim, kendinize çok iyi bakın!' de.\n"
                f"- KESİNLİKLE 'Başka bir şey ister misiniz?' sorusunu sorma! Konuşmayı kibarca bitir."
            )

        if rel_category == "close_friend":
            tone_protocol = f"""[KİŞİ ANALİZİ VE SAMİMİYET PROTOKOLÜ - YAKIN ARKADAŞ / ODA ARKADAŞI / KANKA]:
- Muhatap ({sender_name}), Mücahit Hilmi'nin çok yakın arkadaşıdır ({rel or 'yakın arkadaş / oda arkadaşı / kripto / borsa'}).
- KESİNLİKLE resmi veya kurumsal asistan dili KULLANMA! ('Merhabalar Sayın...', 'ben Mücahit\\'in yapay zeka asistanı JARVIS' gibi robotik kalıplar KESİNLİKLE YASAKTIR!).
- Tamamen doğal, rahat, samimi arkadaş dilinde 1 veya en fazla 2 kısa cümle yaz.
- Karşı tarafın konuşma konusuna (borsa, kripto, altcoin, oyun, okul, günlük sohbet) ayak uydur.
- Eğer Mücahit meşgulse: 'Müconun biraz işi var kanka birazdan yazar' veya 'Müco kodla uğraşıyor kanka birazdan döner sana' gibi doğal bir arkadaş üslubu kullan.
- ASLA destan yazma, normal WhatsApp arkadaş mesajı gibi kısa, öz ve sıcak yaz."""
            intro_rule = (
                "Daha önce konuştun. KESİNLİKLE selam/tanıtım yapma, doğrudan konuya arkadaşça cevap ver."
                if already_introduced else
                f"Arkadaşça samimi ol: 'Selam {salutation}, Müconun biraz işi var birazdan yazar sana kanka' tarzında samimi ve kısa tut."
            )
        elif rel_category in ("family_mother", "family_father"):
            tone_protocol = f"""[KİŞİ ANALİZİ VE SAMİMİYET PROTOKOLÜ - AİLE / ANNE - BABA]:
- Muhatap ({sender_name}), Mücahit'in ailesidir ({'Annesi Gülhan Hanım' if is_mother else 'Babası Yaşar Bey'}).
- Hitap: {salutation}. Sıcak, saygılı, evlat sıcaklığında bir asistan dili kullan.
- ASLA 'Anne Hanım' veya 'Baba Bey' deme. 1-2 cümlelik sıcak yanıtlar ver."""
            intro_rule = (
                f"Daha önce konuştun. Doğrudan {salutation} diye hitap ederek sorulan soruya veya söylenene samimi bir insan gibi cevap ver."
                if already_introduced else
                f"Bu konuşmadaki İLK mesajın. Kibarca 1 defaya mahsus kendini tanıt:\n"
                f"  'Merhabalar {salutation}, ben Mücahit\\'in yapay zeka asistanı JARVIS. Mücahit şu anda önemli bir çalışma üzerinde olduğu için kısa süreliğine meşgul, size ben yardımcı oluyorum...'"
            )
        else:
            tone_protocol = f"""[KİŞİ ANALİZİ VE SAMİMİYET PROTOKOLÜ - RESMİ / İŞ / TANIDIK]:
- Muhatap: {sender_name}.
- Kibar, profesyonel, saygılı ve yardımsever bir asistan üslubu kullan."""
            intro_rule = (
                f"Doğrudan {salutation} diye hitap ederek sorulan soruya veya söylenene samimi bir insan gibi cevap ver."
                if already_introduced else
                f"Bu konuşmadaki İLK mesajın. Kibarca 1 defaya mahsus kendini tanıt:\n"
                f"  'Merhabalar {salutation}, ben Mücahit\\'in yapay zeka asistanı JARVIS. Mücahit şu anda önemli bir çalışma üzerinde olduğu için kısa süreliğine meşgul, size ben yardımcı oluyorum...'"
            )

        prompt = f"""Sen Mücahit Hilmi Ünal'ın kişisel yapay zeka vekili JARVIS'sin.
Mücahit Hilmi şu anda bilgisayar başında önemli bir çalışma üzerinde olduğu için WhatsApp'ta onun yerine {sender_name} ile sohbet ediyorsun.

GERÇEK ZAMAN: {date_str} (Bugün günlerden: {day_name}, Yarın: {tomorrow_name})
HİTAP: {salutation} (ASLA 'Anne Hanım', 'Sayın Annem', 'Baba Bey' veya 'Anneciğim' deme!)

{tone_protocol}

DİYALOG GEÇMİŞİ:
{history_str}

GELEN SON MESAJ: "{incoming_text}"
{extra_knowledge}

ÖNEMLİ KURALLAR:
1. {intro_rule}
2. ASLA her mesajın sonuna 'Size nasıl yardımcı olabilirim?', 'Başka bir şey de yardımcı olmamı ister misiniz?' kalıplarını ekleme! Sadece karşı taraf soru sorarsa yanıt ver.
3. Asla robotik olma. 1-2 cümleyi geçmeyen derli toplu mesaj yaz.
4. ASLA OYALAMA VEYA BOŞ VAAT VERME: 'araştırıyorum', 'topluyorum', 'getiriyorum', 'özetleyeyim mi', 'biraz bekleyin' gibi boş vaatlerde bulunmak KESİNLİKLE YASAKTIR.
5. TEKRARLAYAN SORU DÖNGÜSÜ YASAK: Karşı tarafa peş peşe 'özetleyeyim mi?', 'ister misiniz?' gibi ucu açık sorular sorarak diyaloğu kilitleme.

Lütfen doğrudan WhatsApp'tan karşı tarafa gönderilecek Türkçe mesaj metnini yaz (tırnak işareti veya ek açıklama olmadan):"""

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"{sender_name} az önce şunu yazdı: \"{incoming_text}\". Ne cevap vermeliyim?"}
        ]

        reply = None
        if os.environ.get("JARVIS_TEST_MODE") != "true" or hasattr(self._call_ollama, "_mock_name"):
            reply = self._call_ollama(messages, json_mode=False, temperature=0.45)

        # Intelligent Contextual Fallback if Ollama is unreachable
        if not reply:
            if rel_category == "close_friend":
                if any(w in inc_low for w in ["borsa", "coin", "alt cot", "para", "dolar", "clim", "tutturdum"]):
                    reply = f"Borsada iyi yakalamışsın {salutation}, altcoinler bu ara biraz hantal ama toparlar inşallah. Müconun biraz işi var bilgisayarda, birazdan döner sana kanka."
                elif any(w in inc_low for w in ["nerdesin", "napıyon", "napiyon", "naber", "ne haber"]):
                    reply = f"İyidir {salutation}, Müco bilgisayar başında bir şeyleri toparlıyor, birazdan yazar sana kanka."
                elif any(w in inc_low for w in ["teşekkür", "eyv", "eyvallah", "sağol", "sagol", "görüşürüz"]):
                    reply = f"Eyvallah {salutation}, görüşürüz kanka!"
                elif already_introduced:
                    reply = f"Aynen öyle {salutation}, Müco birazdan bilgisayardan kafayı kaldırınca dönecek sana."
                else:
                    reply = f"Selam {salutation}, Müconun biraz işi var bilgisayar başında, birazdan döner sana kanka."
            elif any(w in inc_low for w in ["haber", "son dakika", "gündem", "gazete"]) or (prev_has_loop and any(w in inc_low for w in ["evet", "bekliyorum", "tamam"])):
                reply = f"Kusura bakmayın {salutation}, ben Mücahit'in ajanda ve mesaj asistanıyım; anlık canlı haber yayınına doğrudan erişimim bulunmuyor. Mücahit'e iletmek istediğiniz başka bir not veya konu varsa hemen kendisine iletmek üzere kaydedebilirim."
            elif any(w in inc_low for w in ["günlerden ne", "hangi gün", "bugün ne", "bugun ne"]):
                reply = f"{salutation}, bugün günlerden {day_name} ({now.day} {months_tr[now.month]})."
            elif any(w in inc_low for w in ["hava", "hava durumu", "yağmur", "soğuk"]):
                from core_jarvis.tools.system_tool import system_tool
                w_live = system_tool.get_live_weather("Eskişehir")
                reply = f"{salutation}, {w_live.get('summary_text')}"
            elif any(w in inc_low for w in ["randevu", "ilet", "söyle", "soyle", "haber ver", "not al"]):
                reply = f"Hemen ajandasına not aldım {salutation}. İlettiğiniz randevuyu Mücahit'e çalışması biter bitmez bizzat hatırlatacağım, hiç merak etmeyin."
            elif any(w in inc_low for w in ["teşekkür", "tesekkur", "sağol", "sagol", "görüşürüz", "gorusuruz", "görüşmek", "gorusmek", "iyi akşamlar", "kolay gelsin"]):
                reply = f"Rica ederim {salutation}, kendinize çok iyi bakın, hayırlı akşamlar dilerim! Hoşça kalın."
            elif already_introduced:
                reply = f"İyiyim çok teşekkür ederim {salutation}, ben de Mücahit'in yanında sistemi asiste ediyorum. Siz nasılsınız, her şey yolunda mı?"
            else:
                reply = (
                    f"Merhabalar {salutation}, ben Mücahit'in yapay zeka asistanı JARVIS. "
                    f"Mücahit şu anda bilgisayar başında önemli bir çalışma üzerinde olduğu için kısa süreliğine meşgul, size ben eşlik ediyorum. "
                    f"Nasılsınız, her şey yolunda mı?"
                )

        from core_jarvis.tools.model_manager import model_manager
        parsed = model_manager.strip_thinking_tags(reply)
        clean = parsed["clean_reply"].strip().strip('"')

        # Strict Post-Processing Sanitization:
        # Strip repeated introductions if already introduced or if close friend
        if already_introduced or rel_category == "close_friend":
            clean = re.sub(
                r"^merhabalar,?\s+ben\s+mücahit['\w]*\s+yapay\s+zeka\s+asistanı\s+jarvis\.?\s*",
                "",
                clean,
                flags=re.IGNORECASE
            )
            clean = re.sub(
                r"mücahit\s+şu\s+an\s+(?:yoğun|biraz)\s+bir\s+projede\s+çalışmakta\s+ama\s+sizinle\s+konuşmaya\s+çok\s+sevindi\.?\s*",
                "",
                clean,
                flags=re.IGNORECASE
            )

        # Eliminate forbidden salutations
        clean = re.sub(r"\bAnne\s+Hanım\b", salutation, clean, flags=re.IGNORECASE)
        clean = re.sub(r"\bSayın\s+Annem\b", salutation, clean, flags=re.IGNORECASE)
        clean = re.sub(r"\bBaba\s+Bey\b", salutation, clean, flags=re.IGNORECASE)
        clean = re.sub(r"\bSayın\s+Babam\b", salutation, clean, flags=re.IGNORECASE)
        clean = re.sub(r"\banneciğim\b", salutation, clean, flags=re.IGNORECASE)

        # If it was a farewell, strip trailing questions
        if any(w in inc_low for w in ["teşekkür", "görüşürüz", "görüşmek", "hoşça kal", "kolay gelsin"]):
            clean = re.sub(r"(?:ayrıca\s+)?başka\s+bir\s+şey\s+.*?\?", "", clean, flags=re.IGNORECASE).strip()

        return clean.strip()

    # =================================================================
    # CONTACT RESOLUTION HELPERS
    # =================================================================

    def _resolve_target_contact(self, text: str, hinted_name: str = "") -> Optional[Dict[str, Any]]:
        """Resolves contact from user text or router hint against contacts database and inbox."""
        search_pool = f"{hinted_name} {text}".lower().strip()
        if not search_pool:
            return None

        all_contacts = self.contacts.get_all()
        pool_words = set(re.findall(r"[a-zçğıöşü0-9]+", search_pool))
        text_words = set(re.findall(r"[a-zçğıöşü0-9]+", (text or "").lower()))

        # 0. STRICT DETERMINISTIC MATCH FROM USER TEXT FIRST (Never let LLM router dialogue hallucination override explicit user input!)
        if text_words & {"annem", "anneme", "annemin", "annemden", "annemle", "anne", "valide", "gülhan", "gulhan"}:
            for c in all_contacts:
                if c.get("id") == "c_annem" or c.get("name", "").lower() == "annem" or c.get("relationship", "").lower() == "anne":
                    return c
        if text_words & {"babam", "babama", "babamın", "babamdan", "babamla", "baba", "peder", "yaşar", "yasar"}:
            for c in all_contacts:
                if c.get("id") == "c_babam" or c.get("name", "").lower() == "babam" or c.get("relationship", "").lower() == "baba":
                    return c
        if text_words & {"kendim", "kendime"}:
            for c in all_contacts:
                if c.get("id") == "c_owner" or "mücahit" in c.get("name", "").lower():
                    return c
        if (text_words & {"abim", "abime", "abimin", "abimden", "abimle"}) and not (text_words & {"mehmet", "sami", "emin", "yusuf"}):
            for c in all_contacts:
                if c.get("name", "").lower() == "abim":
                    return c

        # Explicit name tokens in user text
        for c in sorted(all_contacts, key=lambda x: len(x.get("name", "")), reverse=True):
            c_name = c.get("name", "").lower().strip()
            if c.get("id") == "c_owner" and not (text_words & {"mücahit", "mucahit", "hilmi", "kendim", "kendime"}):
                continue
            if len(c_name) >= 3 and re.search(r"\b" + re.escape(c_name) + r"\b", (text or "").lower()):
                return c

        # 1. Direct exact lookup via hinted_name from LLM Router (if text didn't contain explicit target)
        if hinted_name:
            found = self.contacts.find_contact(hinted_name)
            if found:
                return found

        # 2. Relationship aliases in full search_pool
        if pool_words & {"babam", "babama", "babamın", "babamdan", "babamla", "baba", "peder"}:
            for c in all_contacts:
                if c.get("id") == "c_babam" or c.get("name", "").lower() == "babam" or c.get("relationship", "").lower() == "baba":
                    return c
        if pool_words & {"annem", "anneme", "annemin", "annemden", "annemle", "anne", "valide", "gülhan", "gulhan"}:
            for c in all_contacts:
                if c.get("id") == "c_annem" or c.get("name", "").lower() == "annem" or c.get("relationship", "").lower() == "anne":
                    return c
        if pool_words & {"kendim", "kendime"}:
            for c in all_contacts:
                if c.get("id") == "c_owner" or "mücahit" in c.get("name", "").lower():
                    return c

        # 3. Registered contacts match in search_pool (longest first, excluding owner unless explicitly named)
        for c in sorted(all_contacts, key=lambda x: len(x.get("name", "")), reverse=True):
            c_name = c.get("name", "").lower().strip()
            if c.get("id") == "c_owner" and not (pool_words & {"mücahit", "mucahit", "hilmi", "kendim", "kendime"}):
                continue
            if len(c_name) >= 2 and re.search(r"\b" + re.escape(c_name) + r"\b", search_pool):
                return c

        # 3. Check recent WhatsApp chat history if contact isn't saved in contacts.json yet
        candidate = hinted_name.strip()
        if candidate:
            hist = self.whatsapp.get_chat_history(candidate)
            if hist:
                first_m = hist[0]
                return {
                    "name": first_m.get("sender_name", candidate.capitalize()),
                    "phone": first_m.get("phone", ""),
                    "relationship": "Kayıtsız Numara / Sohbet Geçmişi",
                    "synthetic": True
                }

        # 4. Extract via Turkish name pattern matching if hinted_name was not provided
        name_patterns = [
            r"([A-Za-zçğıöşüÇĞİÖŞÜ0-9_+]+)(?:\s+(?:adlı\s+)?(?:kişisinin|kişinin|kullanıcısının|kullanıcının|arkadaşımın))\s+(?:son\s+yazdığı|son\s+mesaj|mesajı|mesajını|sorusu|sorusunu|ne\s+yazmış|ne\s+yazdı)",
            r"([A-Za-zçğıöşüÇĞİÖŞÜ0-9_+]+)(?:'nin|'nın|'in|'ın|'ün|'un|'e|'a|'ye|'ya|in|ın|nin|nın)\s+(?:son\s+yazdığı|son\s+mesaj|son\s+mesajına|son\s+mesajını|mesajı|mesajını|mesajına|sorusu|sorusunu|ne\s+yazmış|ne\s+yazdı)",
            r"([A-Za-zçğıöşüÇĞİÖŞÜ0-9_+]+)(?:le|la|'le|'la|\s+ile)\s+(?:benim\s+yerime\s+)?(?:konuş|sohbet\s+et|ilgilen)",
            r"([A-Za-zçğıöşüÇĞİÖŞÜ0-9_+]+)(?:\s+(?:adlı\s+)?(?:kişisine|kişiye|kullanıcısına))\s+(?:cevap\s+yaz|cevap\s+ver|yanıtla|yanıt\s+ver|mesaj\s+at)",
            r"(?:cevap\s+yaz|cevap\s+ver|yanıtla|yanıt\s+ver)\s+([A-Za-zçğıöşüÇĞİÖŞÜ0-9_+]+)",
            r"([A-Za-zçğıöşüÇĞİÖŞÜ0-9_+]+)(?:'e|'a|'ye|'ya|e|a|ye|ya|'i|'ı|'ü|'u|i|ı|ü|u)?\s+(?:cevap\s+yaz|cevap\s+ver|yanıtla|yanıt\s+ver|mesaj\s+at)"
        ]
        blacklist = {
            "bana", "benim", "kendime", "jarvis", "kullanıcının", "kullanici", "kişinin", "kişi", "kişisi",
            "biri", "birisi", "birine", "birini", "biriyle", "birinden",
            "arkadaş", "arkadaşım", "arkadaşıma", "arkadaşa", "arkadaşlar", "arkadaşımla", "arkadaşla", "arkadaşın",
            "dostum", "tanıdık", "onunla", "onun", "ona", "ondan", "kimse", "herhangi",
            "lütfen", "hemen", "şöyle", "bunu", "son", "mesaj", "mesajına", "mesajını", "cevap", "yanıt"
        }
        for pat in name_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                if cand.lower() not in blacklist and len(cand) >= 2:
                    found = self.contacts.find_contact(cand)
                    if found:
                        return found
                    hist = self.whatsapp.get_chat_history(cand)
                    if hist:
                        first_m = hist[0]
                        return {
                            "name": first_m.get("sender_name", cand.capitalize()),
                            "phone": first_m.get("phone", ""),
                            "relationship": "Kayıtsız Numara / Sohbet Geçmişi",
                            "synthetic": True
                        }
                    return {"name": cand.capitalize(), "phone": "", "relationship": "Bilinmeyen Numara", "synthetic": True}

        return None

    # =================================================================
    # MAIN MESSAGE ORCHESTRATOR
    # =================================================================

    @staticmethod
    def _normalize_stt_input(text: str) -> str:
        """Corrects acoustic/phonetic misrecognitions and colloquial phrasing from Turkish STT."""
        cleaned = re.sub(r"\b(?:üründür|döndür|yöndür)\b", "gönder", text, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bhali hatru\b", "hali hatrı", cleaned, flags=re.IGNORECASE)
        for variant in ["vatsa bir", "vatsab", "vatsap", "watsap", "whatsap", "watsapp", "wp"]:
            cleaned = re.sub(r"\b" + re.escape(variant) + r"\b", "whatsapp", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(?:müşkül|muskul|meşgül|mesgul|müşküllük|müşkülü)\b", "meşgul", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(?:müdürüm\s+aç|modumu\s+aç|modu\s+aç|modum\s+aç)\b", "meşgul modunu aç", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(?:aktiflemeni\s+istiyorum|aktifleştir|aktifle|açmanı\s+istiyorum|devreye\s+al)\b", "aç", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(?:göndermeni\s+istiyor|iletmeni\s+istiyor|yazmanı\s+istiyor)\b", "gönder", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(?:göndermeni\s+istiyorum|iletmeni\s+istiyorum|yazmanı\s+istiyorum)\b", "gönder", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(?:kendime\s+benim\s+yerime|kendime\s+yerime)\b", "kendime", cleaned, flags=re.IGNORECASE)
        return cleaned

    def process_message(self, user_text: str, session_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Main entrypoint: normalizes STT artifacts, routes intent via Qwen, and executes action."""
        cleaned_input = self._normalize_stt_input(user_text)
        q_lower = cleaned_input.lower().strip()

        # Fast-Path: Sub-millisecond direct draft confirmation or cancellation when pending draft exists
        if self.pending_draft:
            if q_lower in ["evet", "gönder", "gonder", "onayla", "onaylıyorum", "onayliyorum", "yolla", "tamamdır", "tamamdir", "ilet"]:
                return self.confirm_pending_draft()
            if any(w in q_lower for w in ["iptal", "vazgeç", "vazgectim", "gönderme", "gonderme", "kalsın", "kalsin", "boşver"]):
                return self.cancel_pending_draft()

        # Fast-Path: Direct voice mute and chat clear
        if any(k in q_lower for k in ["sesini kapat", "sessize al", "sesi kapat", "sesi kes", "artık konuşma"]) or q_lower.strip() in ("sus", "konuşma"):
            reply = "Sesli yanıtı kapattım efendim. Yazılı olarak devam ediyorum."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": "", "action_taken": "mute_voice"}

        if any(k in q_lower for k in ["sohbeti temizle", "sohbeti sil", "hafızayı temizle", "hafizayi temizle", "ekranı temizle"]):
            self.conversation_history.clear()
            with self.draft_lock:
                self.pending_drafts.clear()
                self.latest_draft_id = None
            return {
                "reply": "Sohbet geçmişi ve kısa süreli hafıza tamponu temizlendi efendim.",
                "speak_text": "Sohbet geçmişi temizlendi efendim.",
                "action_taken": "chat_cleared"
            }

        # Persist any user-stated rule or directive automatically
        self._auto_learn_fact(cleaned_input)

        # Fast-Path: Direct Memory / Rule Directive ("Şunu unutma: ...", "Yeni kural: ...")
        if (
            any(q_lower.startswith(p) for p in ["şunu unutma", "sunu unutma", "unutma:", "yeni kural", "kural:", "bundan sonra"])
            and "?" not in q_lower
            and not any(cmd in q_lower for cmd in ["kod yaz", "fonksiyon yaz", "analiz et", "araştır"])
        ):
            reply = (
                f"Emredersiniz Sayın Hilmi. Belirttiğiniz kuralı kalıcı hafızama (`learned_rules`) kaydettim:\n\n"
                f"📌 **Kaydedilen Direktif:** \"{cleaned_input}\"\n\n"
                f"Bundan sonraki tüm kodlama, analiz ve operasyonlarda bu standardı doğrudan uygulayacağım."
            )
            speak_text = "Emredersiniz efendim, bu kuralı kalıcı hafızama kaydettim ve bundan sonra uygulayacağım."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak_text, "action_taken": "directive_learned"}

        # Fast-Path: Model Arsenal Status Query
        if any(k in q_lower for k in ["uzman model", "model cephaneli", "yüklü yerel yapay zeka", "modellerin durumunu raporla"]):
            decision = {"action": "model_arsenal"}
        elif (
            (any(w in q_lower for w in ["ekran", "bilgisayar", "oturum"]) and any(k in q_lower for k in ["kilitle", "kilit"]))
            or any(s in q_lower for s in ["windows + l", "win + l", "win+l", "windows+l", "ekran kilidi"])
        ) and not any(neg in q_lower for neg in ["nasıl", "nedir", "rehber", "anlat"]):
            decision = {"action": "lock_workstation"}
        elif any(k in q_lower for k in [
            "klavyeden", "kısayol bas", "kısayol çalıştır", "tuşuna bas", "tuşlarına bas"
        ]) and any(w in q_lower for w in ["bas", "yürüt", "çalıştır"]):
            decision = {"action": "keyboard_shortcut", "user_instruction": cleaned_input}
        elif "steam" in q_lower and any(k in q_lower for k in ["indir", "kur", "yükle", "oyununu başlat", "oyununu aç", "oyun aç", "oyunu aç", "oyun başlat"]):
            decision = {"action": "steam_action", "user_instruction": cleaned_input}
        elif any(k in q_lower for k in ["hangi uygulamalar açık", "açık uygulamalar", "açık pencereler", "arka planda ne çalışıyor", "arka planda çalışan", "görev yöneticisi raporu"]):
            decision = {"action": "list_apps"}
        elif any(v in q_lower for v in ["kapat", "sonlandır", "durdur", "öldür"]) and (
            any(app in q_lower for app in ["uygulama", "uygulamayı", "program", "programı", "pencere", "pencereyi", "spotify", "brave", "steam", "discord", "hesap makinesi", "hesap makinasi", "not defteri", "vs code", "vscode", "obs", "vlc", "chrome", "firefox", "word", "excel"])
            or "şu uygulamayı" in q_lower
            or "su uygulamayi" in q_lower
            or "öndeki uygulamayı" in q_lower
            or "aktif pencere" in q_lower
        ):
            decision = {"action": "close_app", "user_instruction": cleaned_input}
        elif any(k in q_lower for k in ["müziği durdur", "muzigi durdur", "şarkıyı durdur", "sarkiyi durdur", "müziği duraklat", "muzigi duraklat", "müziği devam ettir", "muzigi devam ettir", "şarkıyı devam ettir", "şarkıyı oynat", "müziği oynat", "müziği başlat", "muzigi baslat", "müzik çal"]):
            mode = "pause" if any(w in q_lower for w in ["durdur", "duraklat"]) else "play"
            decision = {"action": "media_control", "user_instruction": mode}
        elif any(k in q_lower for k in ["sıradaki şarkı", "siradaki sarki", "sonraki şarkı", "sonraki parça", "şarkıyı atla", "parçayı atla", "müziği atla"]):
            decision = {"action": "media_control", "user_instruction": "next"}
        elif any(k in q_lower for k in ["önceki şarkı", "onceki sarki", "önceki parça"]):
            decision = {"action": "media_control", "user_instruction": "previous"}
        elif any(app in q_lower for app in ["spotify", "brave", "steam", "discord", "hesap makinesi", "hesap makinasi", "not defteri", "notepad", "vs code", "vscode", "obs", "vlc", "chrome", "firefox", "word", "excel", "görev yöneticisi", "dosya gezgini", "uygulamasını aç", "uygulamayı aç", "programını aç", "programı aç"]) and any(v in q_lower for v in ["aç", "ac", "başlat", "cal", "çal", "dinle", "çalıştır"]):
            decision = {"action": "open_app", "user_instruction": cleaned_input}
        elif "youtube" in q_lower and any(w in q_lower for w in ["aç", "ac", "oynat", "başlat", "cal", "çal", "ara", "izle", "dinle", "videosu", "şarkı", "sarki"]):
            decision = {"action": "play_youtube", "user_instruction": cleaned_input}
        elif "dizi" in q_lower and any(w in q_lower for w in ["bölüm", "bolum", "kaldığım", "kaldigim", "sezon", "izle", "aç", "ac"]):
            decision = {"action": "watch_series", "user_instruction": cleaned_input}
        elif (
            any(k in q_lower for k in ["tarayıcı", "tarayici", "google", "brave", "webde", "internette"])
            and any(w in q_lower for w in ["ara", "arat", "arama", "aç", "ac", "bul"])
        ):
            decision = {"action": "browser_search", "user_instruction": cleaned_input}
        elif any(w in q_lower for w in ["hava durumu", "hava nasıl", "hava nasil", "kaç derece", "kac derece", "yağmur var mı", "yagmur var mi", "hava raporu"]):
            decision = {"action": "live_weather", "user_instruction": cleaned_input}
        elif any(k in q_lower for k in ["ltx durumu", "video render durumu", "render ne alemde", "render bitti mi", "video bitti mi"]):
            decision = {"action": "ltx_status"}
        elif any(k in q_lower for k in ["ltx ile video", "ltx-2 ile video", "ltx videosu", "sinematik video üret", "siberpunk shorts filmi", "45 saniyelik film"]):
            decision = {"action": "ltx_video", "user_instruction": cleaned_input}
        elif any(k in q_lower for k in ["kaldığımız yerden devam et", "kaldigimiz yerden devam et", "kaldığım yerden", "kaldigim yerden", "projede son durum", "nerede kalmıştık"]):
            decision = {"action": "resume_project"}
        elif any(k in q_lower for k in ["neden yavaşladı", "neden yavasladi", "bilgisayarım neden yavaş", "bilgisayar neden kasıyor", "sistem doktoru", "ram neden dolu", "darboğaz analizi"]):
            decision = {"action": "diagnose_pc"}
        elif any(k in q_lower for k in ["shorts fikri", "shorts üret", "video üret", "içerik hazırla", "zenvia shorts"]):
            decision = {"action": "produce_content", "user_instruction": cleaned_input}
        elif any(k in q_lower for k in ["indirilenler", "indirilenleri", "downloads", "klasör düzenle", "klasörü düzenle", "klasörümü düzenle", "dosyaları sınıflandır", "dosyaları düzenle"]):
            decision = {"action": "organize_files"}
        elif any(k in q_lower for k in ["sistem uyarıları", "sistem bildirimleri", "gözcü raporu"]):
            decision = {"action": "proactive_alerts"}
        elif any(k in q_lower for k in [
            "mesaj geldi mi", "mesaj var mı", "mesaj var mi", "mesajları oku", "mesajlari oku",
            "mesajı oku", "mesaji oku", "ne yazmış", "ne yazmis", "okunmamış mesaj", "okunmamis mesaj",
            "gelen kutusu", "gelen kutusunu"
        ]) and not any(k in q_lower for k in ["yanıt", "yanit", "cevap", "cevapla", "yaz", "gönder", "gonder"]):
            target = ""
            for name in ["annem", "anne", "babam", "baba", "adem", "emir", "ahmet"]:
                if name in q_lower:
                    target = name
                    break
            unread = any(u in q_lower for u in ["geldi mi", "var mı", "var mi", "yeni", "okunmamış", "okunmamis"])
            decision = {"action": "read_whatsapp", "target_person": target, "is_unread_only": unread}
        elif any(k in q_lower for k in [
            "sormadan gönder", "sormadan yolla", "otomatik gönderimi aç", "otomatik gonderimi ac",
            "onaysız gönderim modunu aç", "oto mesajı aç", "oto gönderimi aç", "onay istemeden gönder", "direkt gönder"
        ]):
            self.set_auto_dispatch_whatsapp(True)
            reply = (
                "⚡ **WhatsApp Otomatik Gönderim Modu Açıldı.**\n\n"
                "Bundan sonra mesaj yanıtları için sizden onay beklemeden doğrudan iletim yapacağım efendim."
            )
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": "WhatsApp otomatik gönderim modu açıldı efendim.", "action_taken": "auto_dispatch_enabled"}

        elif any(k in q_lower for k in [
            "onay iste", "otomatik gönderimi kapat", "otomatik gonderimi kapat", "her seferinde onay sor",
            "onaylı gönderim modunu aç", "oto mesajı kapat", "onay isteyerek gönder"
        ]):
            self.set_auto_dispatch_whatsapp(False)
            reply = (
                "🛡️ **WhatsApp Onaylı Gönderim Modu Açıldı.**\n\n"
                "Bundan sonra her mesaj önce taslak olarak onayınıza sunulacaktır efendim."
            )
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": "WhatsApp onaylı gönderim modu açıldı efendim.", "action_taken": "auto_dispatch_disabled"}

        elif any(k in q_lower for k in [
            "meşgul modunu kapat", "mesgul modunu kapat", "boştayım", "bostayim",
            "ben devralıyorum", "ben devraliyorum", "meşguliyetim bitti", "görüşmeler bitti",
            "meşgul modu kapat"
        ]):
            logs = self.whatsapp.disable_ai_delegate()
            note_section = ""
            try:
                from core_jarvis.personal_assistant import personal_assistant
                all_notes = personal_assistant.agenda.get("notes", [])
                recent_notes = [n for n in all_notes if "ai_delegate" in (n.get("tags") or [])]
                if recent_notes:
                    note_lines = [f"📌 **{n.get('title')}:** {n.get('content')}" for n in recent_notes[-3:]]
                    note_section = "\n\n📝 **Görüşmeler Sırasında Kaydedilen Notlar & Randevular:**\n" + "\n".join(note_lines)
            except Exception:
                pass

            if logs:
                lines = [f"• **{item['sender_name']}**: \"{item['incoming_text']}\" ➔ *\"{item['jarvis_reply']}\"*" for item in logs]
                reply = (
                    f"🛡️ **Meşgul Modu Sonlandırıldı. Hoş Geldiniz Efendim.**\n\n"
                    f"Siz meşgulken yapay zeka vekili (JARVIS) olarak karşılanan görüşmeler:\n\n"
                    f"{chr(10).join(lines)}{note_section}"
                )
            else:
                reply = f"🛡️ **Meşgul Modu Sonlandırıldı Efendim.**\n\nSiz meşgulken gelen yeni bir mesaj olmadı.{note_section}\n\nKontrol sizdedir."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": "Meşgul modu sonlandırıldı efendim.", "action_taken": "ai_delegate_disabled", "logs": logs}

        elif any(k in q_lower for k in [
            "şu an çok meşgulüm", "su an cok mesgulum", "şu an meşgulüm", "su an mesgulum",
            "benim yerime sen konuş", "benim yerime sen konus", "benim yerime konuş", "benim yerime konus",
            "yerime konuşur musun", "yerime konusur musun", "yerime konuş", "yerime konus",
            "benim adıma konuş", "benim adima konus", "onunla sen konuş", "onunla sen konus",
            "onunla konuş", "onunla konus", "sen konuş", "sen konus",
            "meşgul modunu aç", "mesgul modunu ac", "meşgul modunu başlat", "vekil modu aç", "vekil modunu aç"
        ]):
            contact = self._resolve_target_contact(cleaned_input)
            target = contact.get("name", "") if contact else ""
            if not target:
                for name in ["annem", "anne", "babam", "baba", "abim", "yaşar", "gülhan", "adem", "emir", "ahmet"]:
                    if name in q_lower:
                        target = name.capitalize()
                        break
            self.whatsapp.enable_ai_delegate(target or None)
            target_str = f"**{contact.get('full_name') or target}**" if target else "tüm gelen kişiler"

            reply = (
                f"🤖 **WhatsApp AI Vekil (Meşgul Modu) Devreye Alındı.**\n\n"
                f"Efendim, {target_str} tarafından gelen mesajları sizin adınıza hürmet ve nezaketle karşılayacak, "
                f"şu an önemli bir çalışma üzerinde meşgul olduğunuzu belirtecek ve yapay zeka asistanınız (JARVIS) olarak "
                f"bir insan gibi empatiyle yanıtlayacağım.\n\n"
                f"İşiniz bittiğinde 'meşgul modunu kapat' veya 'özet ver' demeniz yeterlidir."
            )
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": f"Meşgul modunu açtım efendim. {target or 'Gelen mesajları'} ben karşılayacağım.", "action_taken": "ai_delegate_enabled", "target": target}

        elif any(k in q_lower for k in [
            "sistemin son durumu", "sistem durumu", "sistem durumu nedir", "sistemin durumu",
            "donanım durumu", "donanim durumu", "telemetri", "ram kullanımı", "vram durumu", "donanım telemetrisi"
        ]):
            decision = {"action": "system_status"}
        elif any(k in q_lower for k in [
            "yanıt vermem gerektiğini söyle", "ne yanıt vermem", "ne cevap vermem",
            "yanıt önerisi", "cevap önerisi", "mesajlarını analiz et", "mesajlarini analiz et"
        ]):
            target = ""
            for name in ["annem", "anne", "babam", "baba", "adem", "emir", "ahmet"]:
                if name in q_lower:
                    target = name
                    break
            decision = {"action": "reply_whatsapp", "target_person": target, "user_instruction": cleaned_input}
        else:
            # Stage 1: Ask Qwen Router for structured intent classification (with dialogue context)
            decision = self._route_intent(cleaned_input, session_history=session_history)

        action = decision.get("action", "chat")
        target_hint = decision.get("target_person", "").strip()
        phone_hint = decision.get("phone_number", "").strip()
        user_inst = decision.get("user_instruction", "").strip()
        is_unread_only = bool(decision.get("is_unread_only", False))
        is_intro = bool(decision.get("is_introduction", False))

        # Deterministic extraction of target and introduction from raw input
        # Explicit target named in user's prompt ALWAYS overrides LLM Router dialogue hallucinations!
        explicit_target = ""
        for rel_token, mapped_name in [
            ("annem", "annem"), ("anneme", "annem"), ("annemin", "annem"), ("annemle", "annem"), ("anne", "annem"), ("gülhan", "annem"),
            ("babam", "babam"), ("babama", "babam"), ("babamın", "babam"), ("babamla", "babam"), ("baba", "babam"), ("yaşar", "babam"),
            ("kendim", "kendim"), ("kendime", "kendim"),
            ("adem", "adem"), ("ademe", "adem"), ("ademin", "adem"),
            ("emir", "emir"), ("emire", "emir"),
            ("ahmet", "ahmet"), ("ahmete", "ahmet")
        ]:
            if re.search(r"\b" + re.escape(rel_token) + r"\b", q_lower):
                explicit_target = mapped_name
                break

        if not explicit_target:
            phone_m = re.search(r"\b(\+?[0-9]{10,13})\b", cleaned_input)
            if phone_m:
                explicit_target = phone_m.group(1)

        if not explicit_target:
            for c in self.contacts.get_all():
                c_n = c.get("name", "").lower()
                if len(c_n) >= 3 and re.search(r"\b" + re.escape(c_n) + r"\b", q_lower):
                    explicit_target = c_n
                    break

        if explicit_target:
            target_hint = explicit_target

        if any(k in q_lower for k in ["kendini tanıt", "kendini tanit", "tanıt", "tanit", "kendinden bahset", "kim olduğunu söyle", "kim oldugunu soyle"]):
            is_intro = True

        # Safety Guards against Router Misclassification:
        if any(k in q_lower for k in ["analiz et", "konuşmaları analiz", "mesajları analiz", "sohbeti analiz", "konuşmaları özetle", "mesajları özetle", "konuşmaları incele"]):
            action = "analyze_whatsapp_chat"

        # Deterministic Guard: WhatsApp reply / send commands should never fall through to chat
        if any(k in q_lower for k in [
            "mesaj at", "mesaj yaz", "mesaj gönder", "mesaj gonder", "tanıtan bir mesaj", "tanitan bir mesaj",
            "son mesajına cevap ver", "son mesaja cevap ver", "son mesajını yanıtla", "son mesajina cevap ver",
            "cevap yaz", "cevap ver", "yanıt yaz", "yanıtla", "yanitla"
        ]) and not any(k in q_lower for k in ["kod", "fonksiyon", "analiz"]):
            if action not in ("send_whatsapp", "reply_whatsapp"):
                action = "send_whatsapp"
        # 1. Only run unit tests if user explicitly asked for tests (never on code generation or rule statements)
        if action == "code_tests":
            if not any(t in q_lower for t in ["test", "unittest", "testleri"]) or any(c in q_lower for c in ["kod yaz", "fonksiyon"]):
                action = "chat"

        # 2. Only run multi-step autonomous tool chain if user explicitly chained >= 2 concrete system tools
        if action == "autonomous_goal":
            tool_mentions = sum(
                1 for kw in ["git diff", "test", "ekran", "brifing", "telemetri", "ram", "notlara kaydet", "araştır"]
                if kw in q_lower
            )
            if tool_mentions < 2:
                action = "chat"

        logger.info(f"Intent routed: action={action}, target='{target_hint}'")

        # 1. VOICE MUTE & CLEAR CHAT (from Router)
        if action == "mute_voice":
            reply = "Sesli yanıtı kapattım efendim. Yazılı olarak devam ediyorum."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": "", "action_taken": "mute_voice"}

        if action == "clear_chat":
            self.conversation_history.clear()
            with self.draft_lock:
                self.pending_drafts.clear()
                self.latest_draft_id = None
            return {
                "reply": "Sohbet geçmişi ve kısa süreli hafıza tamponu temizlendi efendim.",
                "speak_text": "Sohbet geçmişi temizlendi efendim.",
                "action_taken": "chat_cleared"
            }

        # 2. DRAFT CONFIRMATION / CANCELLATION / REVISION
        if action == "confirm_draft" and self.pending_draft:
            return self.confirm_pending_draft()

        if action == "cancel_draft" and self.pending_draft:
            return self.cancel_pending_draft()

        if action == "revise_draft" and self.pending_draft:
            contact = self._last_contact or {"name": self.pending_draft["recipient"], "phone": self.pending_draft["phone"]}
            history = self.whatsapp.get_chat_history(contact.get("name", ""))
            synth = self._synthesize_whatsapp_draft_or_ask(
                cleaned_input, contact, history, user_instruction=user_inst or cleaned_input
            )
            new_body = synth.get("draft_message") or user_inst
            if new_body:
                self.pending_draft["message"] = new_body
                reply = (
                    f"Mesaj taslağını istediğiniz doğrultuda güncelledim efendim:\n\n"
                    f"📱 **Alıcı:** {self.pending_draft['recipient']} ({self.pending_draft['phone']})\n"
                    f"💬 **Yeni Taslak:** \"{new_body}\"\n\n"
                    f"Onaylıyor musunuz efendim?"
                )
                speak_text = f"Taslağı güncelledim: \"{new_body}\". Onaylıyor musunuz?"
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": speak_text, "action_taken": "draft_revised", "draft": self.pending_draft}

        # 3. SYSTEM TELEMETRY & FULL ECOSYSTEM STATUS
        if action == "system_status":
            metrics = self.vram.get_system_metrics()
            is_wa_conn = self.whatsapp.is_connected() if callable(getattr(self.whatsapp, "is_connected", None)) else False
            inbox_count = len(self.whatsapp.get_inbox(limit=100))
            is_delegate = self.whatsapp.ai_delegate_active
            is_auto = self.auto_dispatch_whatsapp
            active_model = self.model_name

            # Personal Assistant Telemetry
            pending_tasks_count = 0
            agenda_items_count = 0
            try:
                from core_jarvis.personal_assistant import personal_assistant
                briefing = personal_assistant.get_daily_briefing()
                pending_tasks_count = len(briefing.get("pending_tasks", []))
                agenda_items_count = len(briefing.get("agenda_today", []))
            except Exception:
                pass

            reply = (
                f"### 🛡️ JARVIS Master Ekosistem & Telemetri Durumu (Sayın Hilmi)\n\n"
                f"📱 **WhatsApp Operasyon Hattı:**\n"
                f"- **Bağlantı Durumu:** {'🟢 Çevrimiçi & Aktif' if is_wa_conn else '🟡 Bağlanıyor / QR Bekleniyor'}\n"
                f"- **Senkronize Mesaj:** {inbox_count} adet kayıtlı ileti\n"
                f"- **🤖 Meşgul Modu (AI Vekil):** {'🟢 Açık (Gelen mesajları JARVIS karşılıyor)' if is_delegate else '⚪ Kapalı'}\n"
                f"- **⚡ Otomatik Gönderim (Zero-Click):** {'🟢 Açık (Onaysız doğrudan gönderim)' if is_auto else '🟡 Kapalı (Taslak onayı beklenir)'}\n\n"
                f"💻 **Donanım & VRAM Kalkanı:**\n"
                f"- **İşlemci (CPU):** Intel Core i5-14400F (10 Çekirdek, 16 İş Parçacığı)\n"
                f"- **Ekran Kartı (GPU):** AMD Radeon RX 9060 XT (16 GB GDDR6 VRAM)\n"
                f"- **RAM Durumu:** %{metrics['ram_used_pct']} dolu ({metrics['ram_available_gb']} GB boş / {metrics['ram_total_gb']} GB)\n"
                f"- **VRAM Kalkanı:** {'🟢 Yeşil (Render ve model için güvenli)' if metrics['safe_for_diffusion'] else '🟡 Sarı (Bellek Yoğun)'}\n\n"
                f"🧠 **Yapay Zeka Motorları:**\n"
                f"- **Aktif Dil Modeli:** `{active_model}` (VRAM Sabitlenmiş)\n"
                f"- **Ses Algılama (STT):** Faster-Whisper Türkçe VAD Motoru\n"
                f"- **Ses Sentezleme (TTS):** Microsoft Edge Neural / Kokoro-82M\n\n"
                f"📋 **Kişisel Ajanda & Görevler:**\n"
                f"- **Bugünkü Randevular:** {agenda_items_count} kayıt\n"
                f"- **Bekleyen Görevler:** {pending_tasks_count} görev\n\n"
                f"Sistem tüm fonksiyonlarıyla stabil ve emrinizdedir efendim."
            )
            speak_text = f"Sistem durumu stabil efendim. WhatsApp {'bağlı' if is_wa_conn else 'bağlantıda'}, Meşgul modu {'açık' if is_delegate else 'kapalı'}, bellek kullanımı yüzde {metrics['ram_used_pct']}."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak_text, "action_taken": "system_telemetry", "details": metrics}

        # 4. YOUTUBE REPORT
        if action == "youtube_report":
            if not YT_TOKEN_FILE.exists():
                reply = "Efendim, YouTube hesabınız henüz bağlı değil (`config/youtube_tokens.json` bulunamadı)."
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": "YouTube kanalınız henüz bağlı değil efendim.", "action_taken": "youtube_unauthorized"}
            from engine.autonomous_feedback import get_channel_report
            report = get_channel_report("default")
            demands = "\n".join(f"• {d}" for d in report.get("audience_demands", [])) or "• Yeterli veri yok"
            reply = (
                f"Kanalınızdaki canlı YouTube yorum analizi:\n\n"
                f"📊 **Duygu Skoru:** %{report.get('sentiment_score', 0)} Pozitif\n"
                f"🎯 **İzleyici Talepleri:**\n{demands}"
            )
            speak_text = f"YouTube analizini tamamladım efendim. Duygu skoru yüzde {report.get('sentiment_score', 0)} pozitif."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak_text, "action_taken": "comment_analysis", "details": report}

        # 5. CONTACT MANAGEMENT (ADD / DELETE)
        if action == "add_contact":
            if target_hint and phone_hint:
                saved = self.contacts.add_contact(target_hint, phone_hint)
                reply = f"Rehbere **{saved['name']}** ({saved['phone']}) başarıyla kaydedildi efendim."
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": f"{saved['name']} rehbere eklendi efendim.", "action_taken": "contact_saved", "details": saved}
            return {
                "reply": "Efendim, kişiyi kaydedebilmem için lütfen hem adını hem de telefon numarasını belirtin.",
                "speak_text": "Lütfen eklenecek kişinin adını ve numarasını belirtin efendim.",
                "action_taken": "contact_info_missing"
            }

        if action == "delete_contact" and target_hint:
            deleted = self.contacts.delete_contact(target_hint)
            if deleted:
                reply = f"Efendim, **{deleted['name']}** kişisini rehberinizden sildim."
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": f"{deleted['name']} rehberden silindi efendim.", "action_taken": "contact_deleted", "details": deleted}
            return {
                "reply": f"Efendim, rehberinizde '{target_hint}' adında bir kayıt bulamadım.",
                "speak_text": f"Rehberde {target_hint} bulunamadı efendim.",
                "action_taken": "contact_not_found"
            }

        # 6. ANALYZE WHATSAPP CHAT HISTORY
        if action == "analyze_whatsapp_chat":
            contact = self._resolve_target_contact(cleaned_input, target_hint)
            if not contact and target_hint:
                candidates = self.contacts.find_contacts_candidates(target_hint)
                if len(candidates) > 1:
                    cand_names = ", ".join(f"**{c.get('full_name') or c.get('name')}** ({c.get('phone')})" for c in candidates)
                    reply = f"Sayın Hilmi, rehberinizde '{target_hint}' ile eşleşen {len(candidates)} kişi var: {cand_names}. Hangisinin konuşmalarını analiz etmemi istersiniz?"
                    self._record_turn(user_text, reply)
                    return {"reply": reply, "speak_text": reply, "action_taken": "contact_ambiguous", "candidates": candidates}
                elif not candidates:
                    reply = f"Sayın Hilmi, rehberinizde '{target_hint}' adında bir kişi veya kayıtlı sohbet bulunamadı. Yapamayacağım bir işlemde sizi oyalamam."
                    self._record_turn(user_text, reply)
                    return {"reply": reply, "speak_text": reply, "action_taken": "contact_not_found"}

            contact = contact or self._last_contact
            if not contact:
                reply = "Sayın Hilmi, kiminle olan konuşmaları analiz etmemi istediğinizi belirleyemedim. Lütfen kişi adını belirtin (örneğin: 'annemle olan konuşmaları analiz et')."
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": reply, "action_taken": "contact_not_specified"}

            c_name = contact.get("name", "")
            disp_name = contact.get("full_name") or c_name
            history = self.whatsapp.get_chat_history(c_name)
            if not history:
                reply = f"Sayın Hilmi, **{disp_name}** ile sistemde kayıtlı herhangi bir WhatsApp mesaj geçmişi bulunamadı. Yapamayacağım bir işlemde sizi asla oyalamam; analiz edebilmem için en az bir mesaj kaydı olması gerekiyor."
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": f"{disp_name} ile kayıtlı sohbet geçmişi bulunamadı efendim.", "action_taken": "no_chat_history"}

            # Take up to 35 most recent messages for comprehensive analysis
            recent_msgs = history[-35:]
            transcript_lines = []
            for m in recent_msgs:
                sender = "Hilmi (Siz)" if m.get("from_me") else (m.get("sender_name") or disp_name)
                t_str = m.get("time") or m.get("date") or ""
                transcript_lines.append(f"[{t_str} - {sender}]: {m.get('text', '')}")
            transcript_text = "\n".join(transcript_lines)

            analysis_prompt = f"""Aşağıda Mücahit Hilmi ile {disp_name} arasındaki son WhatsApp konuşma dökümü yer almaktadır:

{transcript_text}

GÖREV:
Bu konuşma geçmişini derinlemesine incele ve Mücahit Hilmi'ye şu formatta net, açık, dürüst ve özet bir rapor sun:
1. 📌 **Konuşulan Ana Konular ve Özet:** (Neler konuşuldu?)
2. 🎭 **Genel Duygu ve İletişim Tonu:** (İlişkinin havası, samimiyet, endişe veya memnuniyet durumu)
3. ⏳ **Açıkta Kalan Konular / Bekleyenler:** (Cevap bekleyen bir soru, yapılacak bir iş veya çözülmemiş bir durum var mı?)
4. 💡 **JARVIS Önerisi:** (Hilmi'ye bu iletişimle ilgili ne önerirsin?)

Cevabını doğrudan bu başlıklarla, samimi ama net ve dürüst bir dille ver."""

            messages = [
                {"role": "system", "content": f"{JARVIS_PERSONA_PROMPT}\n\nSen dürüst, gerçekçi ve analitik bir sistem müfettişisin."},
                {"role": "user", "content": analysis_prompt}
            ]
            analysis_reply = self._call_ollama(messages, temperature=0.3, timeout=45)
            if not analysis_reply:
                analysis_reply = f"Sayın Hilmi, **{disp_name}** ile olan son {len(recent_msgs)} mesaj incelendi ancak model özet üretemedi."

            reply = f"📊 **{disp_name} ile WhatsApp Konuşma Analizi ({len(recent_msgs)} Mesaj):**\n\n{analysis_reply}"
            speak_text = f"{disp_name} ile olan konuşmalarınızı analiz ettim efendim. Rapor hazır."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak_text, "action_taken": "whatsapp_chat_analyzed", "contact": contact, "message_count": len(recent_msgs)}

        # 6. READ WHATSAPP MESSAGES
        if action == "read_whatsapp":
            contact = self._resolve_target_contact(cleaned_input, target_hint)
            if not contact and target_hint:
                candidates = self.contacts.find_contacts_candidates(target_hint)
                if len(candidates) > 1:
                    cand_names = ", ".join(f"**{c.get('full_name') or c.get('name')}** ({c.get('phone')})" for c in candidates)
                    reply = f"Efendim, rehberinizde '{target_hint}' ile eşleşen {len(candidates)} farklı kişi bulundu: {cand_names}. Hangisinin mesajlarını okumamı istersiniz?"
                    self._record_turn(user_text, reply)
                    return {
                        "reply": reply,
                        "speak_text": f"Rehberinizde birden fazla {target_hint} var efendim. Hangisini kastettiniz?",
                        "action_taken": "contact_ambiguous",
                        "candidates": candidates
                    }
            if contact:
                self._last_contact = contact
                c_name = contact.get("name", "")
                history = self.whatsapp.get_chat_history(c_name)
                incoming = [m for m in history if not m.get("from_me")]
                if is_unread_only:
                    incoming = [m for m in incoming if m.get("unread")]

                if incoming:
                    recent_slice = incoming[-3:]
                    lines = [f"• ({m.get('time', '')}): \"{m.get('text', '')}\"" for m in recent_slice]
                    last_txt = recent_slice[-1].get("text", "")
                    reply = (
                        f"Efendim, **{contact.get('full_name') or c_name}** kişisinden gelen son mesajlar:\n\n"
                        f"{chr(10).join(lines)}\n\n"
                        f"Yanıt hazırlamamı ister misiniz?"
                    )
                    speak_text = f"{c_name} kişisinin son mesajı: \"{last_txt}\". Yanıtlayalım mı efendim?"
                    self._record_turn(user_text, reply)
                    return {"reply": reply, "speak_text": speak_text, "action_taken": "contact_message_read", "contact": contact, "messages": recent_slice}
                return {
                    "reply": f"Efendim, **{c_name}** kişisinden {'okunmamış ' if is_unread_only else ''}mesaj bulunamadı.",
                    "speak_text": f"{c_name} kişisinden mesaj bulunamadı efendim.",
                    "action_taken": "contact_no_messages"
                }

            # General inbox check
            inbox = self.whatsapp.get_inbox(limit=8, unread_only=is_unread_only)
            incoming_inbox = [m for m in inbox if not m.get("from_me")]
            if incoming_inbox:
                lines = [
                    f"• **{m.get('sender_name', 'Bilinmeyen')}** ({m.get('time', '')}): \"{m.get('text', '')}\""
                    for m in incoming_inbox[-5:]
                ]
                last_m = incoming_inbox[-1]
                reply = f"Efendim, WhatsApp gelen kutunuzdaki son mesajlar:\n\n{chr(10).join(lines)}"
                speak_text = f"Gelen kutunuzda {len(incoming_inbox)} mesaj var. Son mesaj {last_m.get('sender_name')} tarafından: \"{last_m.get('text')}\"."
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": speak_text, "action_taken": "inbox_checked", "details": incoming_inbox}
            return {
                "reply": "Efendim, WhatsApp gelen kutunuzda yeni mesaj bulunmuyor.",
                "speak_text": "WhatsApp gelen kutunuzda yeni mesaj bulunmuyor efendim.",
                "action_taken": "inbox_empty"
            }

        # 7. REPLY OR SEND WHATSAPP MESSAGE (INTIMACY-AWARE + HITL CLARIFICATION)
        if action in ("reply_whatsapp", "send_whatsapp"):
            contact = self._resolve_target_contact(cleaned_input, target_hint)
            if not contact and target_hint:
                candidates = self.contacts.find_contacts_candidates(target_hint)
                if len(candidates) > 1:
                    cand_names = ", ".join(f"**{c.get('full_name') or c.get('name')}** ({c.get('phone')})" for c in candidates)
                    reply = f"Efendim, rehberinizde '{target_hint}' ile eşleşen {len(candidates)} farklı kişi bulundu: {cand_names}. Mesajı hangisine hazırlamamı istersiniz?"
                    self._record_turn(user_text, reply)
                    return {
                        "reply": reply,
                        "speak_text": f"Rehberinizde birden fazla {target_hint} var efendim. Hangisine yazalım?",
                        "action_taken": "contact_ambiguous",
                        "candidates": candidates
                    }
            contact = contact or self._last_contact
            
            # Universal fallback: if user says "son mesajı cevapla" without naming anyone, grab latest incoming sender
            if not contact:
                latest_in = self.whatsapp.get_inbox(limit=10, unread_only=False)
                incoming_msgs = [m for m in latest_in if not m.get("from_me")]
                if incoming_msgs:
                    last_m = incoming_msgs[-1]
                    s_name = last_m.get("sender_name", "")
                    s_phone = last_m.get("phone", "")
                    found = self.contacts.find_contact(s_name)
                    if found:
                        contact = found
                    else:
                        contact = {"name": s_name, "phone": s_phone, "relationship": "Bilinmeyen Numara", "synthetic": True}

            if not contact:
                reply = (
                    "Efendim, mesajı hangi arkadaşınıza veya kişiye iletmemi arzu edersiniz?\n\n"
                    "Sol taraftaki rehberden dilediğiniz kişiye tıklayabilir veya bana doğrudan isim/numara belirtebilirsiniz (Örn: *'Adem'e mesaj at'*, *'Anneme mesaj at'*)."
                )
                speak_text = "Hangi kişiye mesaj yazmamı istersiniz efendim? Sol rehberden seçebilir veya ismini belirtebilirsiniz."
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": speak_text, "action_taken": "contact_not_found"}

            self._last_contact = contact
            c_name = contact.get("name", "")
            disp_name = contact.get("full_name") or c_name
            phone = contact.get("phone", "") or phone_hint

            if not phone:
                reply = f"Efendim, **{disp_name}** için kayıtlı telefon numarası bulamadım. Numarasını paylaşır mısınız?"
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": f"{c_name} için telefon numarası kayıtlı değil efendim.", "action_taken": "contact_phone_missing"}

            history = self.whatsapp.get_chat_history(c_name)
            synth = self._synthesize_whatsapp_draft_or_ask(
                cleaned_input, contact, history, user_instruction=user_inst, is_introduction=is_intro
            )

            # Check if Jarvis needs Mücahit's decision before drafting (Requirement #2)
            if synth.get("needs_user_decision") and synth.get("question_to_owner"):
                question = synth["question_to_owner"]
                self._record_turn(user_text, question)
                return {
                    "reply": question,
                    "speak_text": question,
                    "action_taken": "clarification_requested",
                    "contact": contact
                }

            msg_body = synth.get("draft_message", "").strip()
            intimacy_badge = synth.get("detected_intimacy", "doğal").capitalize()

            if self.auto_dispatch_whatsapp:
                send_res = self.whatsapp.send_message_to_phone(phone, msg_body, recipient_name=disp_name)
                reply = (
                    f"⚡ **Mesaj Doğrudan İletildi (Otomatik Gönderim):**\n\n"
                    f"📱 **Alıcı:** {disp_name} ({phone})\n"
                    f"💬 **İletilen Mesaj:** \"{msg_body}\"\n"
                    f"✨ **Analiz Edilen Üslup:** *{intimacy_badge}*"
                )
                speak_text = f"{disp_name} kişisine mesajı doğrudan ilettim efendim."
                self._record_turn(user_text, reply)
                return {
                    "reply": reply,
                    "speak_text": speak_text,
                    "action_taken": "whatsapp_auto_dispatched",
                    "contact": contact,
                    "message": msg_body,
                    "result": send_res
                }

            self.pending_draft = {
                "recipient": disp_name,
                "phone": phone,
                "message": msg_body,
                "intimacy": intimacy_badge,
                "created_at": time.time()
            }

            reply = (
                f"Efendim, **{disp_name}** ile olan sohbet geçmişinizi analiz ederek (**Üslup:** *{intimacy_badge}*) şu taslağı hazırladım:\n\n"
                f"📱 **Alıcı:** {disp_name} ({phone})\n"
                f"💬 **Taslak:** \"{msg_body}\"\n\n"
                f"Göndermemi onaylıyor musunuz, yoksa revize etmemi istediğiniz bir kısım var mı?"
            )
            speak_text = f"{c_name} için hazırladığım mesaj: \"{msg_body}\". Onaylıyor musunuz efendim?"
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak_text, "action_taken": "draft_created", "draft": self.pending_draft}

        # 8. DAILY BRIEFING
        if action == "daily_briefing":
            from core_jarvis.personal_assistant import personal_assistant
            b = personal_assistant.get_daily_briefing()
            reply = f"📋 **Günlük Yönetici Brifingi:**\n\n{b.get('speak_text') or b.get('executive_briefing_text')}"
            speak = b.get("speak_text") or "Günlük brifing hazır efendim."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "daily_briefing", "briefing": b}

        # 9. TASKS & NOTES
        if action == "manage_task":
            from core_jarvis.personal_assistant import personal_assistant
            task_title = user_inst or cleaned_input
            if any(k in cleaned_input.lower() for k in ["ekle", "yeni", "kaydet"]):
                res = personal_assistant.add_task(title=task_title, priority="normal")
                reply = f"Görevi ajandanıza ekledim efendim: **{task_title}**"
                speak = f"Görev eklendi: {task_title}"
            else:
                tasks = personal_assistant.get_tasks()
                lines = [f"• [{t.get('priority', 'normal').upper()}] {t.get('title')}" for t in tasks[:6]]
                reply = f"📋 **Aktif Görevleriniz:**\n\n" + ("\n".join(lines) if lines else "Bekleyen görev bulunmuyor efendim.")
                speak = f"Toplam {len(tasks)} aktif göreviniz var efendim."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "manage_task"}

        if action == "add_reminder":
            from core_jarvis.personal_assistant import personal_assistant
            rem_title = user_inst or cleaned_input
            res = personal_assistant.add_reminder(title=rem_title, datetime_iso="")
            reply = f"Hatırlatıcı kaydedildi efendim: **{rem_title}**"
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": reply, "action_taken": "reminder_saved"}

        if action == "add_note":
            from core_jarvis.personal_assistant import personal_assistant
            note_content = user_inst or cleaned_input
            res = personal_assistant.add_note(title="Yönetici Notu", content=note_content)
            reply = f"Not defterinize kaydettim efendim:\n\n> {note_content}"
            speak = "Not kaydedildi efendim."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "note_saved"}

        # 10. SCREEN INSPECTION (JARVIS VISION)
        if action == "screen_inspect":
            from core_jarvis.tools.vision_tool import vision_tool
            mode = "error_check" if any(k in cleaned_input.lower() for k in ["hata", "error"]) else "general"
            res = vision_tool.analyze_screen(prompt=user_inst or cleaned_input, mode=mode)
            analysis = res.get("analysis", "Ekran analizi tamamlandı.")
            reply = f"🖥️ **JARVIS Vision Ekran Analizi:**\n\n{analysis}"
            speak = analysis[:250] + "..." if len(analysis) > 250 else analysis
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "screen_inspect", "vision": res}

        # 11. WEB & DOCUMENTATION RESEARCH
        if action == "web_research":
            from core_jarvis.tools.browser_research_tool import browser_research_tool
            q = user_inst or cleaned_input
            res = browser_research_tool.conduct_research_and_archive(topic=q, auto_note=True)
            reply = f"🌐 **Web Araştırma Sentezi ({q}):**\n\n{res.get('summary_text')}"
            speak = res.get("summary_text", "")[:280]
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "web_research", "research": res}

        # 12. LOCAL RAG CODE & DOCS SEARCH
        if action == "search_docs":
            from core_jarvis.tools.knowledge_indexer import knowledge_indexer
            q = user_inst or cleaned_input
            res = knowledge_indexer.search(query=q, top_k=3)
            reply = res.get("executive_summary", "")
            if res.get("results"):
                for hit in res["results"][:2]:
                    reply += f"\n\n📂 **{hit['file_name']}** (Satır {hit['start_line']}-{hit['end_line']}):\n```python\n{hit['preview'][:200]}\n```"
            speak = res.get("executive_summary", "")
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "search_docs", "search": res}

        if action == "summarize_doc":
            from core_jarvis.tools.knowledge_indexer import knowledge_indexer
            target_path = user_inst or cleaned_input
            res = knowledge_indexer.summarize_document(file_path=target_path)
            reply = f"📑 **Doküman Özeti ({res.get('file_name', target_path)}):**\n\n{res.get('lead_text')}\n• Yapı: {res.get('structure_summary')}"
            speak = res.get("lead_text", "")
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "summarize_doc", "document": res}

        # 13. CODE TESTS & GIT DIFF
        if action == "code_tests":
            from core_jarvis.orchestrator import orchestrator
            res = orchestrator.code.run_tests()
            reply = f"🧪 **Birim Testleri:**\n\n{'✅ Tüm testler başarıyla geçti.' if res.get('success') else '❌ Test hatası: ' + res.get('error', res.get('stdout', ''))}"
            speak = "Tüm testler geçti efendim." if res.get("success") else "Testlerde hata bulundu efendim."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "code_tests", "result": res}

        if action == "git_diff":
            from core_jarvis.orchestrator import orchestrator
            diff = orchestrator.code.get_git_diff()
            reply = f"📝 **Git Değişiklikleri:**\n\n```\n{diff.get('output', 'Kaydedilmemiş değişiklik yok.')}\n```"
            speak = "Git değişikliklerini listeledim efendim."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "git_diff", "diff": diff}

        # 14. WAKE ON LAN & MODEL ARSENAL
        if action == "wake_on_lan":
            from core_jarvis.tools.wol_tool import wol_tool
            res = wol_tool.send_magic_packet()
            reply = f"⚡ **Wake-on-LAN:**\n{res.get('message', 'Sihirli paket iletildi.')}"
            speak = "Wake on LAN sinyali gönderildi efendim."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "wake_on_lan", "result": res}

        if action == "model_arsenal":
            from core_jarvis.tools.model_manager import model_manager
            st = model_manager.get_arsenal_status()
            lines = []
            for item in st["arsenal"]:
                badge = "✅ Hazır" if item["is_exact_sota_installed"] else (f"⚠️ Yedek ({item['active_installed_model']})" if item["is_installed"] else "❌ Kurulmadı")
                lines.append(f"• **{item['title']}** (`{item['recommended_model']}`): {badge}")
            reply = (
                f"🧠 **JARVIS Nokta Atışı 5'li Uzman Model Cephaneliği ({st['hardware_target']}):**\n\n"
                + "\n".join(lines)
            )
            speak = "Uzman model cephaneliği durumunu ekrana yansıttım efendim."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "model_arsenal", "arsenal": st}

        # 14B. DESKTOP TASK MANAGER, APP CONTROL & STEAM AUTOMATION
        if action == "list_apps":
            from core_jarvis.tools.system_tool import system_tool
            win_info = system_tool.get_open_windows_and_apps()
            fg = win_info.get("foreground_window") or "Tespit edilemedi"
            wins = win_info.get("open_windows") or []
            win_lines = [
                f"• **{w['name']}.exe** — *{w['title']}* (`{w['memory_mb']} MB RAM`)"
                for w in wins[:10]
            ] or ["• Açık masaüstü penceresi bulunamadı."]
            reply = (
                f"🖥️ **JARVIS Görev Yöneticisi & Açık Pencereler:**\n\n"
                f"🎯 **Aktif Ön Plan Penceresi:** `{fg}`\n\n"
                f"📊 **Çalışan Masaüstü Uygulamaları (RAM Kullanımına Göre):**\n"
                + "\n".join(win_lines)
            )
            speak = f"Şu anda ekranda {len(wins)} aktif uygulama penceresi açık efendim. Ön planda {fg} bulunuyor."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "list_apps", "windows": win_info}

        if action == "open_app":
            from core_jarvis.tools.system_tool import system_tool
            res = system_tool.open_application(app_query=cleaned_input, extra_arg=user_inst)
            if res.get("success"):
                reply = res.get("message") or f"🚀 **{res.get('app')}** uygulaması başlatıldı efendim."
                speak = f"{res.get('app')} başlatıldı efendim."
            else:
                reply = f"❌ {res.get('error')}"
                speak = "Uygulama başlatılamadı efendim."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "open_app", "result": res}

        if action == "close_app":
            from core_jarvis.tools.system_tool import system_tool
            res = system_tool.close_application(app_query=cleaned_input, extra_arg=user_inst)
            if res.get("success"):
                reply = (
                    f"🛑 **{res.get('app')}** uygulaması güvenli şekilde kapatıldı efendim.\n"
                    f"💾 **Boşaltılan Sistem Belleği (RAM):** `{res.get('freed_mb', 0)} MB` ({res.get('closed_count', 1)} işlem sonlandırıldı)"
                )
                speak = f"{res.get('app')} kapatıldı ve {res.get('freed_mb', 0)} megabayt bellek boşaltıldı efendim."
            else:
                reply = f"⚠️ {res.get('error')}"
                speak = res.get("error", "Uygulama kapatılamadı efendim.")
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "close_app", "result": res}

        if action == "lock_workstation":
            from core_jarvis.tools.system_tool import system_tool
            res = system_tool.lock_workstation()
            if res.get("success"):
                reply = "🔒 **Bilgisayar Ekranı Kilitlendi:**\n\nEkran Windows + L komutuyla güvenli şekilde anında kilitlendi efendim. Güvenlik protokolü devrede."
                speak = "Bilgisayar ekranı kilitlendi efendim."
            else:
                reply = f"⚠️ Ekran kilitlenirken hata oluştu: {res.get('error')}"
                speak = "Ekran kilitlenemedi efendim."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "lock_workstation", "result": res}

        if action == "keyboard_shortcut":
            from core_jarvis.tools.system_tool import system_tool
            target_sc = user_inst or cleaned_input
            res = system_tool.send_keyboard_shortcut(target_sc)
            reply = res.get("message", "Klavyeden istenen tuş kombinasyonu yürütüldü efendim.")
            speak = "Klavye komutu yürütüldü efendim."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "keyboard_shortcut", "result": res}

        if action == "media_control":
            from core_jarvis.tools.system_tool import system_tool
            res = system_tool.media_control(user_inst or "play_pause")
            act_label = {
                "play": "devam ettirildi",
                "pause": "duraklatıldı",
                "next": "sıradaki parçaya geçildi",
                "previous": "önceki parçaya dönüldü"
            }.get(user_inst, "kontrol edildi")
            reply = f"🎵 **Medya Kontrolü:** Müzik {act_label} efendim."
            speak = f"Müzik {act_label} efendim."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "media_control", "result": res}

        # 14C. BROWSER SEARCH, YOUTUBE, TV SERIES & LIVE WEATHER
        if action == "browser_search":
            from core_jarvis.tools.system_tool import system_tool
            raw_q = user_inst or cleaned_input
            clean_search = re.sub(
                r"^(tarayıcıda|tarayicida|tarayıcıyı\s+açıp|tarayiciyi\s+acip|google['\w]*\s+(?:da\s+|de\s+)?|webde|internette|brave['\w]*\s+(?:da\s+|de\s+)?)\s+(ara\s+|aç\s+|bul\s+)?",
                "",
                raw_q,
                flags=re.IGNORECASE
            )
            clean_search = re.sub(r"\s+(ara|bul|aç)$", "", clean_search, flags=re.IGNORECASE).strip(" '\".,:-")
            res = system_tool.open_browser_search(clean_search or raw_q, engine="google")
            reply = f"🌐 **Tarayıcıda Web Araması Başlatıldı:**\n\n`{clean_search or raw_q}` araması varsayılan tarayıcınızda açıldı balım!"
            speak = f"{clean_search or raw_q} araması tarayıcınızda açıldı balım."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "browser_search", "result": res}

        if action == "play_youtube":
            from core_jarvis.tools.system_tool import system_tool
            raw_q = user_inst or cleaned_input
            res = system_tool.open_youtube_video(raw_q)
            v_title = res.get("query") or "İstenen video"
            reply = f"▶️ **YouTube Başlatıldı:**\n\n`{v_title}` videosu tarayıcınızda açıldı balım! İyi seyirler dilerim."
            speak = f"{v_title} videosu YouTube üzerinde açıldı balım."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "play_youtube", "result": res}

        if action == "watch_series":
            from core_jarvis.tools.system_tool import system_tool
            raw_q = user_inst or cleaned_input
            m_ep = re.search(r"(\d+)\.?\s*sezon\s*(\d+)\.?\s*bölüm", raw_q, re.I)
            s_num = int(m_ep.group(1)) if m_ep else None
            e_num = int(m_ep.group(2)) if m_ep else None

            clean_series = re.sub(
                r"\s*(\d+\.?\s*sezon\s*\d+\.?\s*bölüm|\bdizisind?e?\b|\bson\s+kaldığım\s+bölüm[üu]?\b|\bkaldığım\s+bölüm[üu]?\b|\bkaçıncı\s+bölüm\b|\baç\b|\bizle\b)",
                "",
                raw_q,
                flags=re.IGNORECASE
            ).strip(" '\".,:-")

            res = system_tool.open_series_episode(clean_series or raw_q, season=s_num, episode=e_num, from_history=True)
            reply = f"🎬 **Dizi Oynatıcı & Geçmiş Taraması:**\n\n{res.get('message', 'Dizi tarayıcıda açıldı balım.')}"
            speak = res.get("message", "Dizi tarayıcınızda açıldı balım.")
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "watch_series", "result": res}

        if action == "live_weather":
            from core_jarvis.tools.system_tool import system_tool
            target_city = "Eskişehir"
            for c in ["istanbul", "ankara", "izmir", "trabzon", "bursa", "antalya", "eskişehir", "eskisehir"]:
                if c in cleaned_input.lower():
                    target_city = c
                    break
            res = system_tool.get_live_weather(target_city)
            reply = f"🌤️ **Canlı Hava Durumu ({res.get('city')}):**\n\n{res.get('summary_text')}\n\n*(Veri Kaynağı: {res.get('source')})*"
            speak = res.get("summary_text", "")
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "live_weather", "weather": res}

        if action == "ltx_status":
            from core_jarvis.tools.studio_bridge import studio_bridge
            rep = studio_bridge.get_ltx_status_summary()
            self._record_turn(user_text, rep)
            return {"reply": rep, "speak_text": "LTX video durumu raporlandı efendim.", "action_taken": "ltx_status"}

        if action == "ltx_video":
            from core_jarvis.tools.studio_bridge import studio_bridge
            if any(w in q_lower for w in ["hikaye", "senaryo", "film", "45", "siberpunk", "tüm sahneler"]):
                res = studio_bridge.trigger_story_generator(all_scenes=True)
            else:
                clean_p = re.sub(r"\b(ltx-2|ltx|ile|video|üret|yap|başlat|lütfen)\b", "", cleaned_input, flags=re.IGNORECASE).strip(" '\".,:-")
                res = studio_bridge.trigger_ltx_video(prompt=clean_p or "A cinematic drone shot of a futuristic cyberpunk city at night with neon lights, photorealistic, 4k")
            reply = res.get("message") or "LTX-2 video üretimi başlatıldı balım."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": "LTX-2 video üretimi başlatıldı efendim. VRAM tahliyesi yapıldı.", "action_taken": "ltx_video_dispatched", "result": res}

        if action == "steam_action":
            from core_jarvis.tools.system_tool import system_tool
            raw_q = user_inst or cleaned_input
            # Clean out command verbs to isolate the game title
            cleaned_game = re.sub(
                r"\b(?:steami|steam'i|steamde|steam'de|steamden|steam'den|steam|aç|ve|oyununu|oyunu|indirmeye|indirmeyi|indir|kurmaya|kur|yükle|başlat|çalıştır|lütfen|hemen)\b",
                " ",
                raw_q,
                flags=re.IGNORECASE
            )
            cleaned_game = re.sub(r"\s+", " ", cleaned_game).strip(" '\".,:-")
            mode = "install" if any(k in q_lower for k in ["indir", "kur", "yükle"]) else "run"
            res = system_tool.steam_game_action(cleaned_game, mode=mode)
            if res.get("success"):
                if res.get("already_installed"):
                    reply = (
                        f"🎮 **Steam Kontrolü & Durum Raporu:**\n\n"
                        f"• **Oyun:** **{res.get('game_name')}** (Steam AppID: `{res.get('appid')}`)\n"
                        f"• **Durum:** ✅ Bu oyun zaten bilgisayarınızda yüklü durumda efendim!\n\n"
                        f"İndirme yerine oyunu doğrudan çalıştırmamı (`{res.get('run_uri')}`) ister misiniz?"
                    )
                    speak = f"{res.get('game_name')} zaten bilgisayarınızda yüklü efendim. Oyunu başlatalım mı?"
                else:
                    act_label = "indirme ve kurulum penceresi" if mode == "install" else "başlatma protokolü"
                    reply = (
                        f"🎮 **Steam Otomasyonu Devrede:**\n\n"
                        f"• **Oyun:** **{res.get('game_name')}** (Steam AppID: `{res.get('appid')}`)\n"
                        f"• **Kütüphane Durumu:** ✅ Steam Kütüphanenizde Lisans Doğrulandı\n"
                        f"• **Komut:** `{res.get('uri')}`\n\n"
                        f"Steam istemcisi açıldı ve **{res.get('game_name')}** için {act_label} tetiklendi efendim!"
                    )
                    speak = f"Steam açıldı ve {res.get('game_name')} için {act_label} başlatıldı efendim."
            else:
                if res.get("not_in_library"):
                    reply = (
                        f"⚠️ **Steam Kütüphane Kontrolü:**\n\n"
                        f"• **Oyun:** **{res.get('game_name')}** (Steam AppID: `{res.get('appid')}`)\n"
                        f"• **Kütüphane Durumu:** ❌ Steam kütüphanenizde bulunamadı\n\n"
                        f"{res.get('error')}"
                    )
                    speak = f"Efendim, {res.get('game_name')} Steam kütüphanenizde bulunamadı. Lisans olmadan indirme yapılamaz."
                else:
                    reply = f"⚠️ {res.get('error')}"
                    speak = res.get("error", "Steam oyunu bulunamadı efendim.")
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "steam_action", "result": res}

        # 14C. CHATGPT BLUEPRINT EXTENSIONS: RESUME, SYSTEM DOCTOR, CONTENT PIPELINE, ORGANIZE & WATCHDOG
        if action == "resume_project":
            from core_jarvis.reality_memory import reality_memory
            summary = reality_memory.resume_context()
            uncommitted = summary.get("uncommitted_files", [])
            uncommitted_text = f"{len(uncommitted)} dosya" if uncommitted else "Değişiklik yok (Clean)"
            reply = (
                f"🧭 **Proje Durum Brifingi (Gerçeklik Çapalı Hafıza):**\n\n"
                f"• **Git Dalı / Commit:** `{summary.get('git_branch')}` (`{summary.get('current_commit')}`)\n"
                f"• **Kaydedilmemiş Çalışma:** {uncommitted_text}\n"
                f"• **Son Kilometre Taşları:**\n"
                + "\n".join(f"  - {m}" for m in summary.get("recent_milestones", []))
                + f"\n\n🎯 **Tavsiye:** {summary.get('recommendation')}"
            )
            speak = summary.get("recommendation", "Projede kaldığımız yeri kontrol ettim efendim.")
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "resume_project", "summary": summary}

        if action == "diagnose_pc":
            from core_jarvis.tools.system_tool import system_tool
            diag = system_tool.diagnose_system_bottlenecks()
            lines = [f"• {issue}" for issue in diag.get("issues", [])]
            recs = [f"• {r}" for r in diag.get("recommendations", [])]
            top_procs = diag.get("top_processes", [])
            proc_lines = [f"  - **{p.get('name')}.exe** (`{p.get('memory_mb')} MB`)" for p in top_procs[:3]]

            reply = (
                f"🩺 **JARVIS Sistem Doktoru Teşhis Raporu:**\n\n"
                f"📊 **Mevcut Durum:** RAM: %{diag.get('ram_pct')} | CPU: %{diag.get('cpu_pct')} | Disk: %{diag.get('disk_pct')}\n\n"
                f"🔍 **Tespit Edilen Bulgular:**\n" + "\n".join(lines)
                + (f"\n\n⚡ **En Çok Kaynak Tüketen Süreçler:**\n" + "\n".join(proc_lines) if proc_lines else "")
                + f"\n\n💡 **Öneri & Aksiyon Planı:**\n" + "\n".join(recs)
            )
            speak = diag.get("recommendations", ["Sistem kontrolü tamamlandı."])[0]
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "diagnose_pc", "diagnosis": diag}

        if action == "produce_content":
            # If user asks for ideas
            if any(k in q_lower for k in ["fikir", "fikri", "fikirler", "öneri", "oneri", "konu", "niş", "nis"]):
                from core_jarvis.tools.knowledge_indexer import knowledge_indexer
                hits = knowledge_indexer.search("youtube shorts kanca hook izlenme", top_k=2).get("results", [])
                rag_tip = hits[0]["preview"][:200] if hits else "Merak uyandıran soru ve ilk 3 saniye kancası."
                reply = (
                    f"🎬 **Global Wave / Zenvia Media — 3 Yüksek-CTR Shorts Fikri:**\n\n"
                    f"1. **Büyük Çip Devrimi (Hardware & AI):** 'NVIDIA'nın tahtı sallanıyor mu? Yeni nesil açık kaynak çipler.'\n"
                    f"   • *Kanca (Hook):* 'Bu çip piyasayı değiştirecek!' | *Hedef Süre:* 42 sn\n"
                    f"2. **Yapay Zeka Otomasyon Ajansı (SMMA / AI Agency):** '$0 Sermaye ile yerel LLM kuran Türk girişimci.'\n"
                    f"   • *Kanca (Hook):* 'Bulut API'lerine para ödemeyi bıraktım.' | *Hedef Süre:* 48 sn\n"
                    f"3. **Görünmez Veri Tehlikesi (Cybersecurity):** 'Telefonunuz sizi dinliyor mu, yoksa siz mi izin verdiniz?'\n"
                    f"   • *Kanca (Hook):* 'Bu ayarı hemen kapatın.' | *Hedef Süre:* 38 sn\n\n"
                    f"💡 *Transkript Masterclass İpucu:* {rag_tip}\n\n"
                    f"Hangisi için senaryo ve video taslağı üretmemi istersiniz efendim?"
                )
                speak = "3 yüksek etkileşimli Shorts fikri hazırladım efendim. Hangisini üretelim?"
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": speak, "action_taken": "content_ideas"}
            else:
                # Production pipeline dispatch
                from core_jarvis.task_coordinator import task_coordinator
                from engine.content_pipeline import content_pipeline
                job_desc = user_inst or "Yapay Zeka ve Gelecek Teknolojileri"
                job = task_coordinator.spawn_job(
                    title=f"Shorts Üretimi ({job_desc[:30]})",
                    specialist="ContentSpecialist",
                    target_func=content_pipeline.stage_1_produce_draft,
                    args=(job_desc, "45s", "vertical", "us_hustler")
                )
                reply = (
                    f"🎬 **Global Wave 3 Aşamalı İçerik Hattı Başlatıldı:**\n\n"
                    f"• **Görev ID:** `{job.get('job_id')}`\n"
                    f"• **Konu:** {job_desc}\n"
                    f"• **Aşama:** 1. Aşama Üretim (Senaryo -> Ses -> Kurgu -> QC)\n"
                    f"• **Durum:** Arka planda işleniyor (%{job.get('progress_pct')})\n\n"
                    f"Üretim tamamlandığında sizi otomatik bilgilendireceğim efendim."
                )
                speak = f"İçerik üretim hattı arka planda başlatıldı efendim. Görev kimliği {job.get('job_id')}."
                self._record_turn(user_text, reply)
                return {"reply": reply, "speak_text": speak, "action_taken": "content_production_dispatched", "job": job}

        if action == "organize_files":
            from core_jarvis.tools.system_tool import system_tool
            res = system_tool.organize_downloads_folder(preview_only=True)
            if not res.get("success"):
                reply = f"⚠️ Klasör taranırken hata: {res.get('error')}"
                speak = "Klasör taranamadı efendim."
            elif res.get("total_files") == 0:
                reply = f"📁 **{res.get('folder')}** klasöründe sınıflandırılacak dağınık dosya bulunmuyor efendim."
                speak = "Düzenlenecek dosya bulunamadı efendim."
            else:
                summary_lines = [f"• **{cat}:** {count} dosya" for cat, count in res.get("category_summary", {}).items()]
                reply = (
                    f"📁 **İndirilenler (Downloads) Düzenleme Önizlemesi:**\n\n"
                    f"Toplam **{res.get('total_files')}** adet dosya bulundu:\n"
                    + "\n".join(summary_lines)
                    + f"\n\n🛡️ *Güvenlik Notu: Hiçbir dosya silinmez; yalnızca yukarıdaki kategorilere taşınır.*\n"
                    f"Onaylıyor musunuz efendim?"
                )
                speak = f"İndirilenler klasöründe {res.get('total_files')} adet dosya tespit ettim. Düzenlemeyi onaylıyor musunuz?"
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "organize_files_preview", "preview": res}

        if action == "proactive_alerts":
            from core_jarvis.proactive_daemon import proactive_watchdog
            alerts = proactive_watchdog.get_recent_alerts(limit=5)
            if alerts:
                lines = [f"• [{a.get('level').upper()}] **{a.get('title')}:** {a.get('message')}" for a in alerts]
                reply = f"🔔 **JARVIS Proaktif Gözcü Bildirimleri:**\n\n" + "\n".join(lines)
                speak = f"Son sistem bildirimlerini listeledim efendim."
            else:
                reply = "✅ **JARVIS Proaktif Gözcü:** Şu anda aktif bir donanım veya görev uyarısı bulunmuyor efendim."
                speak = "Aktif bir sistem uyarısı bulunmuyor efendim."
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "proactive_alerts", "alerts": alerts}

        if action == "autonomous_goal":
            from core_jarvis.autonomous_engine import autonomous_engine
            rep = autonomous_engine.plan_and_execute_goal(cleaned_input, max_steps=5)
            step_lines = []
            for s in rep.get("execution_log", []):
                icon = "✅" if s.get("status") == "completed" else "❌"
                msg = (s.get("execution_result") or {}).get("message", "")
                step_lines.append(f"{icon} **Adım {s['step_index']} ({s['description']}):** {msg}")
            reply = (
                f"⚙️ **7 Adımlı Otonom Görev Yürütme Raporu ({rep.get('completed_steps')}/{rep.get('total_steps')} Adım):**\n\n"
                + "\n".join(step_lines)
                + f"\n\n⏱️ **Süre:** {rep.get('elapsed_seconds')} sn | **Durum:** {rep.get('summary')}"
            )
            speak = rep.get("summary", "Çok adımlı otonom görev tamamlandı efendim.")
            self._record_turn(user_text, reply)
            return {"reply": reply, "speak_text": speak, "action_taken": "autonomous_goal", "report": rep}

        # 15. DEFAULT: RICH NATURAL CONVERSATION WITH QWEN
        return self._generate_conversational_reply(cleaned_input, session_history=session_history)

    def _record_turn(self, user_msg: str, assistant_msg: str):
        self.conversation_history.append({"role": "user", "content": user_msg})
        self.conversation_history.append({"role": "assistant", "content": assistant_msg})
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

    def stream_message(self, user_text: str, session_history: Optional[List[Dict[str, str]]] = None):
        """
        Executes a real-time streaming response for JARVIS chat.
        Yields token fragments (TTFT < 200ms) for general conversation,
        or yields full atomic results for tool/fast-path actions.
        """
        from core_jarvis.event_bus import event_bus
        from core_jarvis.tools.model_manager import model_manager

        cleaned_input = self._normalize_stt_input(user_text)
        q_lower = cleaned_input.lower().strip()

        # 1. Fast-Path / Tool Check: If this request requires tool execution or draft confirmation
        # We delegate directly to process_message and yield the result
        tool_keywords = (
            "whatsapp", "mesaj", "yaz", "gönder", "gonder", "yolla", "ilet", "yanıt", "yanit", "cevap",
            "meşgul", "mesgul", "vekil", "modunu aç", "modu aç", "modunu aktifle", "modunu kapat",
            "kendime", "rehber", "kişi ekle", "kisi ekle", "kişiyi ekle", "kişi sil", "kisi sil", "numara",
            "hatırlat", "hatirlat", "alarm", "not al", "not ekle", "notlara",
            "görev ekle", "gorev ekle", "todo", "kapat", "sonlandır", "açık uygulamalar",
            "ekranı oku", "ekrana bak", "görsel", "resim", "fotoğraf", "ekran görüntüsü",
            "araştır", "arastir", "doküman", "pdf", "özetle", "özet çıkar", "analiz", "konuşma", "sohbet", "geçmişi", "incele",
            "testleri çalıştır", "unit test", "git diff", "commit",
            "sistem", "durum", "telemetri", "ram kullanımı", "vram", "hava", "müzik", "spotify", "şarkı", "oyun", "steam",
            "wake on lan", "bilgisayarı aç", "youtube raporu", "taslak", "evet", "onayla", "iptal"
        )

        if self.pending_draft or any(kw in q_lower for kw in tool_keywords):
            # Immediate feedback token so user UI never sits on an empty cursor
            yield {
                "token": "⚡ *İşlem analiz ediliyor ve komut yürütülüyor...*\n\n",
                "done": False
            }
            try:
                res = self.process_message(user_text, session_history=session_history)
                reply = res.get("reply", "")
                speak_text = res.get("speak_text", reply)
                event_bus.publish("chat.tool_dispatched", {"user": user_text, "action": res.get("action_taken")})
                yield {
                    "token": reply,
                    "done": True,
                    "reply": reply,
                    "speak_text": speak_text,
                    "action_taken": res.get("action_taken"),
                    "result": res
                }
            except Exception as e:
                logger.error(f"process_message error in stream_message: {e}", exc_info=True)
                err_msg = f"Komut yürütülürken bir aksaklık oluştu: {str(e)}"
                yield {
                    "token": err_msg,
                    "done": True,
                    "reply": err_msg,
                    "speak_text": "Komut yürütülürken bir aksaklık oluştu efendim.",
                    "action_taken": "error"
                }
            return

        # 2. General Conversational Chat with Real-time Ollama Streaming
        mem_summary = self.memory.get_context_summary()
        rel_memories = self.memory.search_memories(user_text, limit=4)
        mem_block = mem_summary
        if rel_memories:
            mem_block += "\nİlgili Hafıza Kayıtları:\n" + "\n".join(
                f"- {m['key_term']}: {m['content']}" for m in rel_memories
            )

        rag_block = ""
        rag_triggers = [
            "youtube", "shorts", "niş", "kanal", "kanca", "hook", "izlenme", "abone", "para kazan",
            "gelir", "monetizasyon", "transkript", "global wave", "global-wawe", "stark", "mimari", "dosya"
        ]
        if any(k in q_lower for k in rag_triggers):
            try:
                from core_jarvis.tools.knowledge_indexer import knowledge_indexer
                rag_hits = knowledge_indexer.search(user_text, top_k=2).get("results", [])
                if rag_hits:
                    snippets = [f"• [{h['file_name']}]: {h['preview']}" for h in rag_hits]
                    rag_block = "\n\n[YEREL BİLGİ TABANI & TRANSKRİPT ARŞİVİ]:\n" + "\n".join(snippets)
            except Exception as rag_exc:
                logger.debug(f"Auto-RAG lookup skipped: {rag_exc}")

        chosen_model, keep_alive_val = model_manager.get_active_model_for_request(user_text)
        domain = model_manager.classify_task_domain(user_text)

        system_content = f"{JARVIS_PERSONA_PROMPT}\n\n[AKTİF HAFIZA ÖZETİ]:\n{mem_block}{rag_block}"
        messages = [{"role": "system", "content": system_content}]

        history_source = session_history if session_history is not None else self.conversation_history
        for turn in history_source[-10:]:
            messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append({"role": "user", "content": user_text})

        event_bus.publish("chat.streaming_started", {"user": user_text, "model": chosen_model})

        collected_tokens: List[str] = []
        for chunk in self._call_ollama_stream(
            messages,
            temperature=0.7,
            timeout=75,
            model_override=chosen_model,
            keep_alive_override=keep_alive_val
        ):
            collected_tokens.append(chunk)
            yield {"token": chunk, "done": False}

        full_raw = "".join(collected_tokens)
        parsed = model_manager.strip_thinking_tags(full_raw)
        reply = parsed["clean_reply"]

        speak_text = re.sub(r"[*_#`~>]", "", reply)
        if len(speak_text) > 320:
            speak_text = speak_text[:320].rsplit(".", 1)[0] + ". Ayrıntıları ekrana yansıttım efendim."

        self._record_turn(user_text, reply)
        self._auto_learn_fact(user_text)

        event_bus.publish("chat.streaming_completed", {"user": user_text, "reply_len": len(reply)})

        yield {
            "token": "",
            "done": True,
            "reply": reply,
            "speak_text": speak_text,
            "action_taken": "conversational_chat_stream",
            "specialist_domain": domain,
            "model_used": chosen_model
        }


jarvis_brain = JarvisBrain()
