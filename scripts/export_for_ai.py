#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JARVIS & Global Wave - AI Export & Full Codebase Bundler
Packages the complete codebase, system blueprints, and AI analysis prompts into:
1. 00_AI_ANALIZ_TALIMATI_VE_PROMPT.md (Master Prompt for external AIs)
2. 01_JARVIS_TUM_KODLAR_TEK_DOSYA.md (Complete single-file codebase)
3. 02_JARVIS_CEKIRDEK_SISTEM.md (Core OS, Brain, WhatsApp, Web Cockpit)
4. 03_GLOBAL_WAVE_STUDYO_MOTORU.md (Video Studio, Audio, TTS, LTX)
5. JARVIS_SOURCE_CODE.zip (Clean zip archive for drag-and-drop into Claude/ChatGPT)
"""

import os
import sys
import zipfile
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "JARVIS_AI_ANALYSIS_EXPORT"

IGNORED_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".jarvis_cache",
    ".jarvis_backups",
    "output",
    "models",
    "assets",
    "whatsapp_auth",
    "Transkript",
    "knowledge",
    "JARVIS_AI_ANALYSIS_EXPORT"
}

IGNORED_FILES = {
    "baileys_store.json",
    "whatsapp_inbox.json",
    "contacts.json",
    "contacts.csv",
    "tokens.json",
    "client_secret.json",
    "session_token.key",
    "package-lock.json",
    "app.db",
    "global_wave.db",
    "jarvis_memory.db"
}

ALLOWED_EXTENSIONS = {
    ".py", ".html", ".js", ".bat", ".json", ".md", ".ps1", ".txt"
}


def get_file_category(rel_path: str) -> str:
    if rel_path.startswith("core_jarvis") or rel_path.startswith("web") or rel_path.startswith("scripts") or rel_path in {"run_global_wave.py", "start_jarvis.bat", "connect_whatsapp.bat"}:
        return "core"
    elif rel_path.startswith("engine"):
        return "studio"
    else:
        return "other"


def collect_files():
    collected = []
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for f in files:
            if f.endswith((".pyc", ".mp4", ".wav", ".mp3", ".png", ".jpg", ".db", ".key")):
                continue
            if f in IGNORED_FILES:
                continue
            full_path = Path(root) / f
            rel_path = full_path.relative_to(BASE_DIR).as_posix()
            if full_path.suffix.lower() in ALLOWED_EXTENSIONS or f == "requirements.txt":
                collected.append((full_path, rel_path))
    collected.sort(key=lambda x: x[1])
    return collected


def generate_tree(file_list):
    lines = ["JARVIS / Global Wave Proje Dosya Ağacı:", ""]
    for _, rel in file_list:
        lines.append(f"  ├── {rel}")
    return "\n".join(lines)


def generate_master_prompt():
    return f"""# 🧠 JARVIS AI OPERATING SYSTEM & GLOBAL WAVE - KAPSAMLI ANALİZ İSTEMİ (MASTER PROMPT)

> **Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}
> **Hedef:** Harici Yapay Zeka (Claude 3.5 Sonnet, ChatGPT-4o, Gemini 1.5 Pro vb.)
> **İnceleme Kapsamı:** JARVIS AI Operating System (Yerel Kişisel Yapay Zeka İşletim Sistemi) & Global Wave Otonom İçerik Motoru

---

## 💻 1. Sistem ve Donanım Mimarisi
Bu proje, kullanıcının (**Mücahit Hilmi**) kişisel bilgisayarında çalışan, hem otonom bir **Yapay Zeka İşletim Sistemi (JARVIS)** hem de **Otonom YouTube Shorts Stüdyosu (Global Wave)** olarak görev yapan yerel bir ekosistemdir.

- **İşlemci (CPU):** Intel Core i5-14400F
- **Ekran Kartı (GPU):** AMD Radeon RX 9060 XT (16 GB VRAM)
- **Sistem Belleği (RAM):** 16 GB DDR5
- **İşletim Sistemi:** Windows 11 + WSL2 (Linux)
- **Yerel Model Altyapısı (Ollama God-Mode):**
  - **Birincil Beyin (Hızlı Türkçe/İcra):** `qwen2.5:7b-instruct-q4_K_M`
  - **Yazılım & Kodlama Uzmanı:** `qwen2.5-coder:14b`
  - **Derin Muhakeme & Analiz:** `deepseek-r1:14b`
  - **Görüntü / Multimodal:** `llama3.2-vision:11b`
  - **Stratejik Planlama:** `phi4:14b`

---

## 🏛️ 2. Temel Modüller ve İşleyiş Haritası

1. **`core_jarvis/jarvis_brain.py` (Yapay Zeka Beyni & Niyet Yönlendirici):**
   - Kullanıcının sesli veya yazılı girdilerini analiz eder.
   - 0-shot kural tabanlı + Few-shot LLM hibrit niyet sınıflandırması (`_route_intent`) yapar.
   - Kodlama ve derin matematik isteklerinde yapay zekayı 15 dakikalık "Sticky Mode" ile 14B modellere esnetir.
   - Kullanıcının doğrudan emirlerini ve tercihlerini (`bundan sonra...`, `şunu unutma...`) otomatik algılayıp `memory_graph.py` içine kalıcı epizodik kural olarak işler.

2. **`core_jarvis/whatsapp_daemon.py` (Baileys v7 Entegrasyonu & Meşgul Modu):**
   - Node.js tabanlı Baileys v7 soket köprüsü ile doğrudan kullanıcının gerçek WhatsApp oturumuna bağlanır.
   - **LID <-> Phone Çözümleme:** WhatsApp v7'nin gizli LID kimliklerini arka planda telefon numaralarıyla eşleştirir.
   - **Meşgul Modu (AI Delegate):** Kullanıcı meşgulken gelen kişisel mesajlara JARVIS kendi kimliğiyle ("Merhabalar, ben Mücahit Hilmi'nin yapay zeka asistanı JARVIS...") cevap verir. WhatsApp Bültenleri (`@newsletter`), kanallar ve kalabalık gruplar otomatik cevaplama dışı bırakılır.
   - **Kişisel Sahip Oturumu:** Sahip kendi kendine mesaj attığında (`Kendime Not`), JARVIS bunu doğrudan komut olarak işler ve sistem telemetrisi / ajanda yönetimi yapar.

3. **`core_jarvis/personal_assistant.py` & `memory_graph.py`:**
   - Ajanda, notlar, hatırlatıcılar ve ilişkiler ağını (`contacts.json`, `personal_agenda.json`) yönetir.

4. **`core_jarvis/proactive_daemon.py` & `task_coordinator.py`:**
   - Arka planda donanım sağlığını, RAM/VRAM taşmasını, Telegram yönetici hattını ve otonom görev zincirlerini denetler.

5. **`web/` (Lüks Cam Arayüz & FastAPI Sunucusu):**
   - `web/server.py` ve modüler yönlendiriciler (`web/routers/`).
   - `web/templates/jarvis_luxury.html`: Sayın Hilmi için tasarlanmış fütüristik, cam efektli (glassmorphic), karanlık mod kokpit.
   - Token streaming (SSE), gerçek zamanlı ses sentezi ve WhatsApp mesajlaşma merkezi.

6. **`engine/` (Global Wave Otonom YouTube İçerik Stüdyosu):**
   - Niche/trend analizi, senaryo yazımı (`script_engine.py`), Kokoro/Edge-TTS seslendirme (`voice_engine.py`), Whisper altyazı senkronizasyonu (`subtitle_whisper.py`), LTX video üretimi (`video_ltx.py`) ve YouTube otomatik yükleme (`uploader_youtube.py`).

---

## 🎯 3. Başka Bir Yapay Zekadan (Sizden) İstenen Görevler

Lütfen ekte veya aşağıda sunulan kod tabanını baştan sona, satır satır inceleyiniz ve aşağıdaki başlıklarda kapsamlı, acımasız ve yapıcı bir **360 Derece Sistem Değerlendirme Raporu** hazırlayınız:

1. **Mimari Kalite ve Kod Standartları:**
   - Kod yapısı ne kadar modüler ve sürdürülebilir?
   - Kod tekrarı (DRY ilkesi) veya spagetti tasarım kalıntıları var mı?
   - Hata yakalama (`try/except`) ve loglama mimarisi profesyonel standartlarda mı?

2. **Gizli Hatalar, Yarış Koşulları (Race Conditions) ve Kilitlenmeler:**
   - Asenkron FastAPI ile çoklu iş parçacığı (`threading.Thread`, `RLock`, SQLite, JSON disk I/O) arasında olası yarış koşulları, kilitlenmeler veya bellek sızıntıları var mı?
   - Baileys soket iletişimi veya SQLite bağlantılarında kaynak tükenmesi riski mevcut mu?

3. **Güvenlik ve İzin Yönetimi (Security & Guardrails):**
   - `permission_guard.py`, `owner_session.py` ve yerel yetkilendirme katmanı yetkisiz erişimlere veya prompt injection saldırılarına karşı ne kadar dayanıklı?
   - WhatsApp üzerinden dışarıdan gelen bir mesajın sistemi manipüle etme riski var mı?

4. **Performans ve Kaynak Optimizasyonu:**
   - 16GB VRAM (RX 9060 XT) ve 16GB RAM üzerinde yerel modeller çalışırken bellek taşması nasıl önlenir?
   - Kodda fark edilen mikro optimizasyon fırsatları nelerdir?

5. **Gelecek Vizyonu ve Özellik Önerileri (Level Up):**
   - JARVIS'e gerçek bir Jarvis hissi katacak, modern otonom ajan (Agentic Workflow, MCP - Model Context Protocol, Vision Tooling vb.) seviyesinde hangi yeni özellikler ve entegrasyonlar kazandırılmalıdır?
   - Sistemin en zayıf halkası nedir ve ilk olarak nereye odaklanılmalıdır?

---
*Kod tabanı aşağıda tam dosya yollarıyla birlikte sunulmuştur.*
"""


def bundle_codebase(file_list, output_file: Path, filter_category: str = None):
    with open(output_file, "w", encoding="utf-8") as out:
        out.write(generate_master_prompt())
        out.write("\n\n" + "="*80 + "\n")
        out.write("PROJE DOSYA AĞACI\n")
        out.write("="*80 + "\n\n")
        out.write("```\n")
        out.write(generate_tree(file_list))
        out.write("\n```\n\n")
        out.write("="*80 + "\n")
        out.write("KAYNAK KODLARIN TAMAMI (A'DAN Z'YE TÜM DOSYALAR)\n")
        out.write("="*80 + "\n\n")

        count = 0
        for full_p, rel_p in file_list:
            cat = get_file_category(rel_p)
            if filter_category and filter_category != "all":
                if filter_category == "core" and cat not in {"core", "other"}:
                    continue
                elif filter_category == "studio" and cat not in {"studio", "other"}:
                    continue

            try:
                content = full_p.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                content = f"// Dosya okunamadı: {e}"

            lang = "python"
            if rel_p.endswith(".html"):
                lang = "html"
            elif rel_p.endswith(".js"):
                lang = "javascript"
            elif rel_p.endswith(".json"):
                lang = "json"
            elif rel_p.endswith((".bat", ".cmd")):
                lang = "bat"
            elif rel_p.endswith(".ps1"):
                lang = "powershell"
            elif rel_p.endswith(".md"):
                lang = "markdown"

            out.write(f"### 📄 DOSYA: `{rel_p}`\n")
            out.write(f"*Boyut: {full_p.stat().st_size:,} bayt | Satır: {len(content.splitlines()):,}*\n\n")
            out.write(f"```{lang}\n")
            out.write(content)
            if not content.endswith("\n"):
                out.write("\n")
            out.write("```\n\n" + "-"*60 + "\n\n")
            count += 1

    return count


def create_clean_zip(file_list, zip_path: Path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for full_p, rel_p in file_list:
            zf.write(full_p, arcname=rel_p)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    file_list = collect_files()
    print(f"[Export] Toplam {len(file_list)} kaynak kod ve konfigürasyon dosyası toplandı.")

    # 1. Master Prompt
    prompt_file = OUTPUT_DIR / "00_AI_ANALIZ_TALIMATI_VE_PROMPT.md"
    prompt_file.write_text(generate_master_prompt(), encoding="utf-8")
    print(f"[Export] Master Prompt oluşturuldu: {prompt_file.name}")

    # 2. Complete Codebase Bundle (Single File)
    single_file = OUTPUT_DIR / "01_JARVIS_TUM_KODLAR_TEK_DOSYA.md"
    c_single = bundle_codebase(file_list, single_file, filter_category="all")
    print(f"[Export] Tek parça tüm kodlar paketi oluşturuldu: {single_file.name} ({c_single} dosya, {single_file.stat().st_size / (1024*1024):.2f} MB)")

    # 3. Core Split (For Claude / GPT-4o 200k context)
    core_file = OUTPUT_DIR / "02_JARVIS_CEKIRDEK_SISTEM.md"
    c_core = bundle_codebase(file_list, core_file, filter_category="core")
    print(f"[Export] Çekirdek sistem paketi oluşturuldu: {core_file.name} ({c_core} dosya, {core_file.stat().st_size / (1024*1024):.2f} MB)")

    # 4. Studio Split
    studio_file = OUTPUT_DIR / "03_GLOBAL_WAVE_STUDYO_MOTORU.md"
    c_studio = bundle_codebase(file_list, studio_file, filter_category="studio")
    print(f"[Export] Stüdyo motoru paketi oluşturuldu: {studio_file.name} ({c_studio} dosya, {studio_file.stat().st_size / (1024*1024):.2f} MB)")

    # 5. Clean Zip Archive
    zip_file = OUTPUT_DIR / "JARVIS_SOURCE_CODE.zip"
    create_clean_zip(file_list, zip_file)
    print(f"[Export] Temiz Zip arşivi oluşturuldu: {zip_file.name} ({zip_file.stat().st_size / (1024*1024):.2f} MB)")

    # Also copy the export folder to Desktop for ultra-easy access
    desktop_export = Path("/mnt/c/Users/unalm/OneDrive/Masaüstü/JARVIS_AI_ANALYSIS_EXPORT")
    try:
        import shutil
        if desktop_export.exists():
            shutil.rmtree(desktop_export)
        shutil.copytree(OUTPUT_DIR, desktop_export)
        print(f"[Export] Masaüstüne kopyalandı: {desktop_export}")
    except Exception as e:
        print(f"[Export Warning] Masaüstüne kopyalanamadı: {e}")

    print("\n[TAMAMLANDI] Yapay zekaya verilecek tüm analiz dosyaları hazır!")


if __name__ == "__main__":
    main()
