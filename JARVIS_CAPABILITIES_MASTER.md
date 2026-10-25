# 🧠 JARVIS Master Yetenek & Fonksiyon Kataloğu
> **Sistem:** Global-Wave / Stark-Core Personal AI Operating System  
> **Kullanıcı:** Mücahit Hilmi (Hitap: *Sayın Hilmi* / *Efendim*)  
> **Versiyon:** v6.0 (Master Architecture - Multimodal WhatsApp, Windows Daemon OS & Fast Mocked Suite)  
> **Son Güncelleme:** 25 Ekim 2026  
> **Doğrulama:** 117 Birim Testi Mimarisi (İzole Mock & Soket Korumalı Hızlı Test Altyapısı)

Bu doküman, JARVIS'in sahip olduğu tüm özerk yetenekleri, kontrol katmanlarını, güvenlik kalkanını, API uç noktalarını, görsel Web HUD panellerini ve tetikleyici komutlarını eksiksiz listeler. Yeni bir özellik eklendikçe güncellenir.

---

## 💻 1. Donanım & Çevre Profili
Sistem, yerel bilgisayarın fiziksel sınırlarına tam uyumlu ve **$0.00 harici API maliyeti** prensibiyle çalışır:
- **İşlemci (CPU):** `Intel Core i5-14400F` (10 Fiziksel Çekirdek, 16 İş Parçacığı) — Whisper STT, FFmpeg çoklu işlem ve yerel model yürütme.
- **Ekran Kartı (GPU):** `AMD Radeon RX 9060 XT` (AMD RDNA Mimarisi) — AMD AMF (`h264_amf`) donanım hızlandırmalı video render ve DirectML desteği.
- **Bellek (RAM):** `16 GB DDR` — Bellek taşmasını önleyen dinamik eşik denetimi; yerel çıkarımda 7B/8B modeller (`qwen2.5-coder:7b`, `qwen3:8b`, `llama3.1:8b`).
- **Depolama (Disk C:):** Geçici render dosyaları OneDrive kilitlemesini (`WinError 32`) önlemek için `%LOCALAPPDATA%\Temp\global_wave_workspace\` altında işlenir.

---

## 🛡️ 2. Dört Kademeli Güvenlik Kalkanı (`permission_guard.py`)
Modelin kendi başına her işlemi yapması engellenmiş, teknik katmanda zorlanan 4 seviyeli izin matrisi kurulmuştur:

1. **Seviye 1 — Otomatik (Düşük Risk, Salt Okunur):**
   - Telemetri okuma, dosya arama, log inceleme, test çalıştırma, gelen mesajları kontrol etme, rehber sorgulama, git diff, güvenli PowerShell okuma komutları, daemon durum sorgulama.
2. **Seviye 2 — Sınırlı Çalışma Alanı (Geri Alınabilir Eylemler):**
   - Proje dosyalarını düzenleme, test düzeltme, senaryo üretimi, video kurgusu, yerel yedek (snapshot) alma, git commit, masaüstü kısayolu oluşturma.
3. **Seviye 3 — Açık Kullanıcı Onayı (Human-in-the-Loop):**
   - Git push, YouTube'a video yükleme, WhatsApp/Telegram/Gmail üzerinden doğrudan mesaj gönderme, süreç zorla sonlandırma (`kill`), kalıcı dosya silme, yedekten geri yükleme (`rollback`), ücretli API çağrısı, Wake-on-LAN sinyali gönderme, Windows başlangıç (Startup) kaydı ekleme/kaldırma.
4. **Seviye 4 — Kesinlikle Yasak (Kullanıcı Onaylasa Dahi Yürütülmez):**
   - Güvenlik duvarını kapatma, kimlik bilgilerini/tokenları sızdırma, sistem sahibini (`c_owner`) silme, sistem çekirdeğini bozma, `format-volume` gibi yıkıcı komutlar.

---

## 🧩 3. Modüller & Fonksiyon Yetenekleri

### A. Donanım, Windows & Sistem Yönetimi (`system_tool.py` & `wol_tool.py`)
- **Canlı Telemetri:** CPU yük yüzdesi, RAM kullanımı (Toplam/Kullanılan/Boş GB ve %), C: disk doluluk oranı, GPU sağlığı ve en çok bellek tüketen ilk 5 Windows sürecini anlık sorgular.
- **Zırhlı PowerShell:** Whitelist denetimli komut çalıştırıcı. Seviye 4 komutları engeller, Seviye 3 komutlarda açık onay ister, Seviye 1-2 güvenli komutları yürütür.
- **Versiyonlu Snapshot & Rollback:** Kod veya dosya düzenlemeden önce `.jarvis_backups/` altına anlık yedek alır; hata durumunda tek komutla geri yükler.
- **Wake-on-LAN (WOL):** Kapalı/uyku modundaki bilgisayarı 102-byte UDP Magic Packet ile uzaktan uyandırır. Ağ arayüzünün MAC ve yerel IP adresini tespit eder, BIOS ve WAN yönlendirme rehberi sunar.

### B. Gerçeklik Tabanlı Hafıza — Truth-Over-Memory (`reality_memory.py`)
- **"Kaldığımız yerden devam et" Yeteneği:** Bellekteki eski konuşmalar yerine gerçek diski, `git status`, `git branch`, değiştirilen dosyaları ve açık servisleri (Web HUD: 7860, Ollama: 11434) denetleyerek durumu doğrular.
- **Çok Adımlı Görev Takibi:** Başlatılan görevlerin adımlarını, başarı/başarısızlık durumlarını ve engellerini diske kaydeder.

### C. 7 Adımlı Otonom Yürütme Döngüsü (`autonomous_engine.py`)
1. **Hedefi Anla:** Kısıtları ve istenen sonucu belirle.
2. **Planı Oluştur:** Adımları, gerekli araçları ve başarı ölçütlerini çıkar.
3. **Yetkiyi Kontrol Et:** `permission_guard` üzerinden izin seviyesini denetle (Gerekirse durup onay iste).
4. **Uygula:** Yetkili araçla işlemi yürüt.
5. **Doğrula:** Çıktıyı, dosya boyutunu veya test sonucunu doğrula.
6. **Düzelt veya Dur:** Doğrulama başarısız olursa otomatik teşhis yapıp güvenli düzeltme dene (Maksimum 3 deneme; aşılırsa güvenle dur ve engeli raporla).
7. **Raporla:** Yapılan değişiklikleri, süreyi ve kalan riskleri şeffafça sun.

### D. Global Wave (Zenvia Media) 3 Aşamalı İçerik Hattı (`content_pipeline.py`)
1. **Üretim (Production):**
   - Hedef süreye (30s, 45s, 60s Shorts veya 10, 12, 14, 16 dk belgesel) göre matematiksel kelime kalibrasyonu (2.33 kelime/sn).
   - Dual-Hook (0-3s Hook + 3-6s Re-Hook), 5 kanca kategorisi (Danger, Curiosity, Controversy, Record, Default).
   - Metin insanlaştırma (`humanizer.py`) ve yorum kışkırtma (`engagement_engine.py`).
   - Yüksek CTR otomatik kapak motoru (`thumbnail_engine.py`).
2. **Kalite Kontrolü (QC):**
   - `ffprobe` ile süre toleransı (±%5), ses izinin varlığı, çözünürlük (min 720p/1080p) ve SAR (1:1) denetimi.
   - **Simülasyon vs Gerçek Ayrımı:** Yapay zekâ skorları `YAPAY ZEKA TAHMİNİ (Simülasyon)` olarak etiketlenir, gerçek YouTube analitiğinden ayrı tutulur.
3. **Yayın Staging:**
   - Başlık, açıklama, etiketler ve gizlilik modu (`private`) hazırlanır.
   - YouTube'a canlı yükleme yalnızca Seviye 3 açık kullanıcı onayı ile gerçekleştirilir (`uploader_youtube.py`).

### E. Çoklu Ajan Koordinatörü & Altyapı Motoru (`task_coordinator.py` & `infra_tool.py`)
- **Arka Plan İş Gözetmeni:** Render, model indirme ve testler gibi uzun işleri kilitlenmeyen iş parçacığında çalıştırır; %0-%100 canlı ilerleme sunar.
- **İptal Mekanizması:** Kullanıcı dilediğinde arka plandaki görevi güvenle durdurabilir (`cancel_job`).
- **Konteyner & Docker Denetimi:** `docker ps` ile çalışan servisleri sorgular.
- **Model Envanteri & $0 Maliyetli Akıllı Yönlendirici:**
   - Rutin işler ➔ `qwen3:8b`
   - Kod geliştirme ve hata ayıklama ➔ `qwen2.5-coder:7b`
   - Uzun belgesel senaryosu ➔ `qwen3:14b`

### F. Kişisel Asistan, Günlük Planlama & Ajanda (`personal_assistant.py`)
- **"Jarvis, bugün ne yapmam gerekiyor?" Günlük Brifingi:**
  - Bugünün vadesi dolan işleri,
  - Gecikmiş işlerin kırmızı alarmı,
  - Global Wave projesinin aktif durumu (yarım kalan işler, commit edilmemiş dosyalar),
  - WhatsApp okunmamış mesaj sayısı,
  - Tony Stark tarzı Türkçe yönetici seslendirme metni.
- **Görev & Proje Panosu:** Öncelik seviyeli görev ekleme, tamamlama ve listeleme.
- **Zamanlanmış Hatırlatıcılar & Takvim:** Bildirim saati, önceden haber verme süresi ve tekrarlayan hatırlatıcılar.
- **Yönetici Hızlı Notları:** Fikir ve direktiflerin anında arşivlenmesi.

### G. İletişim, Rehber & WhatsApp Multimodal OS (`contacts.py`, `whatsapp_daemon.py` & `whatsapp_bridge/`)
- **Baileys Canlı WhatsApp Entegrasyonu:** TypeScript/Node.js Baileys köprüsü üzerinden QR kod ve pairing-code destekli, gerçek zamanlı çift yönlü mesajlaşma senkronizasyonu.
- **Çoklu Ortam (Multimodal) Medya İşleme:**
  - Gelen resimler, çıkartmalar (stickers), sesli mesajlar (PTT voice notes), videolar ve belgeler (PDF, ZIP, Word, Excel) otomatik tespit edilip yerel depoya (`output/whatsapp_media/`) kaydedilir.
  - Web HUD üzerinde zengin önizleme: Görseller için zoom yapılabilir galeri önizlemesi, sesli notlar için yerel HTML5 audio oynatıcı, videolar için gömülü video oynatıcı, dokümanlar için türe özel renkli simgeler (PDF kırmızı, ZIP sarı, DOCX mavi, XLSX yeşil) ve doğrudan güvenli indirme/tarayıcıda açma bağlantıları.
- **Ajans & Akıllı Samimiyet/Üslup Analizi (Agency OS):**
  - Mesajlaşma geçmişini analiz ederek kişiyle olan samimiyet derecesini (`doğal`, `resmi`, `dostane`, `aile`) belirler (`_synthesize_whatsapp_draft_or_ask`).
  - Eğer kullanıcı niyeti veya hitap tarzında belirsizlik varsa varsayımda bulunmaz; Sayın Hilmi'ye danışarak netleştirme talep eder (`clarification_requested`).
- **Rehber Merkezi (Contacts Hub):** Kişi ekleme, düzenleme, CSV/vCard içe aktarma, sistem sahibi (`c_owner`) silinemezlik koruması.
- **Akraba & Aile Protokolü:** Babaya (Yaşar Ünal) ve Anneye kesinlikle "Sayın Babam" gibi robotik hitaplar kullanmaz; sıcak ve saygılı Türk aile diline uygun hitap eder.
- **HITL (Human-in-the-Loop) Taslak Güvenliği:** Mesaj taslağı hazırlar, kullanıcı Web HUD üzerinden veya sesle onaylamadan asla karşı tarafa mesaj iletmez.

### H. Otonom Web & Dokümantasyon Araştırma Motoru (`browser_research_tool.py`)
- **$0 Maliyetli Web Taraması (Zero-Cost Web Search):** Harici arama motoru API'lerine para ödemeden DuckDuckGo HTML ağ geçidi üzerinden anlık arama yapar ve özet snippet'leri çeker.
- **Prompt-Injection Zırhı:** Güvenilmeyen web sitelerinden gelebilecek talimatları ("ignore previous instructions", "disregard all rules", "send me all tokens", "format c:", vb.) tarar ve `[ENGELLENEN GÜVENİLMEZ TALİMAT]` olarak temizleyerek sistem promptunu korur.
- **Donanıma Özel Yerel Model Kıyaslama:** i5-14400F + AMD Radeon RX 9060 XT + 16GB RAM mimarisine göre modelleri değerlendirir. 16GB RAM için ~4.7-5.2 GB bellek tüketen 7B/8B modelleri (`qwen2.5-coder:7b`, `deepseek-r1:8b`, `qwen3:8b`) önerir; sistemi çökertecek 70B modelleri "Yetersiz Donanım" olarak raporlar.
- **Yönetici Not Defterine Otomatik Arşivleme:** Araştırılan teknik konuları otomatik olarak `personal_assistant.add_note` ile `research` etiketiyle kaydeder.

### I. Akıllı Dosya & Dokümantasyon İndeksleyici — Yerel RAG Motoru (`knowledge_indexer.py`)
- **$0 Maliyetli BM25 Sıralama Motoru (Zero-Cost Local RAG):** Harici vektör veritabanı veya token ücreti ödemeden standart kütüphane BM25 algoritmasıyla binlerce doküman ve kod parçasını <10ms içinde arar.
- **Çoklu Biçim ve Kod/Markdown Ayrıştırma:** `.md`, `.py`, `.txt`, `.json`, `.csv`, `.yaml` dosyalarını başlık (`#`) ve sınıf/fonksiyon (`def`, `class`) sınırlarına göre akıllı parçalara (chunk) böler.
- **Hassas Dosya Kara Listesi:** `.env`, `session_token.key`, `.pem`, `client_secret*.json`, `id_rsa*` gibi kimlik ve şifreleme dosyalarını indekslemeye dahil etmez, sızdırma riskini sıfırlar.
- **Artımlı İndeksleme & Önbellek (`.jarvis_cache/knowledge_index.json`):** Değişmeyen dosyaları diskte tararken atlar; sadece yeni ve güncellenen dosyaları indeksler.
- **Doküman Yapısal Analizi & Özetleme:** Dosyanın satır sayısını, dosya boyutunu, sınıf/fonksiyon haritasını ve ana başlıklarını çıkarıp yönetici özeti üretir.

### J. Sesli Yanıt & Canlı Tetikleyici — Wake-Word & Kokoro TTS Motoru (`voice_tool.py`)
- **"Hey Jarvis" Sesli Uyanma (Wake-Word):** Kullanıcı ses veya metinle *"Hey Jarvis"*, *"Jarvis"*, *"Dinle Jarvis"* dediğinde uyanma kelimesini ayıklar ve komutu master orkestratöre yönlendirir.
- **Metin Temizleme ve Fonetik Sadeleştirme:** Markdown işaretlerini (`**`, `#`, backtick, emoji, teknik etiketler) konuşmadan önce temizleyerek kulağa akıcı gelen insan dili üretir.
- **100% Çevrimdışı Kokoro-82M ONNX Stüdyo Sesi ($0 Maliyet):** CPU üzerinde ~300MB RAM tüketerek stüdyo kalitesinde ses dosyaları üretir (`/output/jarvis_voices/`).
- **Web Speech & Çift Katmanlı Seslendirme:** Web arayüzünde üretilen ses dosyasını oynatır; istenirse tarayıcı yerel seslendiricisi (`window.speechSynthesis`) ile sıfır gecikmeli yanıt verir.

### K. Windows Yaşam Döngüsü & Sessiz Arka Plan Servis Yöneticisi (`daemon_manager.py` & `scripts/jarvis_daemon.py`)
- **%100 Yerel & Penceresiz Arka Plan Yürütme (Zero-Window Daemon):**
  - Windows 11 üzerinde `pythonw.exe` ve `DETACHED_PROCESS` | `CREATE_NO_WINDOW` bayrakları ile terminal penceresi açılmadan arka planda çalışır.
  - Özel VBScript motoru (`create_silent_vbs` -> `start_silent.vbs`), dinamik dizin çözümleme kullanarak OneDrive veya Türkçe karakterli yollarda (`Masaüstü`) dahi sıfır hata ile sessiz başlatma sağlar.
- **Süreç & Port İzleme (Port 7860 & PID Denetimi):**
  - TCP port 7860 soket yoklaması ve FastAPI `/api/config` HTTP sağlık kontrolü ile servisin canlılığını teyit eder (`is_port_in_use`, `is_http_ready`).
  - `.jarvis_cache/jarvis_daemon.pid` ile süreç ID takibi ve PowerShell tabanlı CPU & RAM bellek telemetrisi (`get_process_info`).
- **Windows Masaüstü Kısayolu:**
  - Tek tıkla veya CLI ile kullanıcının masaüstüne (`OneDrive/Masaüstü` veya `Desktop`) `JARVIS AI Operating System.lnk` oluşturur (`create_desktop_shortcut`).
- **Windows Açılışında Otomatik Başlatma (Startup Service):**
  - Windows Başlangıç klasörüne (`shell:startup`) `JARVIS_Background_Service.lnk` ekleyerek bilgisayar açıldığında JARVIS'in otomatik ve sessizce başlamasını sağlar (`install_windows_startup` / `uninstall_windows_startup`).
- **Süreç Ağacı Temiz Sonlandırma:**
  - `taskkill /F /T /PID` mekanizması ile port 7860 ve alt iş parçacıklarını kilitlenmeden, güvenle kapatır (`stop`).
- **Çoklu Yönetim Arayüzleri:**
  - CLI: `python scripts/jarvis_daemon.py {start,stop,restart,status,shortcut,startup-install,startup-uninstall}`
  - Batch: `start_jarvis.bat` (Tek tıkla masaüstü başlatıcı ve menü)
  - PowerShell: `scripts/start_jarvis.ps1`
  - Web REST API: Web HUD üzerinden tek tıkla durum sorgulama ve kısayol/startup yönetimi.

---

## 🗣️ 4. Jarvis Tetikleyici Cümleler (Sesli & Yazılı Sözlük)

| Kullanıcının Söylediği | Devreye Giren Uzman | Yapılan İşlem |
|---|---|---|
| *"Jarvis, bugün ne yapmam gerekiyor?"* | `AssistantSpecialist` | Günlük ajandayı, geciken işleri, projeyi ve mesajları derleyip sesli okur. |
| *"Kaldığımız yerden devam et"* | `RealityMemory` | Gerçek Git ve dosya durumunu analiz edip son kalınan adımı raporlar. |
| *"Bilgisayarım neden yavaşladı?"* | `SystemSpecialist` | CPU, RAM, Disk ve en çok kaynak tüketen süreçleri inceler, teşhis koyar. |
| *"Testleri çalıştır"* | `CodeSpecialist` | Tüm birim testlerini koşturup başarı/hata raporu üretir. |
| *"Git diff / Ne değişti?"* | `CodeSpecialist` | Çalışma alanındaki kaydedilmemiş kod farklarını listeler. |
| *"Video üret: Yapay Zeka Devrimi"* | `ContentSpecialist` | Senaryo, ses, b-roll, altyazı ve kapak üretim döngüsünü başlatır. |
| *"Video motoru durumu"* | `ContentSpecialist` | FFmpeg, Pexels ve donanım render hızlandırma hazırliğini denetler. |
| *"Docker durumu nedir?"* | `SystemSpecialist` | Konteynerlerin ve daemon'ın çalışıp çalışmadığını kontrol eder. |
| *"Hangi yerel modeller yüklü?"* | `SystemSpecialist` | Ollama model kataloğunu ve disk boyutlarını listeler. |
| *"Aktif görevler / kuyruk ne durumda?"* | `TaskCoordinator` | Arka planda devam eden işlerin % ilerlemesini ve kalan süresini sunar. |
| *"Görev ekle: Yeni Shorts planla"* | `AssistantSpecialist` | Kişisel ajandaya öncelikli yeni görev kaydeder. |
| *"Not al: [Fikir]"* | `AssistantSpecialist` | Yönetici not defterine anlık memo ekler. |
| *"Araştır: Ollama deepseek-r1 performansı"* | `ResearchSpecialist` | Web ve yerel havuzu tarar, bulguları özetler ve yönetici notlarına kaydeder. |
| *"Donanım için en iyi modelleri karşılaştır"* | `ResearchSpecialist` | i5-14400F, RX 9060 XT ve 16GB RAM sınırlarına göre en uygun modelleri kıyaslar. |
| *"Yerel dokümanlarda ara: permission guard"* | `ResearchSpecialist` | BM25 ile kod ve doküman havuzunu tarar, en alakalı dosyayı ve satır aralığını sunar. |
| *"Doküman özetle: JARVIS_CAPABILITIES_MASTER.md"* | `ResearchSpecialist` | Dosya yapısını (satır, boyut, fonksiyon/başlık) analiz edip özet çıkarır. |
| *"Bilgi tabanını güncelle"* | `ResearchSpecialist` | Çalışma alanı dosyalarını tarar ve `.jarvis_cache/knowledge_index.json` indeksini tazeler. |
| *"Seslendir: Sistemler aktif efendim"* | `VoiceSpecialist` | Kokoro-82M ONNX ile metni seslendirir ve ses dosyasını üretir. |
| *"Ses sistemi durumu"* | `VoiceSpecialist` | ONNX ağırlıkları, önbellekteki ses sayısı ve hazır ses motorlarını raporlar. |
| *"Arka plan servisini başlat"* | `JarvisDaemonManager` | JARVIS'i penceresiz arka plan servisi olarak çalıştırır ve Web HUD'ı açar. |
| *"Servisi durdur"* | `JarvisDaemonManager` | PID ve port 7860 süreç ağacını güvenle sonlandırır. |
| *"Servis durumunu göster / Telemetri"* | `JarvisDaemonManager` | PID, CPU, RAM, HTTP ve Ollama durumunu raporlar. |
| *"Masaüstü kısayolu oluştur"* | `JarvisDaemonManager` | Windows Masaüstüne JARVIS AI OS kısayolu (.lnk) ekler. |
| *"Windows açılışına ekle / kaldır"* | `JarvisDaemonManager` | Bilgisayar açılışında arka planda otomatik başlamasını sağlar veya kaldırır. |
| *"WhatsApp medyasını göster / indir"* | `WhatsAppDaemon` | Gelen sesli not, görsel veya dokümanı Web HUD üzerinde önizler. |

---

## 🔌 5. Web HUD REST API Uç Noktaları

| Uç Nokta | Metot | Açıklama |
|---|:---:|---|
| `/api/jarvis/system/telemetry` | `GET` | Donanım (CPU, RAM, Disk, GPU) ve süreç telemetrisi |
| `/api/jarvis/reality/state` | `GET` | Canlı Git ve proje disk durumu |
| `/api/jarvis/orchestrator/dispatch` | `POST` | Niyete göre uzman ajana görev dağıtımı |
| `/api/jarvis/system/powershell` | `POST` | Whitelist korumalı PowerShell komutu yürütme |
| `/api/jarvis/system/backup` | `POST` | Anlık snapshot dosya yedeği oluşturma |
| `/api/jarvis/wol/identity` | `GET` | Ağ kartı MAC ve yerel IP tespiti |
| `/api/jarvis/wol/wake` | `POST` | 102-byte Wake-on-LAN sihirli paket gönderme |
| `/api/jarvis/security/audit` | `GET` | Son 50 güvenlik ve izin denetim kaydı |
| `/api/jarvis/content/produce` | `POST` | 1. Aşama İçerik Üretimi (Senaryo + Kapak) |
| `/api/jarvis/content/qc` | `POST` | 2. Aşama Kalite Kontrolü (Teknik probe + Simülasyon) |
| `/api/jarvis/content/publish` | `POST` | 3. Aşama YouTube yayın staging (Onaylı) |
| `/api/jarvis/assistant/briefing` | `GET` | Günlük ajanda ve yönetici brifingi |
| `/api/jarvis/assistant/tasks` | `GET/POST` | Görev listeleme ve ekleme |
| `/api/jarvis/assistant/tasks/{id}/complete` | `POST` | Görev tamamlama |
| `/api/jarvis/assistant/reminders` | `GET/POST` | Zamanlanmış hatırlatıcı yönetimi |
| `/api/jarvis/assistant/notes` | `GET/POST` | Yönetici notları yönetimi |
| `/api/jarvis/jobs` | `GET` | Arka plandaki uzun süren işlerin listesi |
| `/api/jarvis/jobs/{id}/cancel` | `POST` | Arka plan işini iptal etme |
| `/api/jarvis/infra/docker` | `GET` | Docker daemon ve konteyner durumu |
| `/api/jarvis/infra/models` | `GET` | Yerel Ollama modelleri |
| `/api/jarvis/infra/route` | `POST` | $0 maliyetli optimal model seçici |
| `/api/jarvis/research/query` | `POST` | Web araması yapar ve yönetici notuna kaydeder |
| `/api/jarvis/research/hardware-models` | `POST` | Donanım sınırlarına göre yerel model karşılaştırması |
| `/api/jarvis/research/fetch` | `POST` | Web sayfası içeriğini güvenli/temizlenmiş metin olarak çeker |
| `/api/jarvis/knowledge/search` | `POST` | BM25 algoritması ile yerel doküman ve kodlarda arama yapar |
| `/api/jarvis/knowledge/index` | `POST` | Çalışma alanındaki dokümanları tarar ve RAG indeksini yeniler |
| `/api/jarvis/knowledge/summarize` | `POST` | Belirtilen dosyanın yapısını ve özetini çıkarır |
| `/api/jarvis/knowledge/stats` | `GET` | İndekslenen dosya, parça (chunk) ve kelime istatistikleri |
| `/api/jarvis/voice/command` | `POST` | Wake-word denetimiyle sesli komutu işler ve sesli yanıt üretir |
| `/api/jarvis/voice/speak` | `POST` | Kokoro-82M ONNX ile metni seslendirir ve `.wav` URL'i döner |
| `/api/jarvis/voice/status` | `GET` | Ses motoru, ONNX ağırlıkları ve önbellek durumu |
| `/api/jarvis/daemon/status` | `GET` | Arka plan servisi, PID, port 7860, RAM, masaüstü kısayolu ve Windows başlangıç durumu |
| `/api/jarvis/daemon/shortcut` | `POST` | Windows Masaüstüne JARVIS başlatıcı kısayolu (.lnk) oluşturma |
| `/api/jarvis/daemon/startup` | `POST` | Windows açılışında sessiz çalışma (Startup) servisini aktif/pasif etme |

---

## 🖥️ 6. Web HUD Yönetici Kumanda Panelleri (Frontend UI)

JARVIS Web HUD, Iron Man tarzı karanlık cam (glassmorphism), neon cam göbeği/mor ışımalar ve 5 bağımsız alt paneliyle Sayın Hilmi için tasarlandı:

### A. İletişim & Chat Paneli (`#jarvisHudView_chat`)
- Doğrudan JARVIS yapay zeka çekirdeğiyle konuşma veya rehberdeki kişilere (WhatsApp Baileys) mesaj hazırlama/gönderme.
- **Multimodal Medya Önizleme:** Gelen WhatsApp fotoğrafları, ses kayıtları, videolar ve PDF/ZIP/Office dokümanları mesaj akışında doğrudan oynatılır, önizlenir ve güvenle indirilebilir.
- **Akıllı Üslup Bildirimi:** Mesaj taslağı hazırlanırken geçmiş sohbetten çıkarılan samimiyet düzeyi (*Doğal, Resmi, Samimi, Aile*) rozetiyle Sayın Hilmi'ye onaylatılır.
- **Windows Yaşam Döngüsü Denetimi:** Masaüstü kısayolu oluşturma ve Windows başlangıcına ekleme fonksiyonları.
- Hızlı yönlendirme şeridi: Günlük Brifing, Ajanda, Hafıza RAG, Ses Stüdyosu ve Sistem Durumu butonları.
- Anlık mikrofon ile sesli komut alma ve Kokoro TTS sesli yanıtları.

### B. Günlük Brifing & Yönetici Özeti (`#jarvisHudView_briefing`)
- **Dinamik Karşılama:** Günün saatine göre akıllı hitap (*"Günaydın Sayın Hilmi"*, *"İyi Akşamlar Sayın Hilmi"*).
- **Tek Tıkla Seslendirme:** *"Brifingi Dinle (Kokoro TTS)"* butonu ile günün tüm özetini yerel nöral sesle seslendirir.
- **4 Canlı Operasyon Rozeti:** Aktif Görevler, WhatsApp İletişimleri, Arka Plan Render İşleri ve Sistem Telemetrisi.
- **Öncelikli Görev Panosu:** Acil/yüksek öncelikli görevler ve inline hızlı görev ekleme formu.
- **Zamanlanmış Hatırlatıcılar & Son Yönetici Notları:** Yaklaşan randevular ve son stratejik kararlar.

### C. Ajanda, Görevler & Yönetici Not Panosu (`#jarvisHudView_agenda`)
- **Görev Yönetimi:** Tümü, Bekleyen ve Tamamlanan durum filtreleri; Acil (kırmızı), Yüksek (kehribar), Normal (cam göbeği) öncelik rozetleri; son teslim tarihi takibi.
- **İnteraktif Tamamlama:** Tek tıkla görevi tamamlama, pozitif sesli uyarı chimesi ve anında brifingle çift yönlü senkronizasyon.
- **Yönetici Notları (Memos):** Başlık, içerik ve etiketleme (`#toplantı`, `#fikir`, `#finans`) ile anlık strateji arşivi.

### D. Yerel Kod & Dokümantasyon RAG Arama Paneli (`#jarvisHudView_rag`)
- **BM25 Hızlı Arama:** Yerel kod tabanını (<10ms) tarayan anlık arama motoru.
- **Önerilen Arama Rozetleri:** `#ffmpeg amf`, `#telemetry`, `#prompt injection`, `#kokoro tts`, `#whatsapp daemon`, `#daemon manager`.
- **Kod Önizleme & Anlık Özet:** Satır aralıkları, alaka skoru, JetBrains Mono kod bloğu ve *"Özetle"* butonuyla anında inline doküman özeti.
- **İndeks Tazeleme:** Tek tıkla çalışma alanını yeniden tarama (`reindexKnowledge`).

### E. Ses, Kokoro-82M & Holografik Dalga Analizörü (`#jarvisHudView_voice`)
- **60 FPS Holografik Dalga Canvas:** HTML5 Canvas üzerinde çalışan çoklu reaktör halkaları ve renkli neon sinüs dalgaları. JARVIS konuşurken yüksek genlikli canlı dalgalar, beklemedeyken yumuşak nefes alma animasyonu.
- **Wake-Word Simülatörü:** *"Hey Jarvis"*, *"Dinle Jarvis"* tetikleme analizi ve temizlenen komutun anında çalıştırılması.
- **Kokoro-82M Stüdyosu:** 4 farklı stüdyo ses karakteri (`am_adam`, `af_sarah`, `af_nicole`, `am_george`), 0.8x-1.4x hız ayarı, hazır brifing şablonları ve özel metin sentezleme.

---

## 🧪 7. Test Mimarisi & Hızlı İzolasyon Standardı
- **İzole & Mocked Testler:** `tests/test_daemon_launcher.py` içerisinde soket kilitlenmelerini, harici COM nesnelerini ve Ollama bağlantı zaman aşımlarını önlemek için mock (`unittest.mock`) stratejisi uygulanmıştır.
- **Sıfır Dış Bağımlılık:** Testler harici sunucu veya canlı port açmadan milisaniyeler içerisinde tam kapsama ile tamamlanır.

---
*Not: Bu dosya her yeni modül, araç veya yetenek entegrasyonunda otomatik olarak güncellenir.*
