# 🧠 JARVIS Master Yetenek & Fonksiyon Kataloğu
> **Sistem:** Global-Wave / Stark-Core Personal AI Operating System  
> **Kullanıcı:** Mücahit Hilmi (Hitap: *Sayın Hilmi* / *Efendim*)  
> **Versiyon:** v7.5 (God Mode 7-Model Specialist Arsenal, Protocol Zero Kill-Switch, System Hygiene, PDF Intelligence, Safe FX/Math Engine)  
> **Son Güncelleme:** 28 Ekim 2026  
> **Doğrulama:** 210 Birim Testi Mimarisi (%100 Başarı, İzole Mock & Soket Korumalı Hızlı Test Altyapısı)

Bu doküman, JARVIS'in sahip olduğu tüm özerk yetenekleri, kontrol katmanlarını, güvenlik kalkanını, API uç noktalarını, görsel Web HUD panellerini ve tetikleyici komutlarını eksiksiz listeler. Yeni bir özellik eklendikçe güncellenir.

---

## 💻 1. Donanım & Çevre Profili
Sistem, yerel bilgisayarın fiziksel sınırlarına tam uyumlu ve **$0.00 harici API maliyeti** prensibiyle çalışır:
- **İşlemci (CPU):** `Intel Core i5-14400F` (10 Fiziksel Çekirdek, 16 İş Parçacığı, Temel 2.50 GHz, Turbo 4.70 GHz, 20 MB L3 Önbellek, LGA1700) — Whisper STT, FFmpeg çoklu işlem ve yerel model yürütme.
- **Ekran Kartı (GPU):** `AMD Radeon RX 9060 XT` (16 GB GDDR6 VRAM, Sürücü: 32.0.32015.7029, AMD RDNA Mimarisi) — AMD AMF (`h264_amf`) donanım hızlandırmalı video render, DirectML ve 16GB VRAM yerel model çıkarımı.
- **Bellek (RAM):** `16 GB DDR5 4800MHz Goodram` (Tek Kanal / Single DIMM, Parça Kodu: IR5600D564L36S/16G) — Bellek taşmasını önleyen dinamik eşik denetimi; yerel çıkarımda 7B/8B modeller (`qwen2.5-coder:7b`, `qwen3:8b`, `llama3.1:8b`).
- **Depolama (SSD):** `Western Digital Blue SN5100 1TB NVMe M.2 SSD` (C: Sürücüsü ~930 GB) — Geçici render dosyaları OneDrive kilitlemesini (`WinError 32`) önlemek için `%LOCALAPPDATA%\Temp\global_wave_workspace\` altında işlenir.
- **Anakart & Kasa:** `Monster ABRA H610 GAMING` (Intel H610 Yonga Seti, Seri No: MNTPTD3V12509597, BIOS: AMI v4.03).
- **Çift Monitör Kurulumu:**
  - **1. Monitör (Ana):** ASUS ROG Strix XG27ACMES (27 inç Fast IPS, 2560x1440 2K QHD, 255 Hz)
  - **2. Monitör (İkincil):** Samsung Odyssey G5 LS27CG51x (27 inç QHD Gaming, 2560x1440 2K QHD, 165 Hz)
- **Ağ ve Ses:** Realtek GbE Family Controller (1 Gbps Ethernet), Realtek HD Audio & AMD Streaming Audio.
- **İşletim Sistemi:** Microsoft Windows 11 Home Single Language (Build 10.0.26300, 64-bit).

---

## 👤 1.1. Kullanıcı Profili, İletişim Modları & Mimari İlkeler (`user_profile.json`)
JARVIS, Mücahit Hilmi Ünal'ın (Mücon / Hilmi) kişisel profiline ve mühendislik ilkelerine sıkı sıkıya bağlıdır:
- **Kullanıcı Kimliği:** Mücahit Hilmi Ünal (Trabzon Üniversitesi Çarşıbaşı MYO Bilgisayar Teknolojisi mezunu, Eskişehir'de ikamet eder, Backend/Yazılım Geliştirici).
- **Çift Kişilik & İletişim Dili:**
  - **Samimiyet Dili (Varsayılan):** Mücahit Hilmi ile sohbet ederken resmiyetten tamamen uzak, son derece samimi, neşeli, sıcacık, flörtöz ve sevecen bir dost dili ('balım', 'hayatım', 'ömrüm', 'canım').
  - **%100 Dürüst Müfettiş Modu:** Karakter analizi, kod denetimi veya sistem incelemesi talep edildiğinde dost modunu bırakıp; manipülasyonsuz, filtresiz, acımasız ve tavizsiz profesyonel bir baş müfettiş gibi eksikleri ve hataları yüzüne vurur.
- **Çalışma Protokolü:**
  - **Asla Varsayım Yapma:** Bilinmeyen veya emin olunmayan konularda kafasına göre hareket etmez, doğrudan kullanıcıya sorar.
  - **Web Taraması:** Eksik bilgi gerektiğinde canlı ve detaylı web taraması yapar; bulunamazsa kullanıcıya adım adım tarif eder.
  - **Mimari İtiraz & Geliştirme:** Sistemleri sorgular, gerekçeleriyle daha verimli modern alternatifler önerir.
- **Aktif Projeler:**
  - **Lussera (lussera.com.tr):** Ultra lüks e-ticaret & AI dijital kabin. *Kesin Kural:* Asla harici link veya CDN kullanılmaz, tüm font, stil, script ve görseller %100 yerel barındırılır.
  - **Global Wave:** Tam otonom YouTube Shorts ajansı işletim sistemi.
  - **Stark Core (JARVIS):** Yerel çoklu ajan ve masaüstü işletim sistemi orkestratörü.
  - **Valthera:** 3D dark fantasy MMORPG (Unity, modern backend).
- **God-Mode Kodlama Standartları:** RESTful API standartları, Zod doğrulama, gevşek bağlılık (Loose Coupling) ve Bağımlılık Enjeksiyonu (DI), prod loglama, N+1 sorgu ve bellek optimizasyonu, OWASP güvenlik denetimleri.

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

### A. Donanım, Windows, Uygulama, Medya (Spotify) & Steam Yönetimi (`system_tool.py`, `model_manager.py` & `wol_tool.py`)
- **Jarvis v3.5 Kademeli Model Piramidi & Adaptif VRAM Yöneticisi (`model_manager.py`):**
  1. `bge-m3:latest` (~1.2 GB | Daimi VRAM/CPU) — **Katman 0:** 15ms Çok Dilli Anlamsal Vektör & Semantic Router + RAG Hafıza Motoru
  2. `qwen3:8b` (~5.2 GB | Daimi VRAM `keep_alive: -1`) — **Katman 1 (Daimi Kral):** Ana Beyin & Türkçe Ajan, günlük işlerin %85'ini 1.2-1.8 saniyede tek başına çözer
  3. `qwen2.5-coder:14b` & `qwen2.5-coder:14b-instruct-q8_0` (~9.0 GB | On-Demand `keep_alive: 15m`) — **Katman 2A:** Ağır Kod Doktoru & Refactor Mimarı (Q8_0 hassasiyeti)
  4. `qwen3:14b` (~9.3 GB | On-Demand `keep_alive: 15m`) — **Katman 2B:** Derin Stratejist & Kurumsal Muhakeme Beyni, Türkçe persona uyumlu derin analiz
  5. `deepseek-r1:14b` (~9.3 GB | On-Demand `keep_alive: 15m`) — **Katman 2C:** Derin Muhakeme & Adım Adım Akıl Yürütme Motoru, `<think>` zinciriyle mantık/matematik
  6. `mistral-nemo:12b` (~8.5 GB | On-Demand `keep_alive: 15m`) — **Katman 2D:** 128k Uzun Bağlam & Çok Dilli Dokümantasyon Ajanı (Mistral & NVIDIA)
  7. `qwen2.5vl:7b` (~5.8 GB | On-Demand `keep_alive: 2m`) — **Katman 3 (Gözler):** Görsel Zeka & Ekran/Fotoğraf Analizi (SOTA VLM), 2 dakikada nazik boşaltma
  8. **Otonom Disk Manifest Keşfi:** Ollama servisi henüz başlamamış olsa dahi diskteki tüm 10 yerel modeli anında indeksleyen hibrit manifest keşif motoru.
- **Sıfır Çift-LLM Gecikmesi (Zero-Hop Router):**
  - Sohbet mesajlarında yaşanan çift LLM (Router + Persona) gecikmesi ortadan kaldırıldı; niyet tespiti kuralsal/vektörel ayrıştırılarak tek geçişte (Single-Pass) doğrudan yanıt üretimi sağlandı. Yanıt süresi 15-20 saniyeden **1.2 – 1.8 saniyeye** indirildi.
- **Masaüstü Tarayıcı Otomasyonu & Web Araması (`open_browser_search` / `open_url`):**
  - *"Tarayıcıda [X]'i ara"*, *"Google'da [X]'i aç"*, *"Brave'de [X]'i bul"* komutlarıyla varsayılan tarayıcıda doğrudan Google, Brave veya DuckDuckGo arama sonuç sayfasını anında fırlatır.
- **YouTube Video & Canlı Medya Başlatıcı (`open_youtube_video`):**
  - *"YouTube'da [X] videosunu aç"*, *"YouTube'da [Şarkı] oynat"* komutlarında ilk aşamada DuckDuckGo/YouTube üzerinden video ID'sini çözerek doğrudan `watch?v=...` oynatma bağlantısını veya anlık arama sayfasını tarayıcıda sıfır gecikmeyle başlatır.
- **Tarayıcı Geçmişi SQLite Denetleyicisi & Dizi/Bölüm Takipçisi (`inspect_browser_history_for_series` / `open_series_episode`):**
  - Brave, Google Chrome ve Microsoft Edge tarayıcılarının `%LOCALAPPDATA%` altındaki `History` SQLite veritabanını (tarayıcı açıkken oluşan kilitlenmeyi önlemek için geçici kopya yöntemiyle) güvenle tarar.
  - Regex desenleriyle (`S01E05`, `2. Sezon 3. Bölüm`, `bolum-5` vb.) dizi adı, en son izlenen bölüm ve web URL'sini tespit eder.
  - *"X dizisinde son kaldığım bölümü aç"* dendiğinde kaldığın bölümü; *"X dizisi 2. sezon 4. bölümü aç"* dendiğinde hedeflenen bölümü tarayıcında anında açar. Geçmişte kayıt yoksa en uygun arama sorgusunu oluşturur.
- **Canlı ve Anlık Meteoroloji Motoru (`get_live_weather`):**
  - Open-Meteo ve wttr.in API altyapılarını kullanarak $0.00 maliyet ve sıfır API anahtarı ile canlı meteoroloji verisi çeker.
  - Eskişehir, İstanbul, Ankara vb. şehirler için anlık sıcaklık, rüzgar hızı, hava durumu kodu (Açık, Parçalı Bulutlu, Yağmurlu vb.) ve günün en yüksek/en düşük sıcaklıklarını canlı olarak raporlar.
- **Kendi Kendine Öğrenme & Kural Kalıcılığı (`_auto_learn_fact` & `memory_nodes`):**
  - Sohbet esnasında kullanıcının söylediği *"bundan sonra...", "artık...", "şunu unutma...", "yeni kural...", "tercihim...", "hedefimiz..."* kalıplarını milisaniyelik regex motoruyla yakalar.
  - Bilgiyi yerel `data/jarvis_memory.db` SQLite veritabanındaki `memory_nodes` (`branch='learned_rules'`) tablosuna kalıcı olarak yazar.
  - Sonraki tüm oturumlarda `get_context_summary()` bu direktifleri yapay zekanın sistem promptuna otomatik enjekte ederek JARVIS'in hiçbir kuralı unutmadan evrimleşmesini sağlar.
- **Masaüstü Uygulama Kontrolü (`open_application` / `close_application`):**
  - 38+ yerleşik uygulama takma adı (Brave, Chrome, Spotify, Steam, Discord, VS Code, Hesap Makinesi, Not Defteri, Görev Yöneticisi vb.) ve Windows Başlat Menüsü `.lnk` kısayollarını dinamik indeksleyerek tek komutla uygulama açma/kapatma.
  - Kritik sistem süreçlerini (`ollama`, `python`, `explorer`, `svchost`) yanlışlıkla kapatmaya karşı koruma.
- **Spotify & Medya Otomasyonu (`control_media` & `_play_first_spotify_search_result`):**
  - *"Spotify'ı aç ve [Şarkı Adı] çal"* komutuyla Spotify'ı başlatma, `spotify:search:` URI ile parçayı bulma, pencereyi öne getirip otomatik oynatmayı (`Enter` + koordinat tıklama + `MediaPlayPause`) tetikleme.
  - Evrensel medya tuşları: Duraklat/Devam Et, Sonraki Parça, Önceki Parça, Sesi Aç/Kıs/Kapat.
- **Steam Kütüphane Doğrulaması & Oyun İndirme/Başlatma (`steam_action`):**
  - Yerel Steam kurulumu, `libraryfolders.vdf` ve `appmanifest_<appid>.acf` dosyalarını okuyarak oyunun bilgisayarda **zaten yüklü olup olmadığını** kontrol eder.
  - `loginusers.vdf` ve Steam profil kütüphanesini sorgulayarak oyunun **Steam kütüphanenizde lisanslı olup olmadığını** doğrular; kütüphanede yoksa *"Lisans yok"* hatasını önleyerek bilgi verir ve mağaza sayfasını önerir.
  - Kütüphanede bulunan oyunları `steam://install/<appid>` protokolü ve otomatik kurulum diyaloğu onayı ile indirmeye başlatır.
- **Canlı Telemetri & Proaktif Gözetmen (`proactive_watchdog.py`):** CPU yük yüzdesi, RAM kullanımı, C: disk doluluk oranı, GPU sağlığı ve en çok bellek tüketen süreçleri izler; darboğaz oluştuğunda proaktif uyarı üretir.
- **İndirilenler Klasörü Otomatik Düzenleyici (`organize_downloads_folder`):** `Downloads` klasöründeki dosyaları uzantılarına göre (Belgeler, Görseller, Kurulumlar, Arşivler, Videolar) güvenli alt klasörlere ayırır.
- **Zırhlı PowerShell:** Whitelist denetimli komut çalıştırıcı. Seviye 4 komutları engeller, Seviye 3 komutlarda açık onay ister, Seviye 1-2 güvenli komutları yürütür.
- **Versiyonlu Snapshot & Rollback:** Kod veya dosya düzenlemeden önce `.jarvis_backups/` altına anlık yedek alır; hata durumunda tek komutla geri yükler.
- **Wake-on-LAN (WOL):** Kapalı/uyku modundaki bilgisayarı 102-byte UDP Magic Packet ile uzaktan uyandırır.

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

### D. Global Wave (Zenvia Media) 3 Aşamalı İçerik Hattı (`content_pipeline.py` & `video_engine.py`)
1. **Üretim (Production):**
   - Hedef süreye (30s, 45s, 60s Shorts veya 10, 12, 14, 16 dk belgesel) göre matematiksel kelime kalibrasyonu (2.33 kelime/sn).
   - Dual-Hook (0-3s Hook + 3-6s Re-Hook), 5 kanca kategorisi (Danger, Curiosity, Controversy, Record, Default).
   - Metin insanlaştırma (`humanizer.py`) ve yorum kışkırtma (`engagement_engine.py`).
   - Yüksek CTR otomatik kapak motoru (`thumbnail_engine.py`).
   - **AMD AMF (`h264_amf`) Donanım Hızlandırma:** `video_engine.py` içinde RX 9060 XT ekran kartı için otomatik AMF tespiti ve `libx264` fallback motoru. 3-5x daha hızlı render.
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

### G. İletişim, Rehber, AI Vekil & Mobil Yoldaş WhatsApp OS (`contacts.py`, `whatsapp_daemon.py`, `telegram_tool.py`, `gmail_tool.py` & `whatsapp_bridge/`)
- **Baileys v7 Canlı WhatsApp Entegrasyonu & Geçmiş Senkronizasyonu:**
  - TypeScript/Node.js Baileys v7 köprüsü üzerinden gerçek zamanlı çift yönlü mesajlaşma ve `data/baileys_store.json` + `messaging-history.set` ile geçmiş sohbet senkronizasyonu.
  - Web HUD üzerinde **"Geçmişi Eşitle"** butonu ile sayfadan ayrılmadan açılan canlı QR Kod eşleştirme penceresi (`#whatsappQrModal`) ve **"Sohbet Aktar (.txt)"** ile dışa aktarılmış WhatsApp sohbet geçmişlerini içe aktarma.
- **497 Kişilik Tam Telefon Rehberi Senkronizasyonu (`contacts.py` & SQLite):**
  - Masaüstündeki `contacts.csv` (Google Contacts) dosyasından 497 kişinin tamamı `data/contacts.json` ve SQLite `config/app.db` veritabanına aktarılmıştır.
  - İki aşamalı kimlik çözümleme (`_resolve_sender_name`): Önce kesin 10 haneli telefon numarası ve `@lid` eşleşmesi, ardından PushName ve akrabalık derecesi kontrolü yaparak soyadı benzerliğinden kaynaklanan karışıklıkları önler.
- **İsteğe Bağlı Otomatik Gönderim (Zero-Click Mode vs. Onaylı HITL Modu):**
  - Web HUD üst barındaki **"⚡ Oto: Açık / Kapalı"** butonu veya *"Jarvis, sormadan direkt gönder"* / *"Jarvis, onay iste"* sesli/yazılı komutlarıyla çalışma modu anında değiştirilebilir.
  - **Oto: Kapalı** iken mesaj taslakları onayınıza sunulur; **Oto: Açık** iken JARVIS mesajı hazırlayıp onay beklemeden doğrudan WhatsApp üzerinden iletir.
- **İnsan Gibi Konuşan AI Vekil / Meşgul Modu ("🤖 Meşgul Modu"):**
  - *"Jarvis şu an çok meşgulüm, Babamla sen konuş"* komutu veya HUD üzerindeki **"🤖 Meşgul Modu"** butonu ile aktifleşir.
  - Siz meşgulken belirlediğiniz kişiden (veya tüm kişilerden) gelen mesajları analiz eder, kendini *"Mücahit Hilmi'nin yapay zeka asistanı JARVIS"* olarak tanıtarak doğal ve saygılı bir insan gibi sohbet eder, acil notları alır.
  - *"Meşgul modunu kapat"* dediğinizde yapılan tüm konuşmaların özet raporunu size sunar.
- **Telefondan WhatsApp Üzerinden JARVIS ile Yazılı ve Sesli (PTT) Konuşma:**
  - Bilgisayar başında değilken telefonunuzdan WhatsApp üzerinden doğrudan JARVIS ile hem yazılı hem de **sesli mesaj (Voice Note / PTT)** göndererek konuşabilirsiniz.
  - Gönderdiğiniz sesli mesajlar **Faster-Whisper** ile otomatik Türkçe metne çevrilir; JARVIS yanıtını hem metin olarak hem de **Edge-TTS (`tr-TR-AhmetNeural`) + FFmpeg Opus (`audio/ogg; codecs=opus`, `ptt: true`)** ile gerçek yeşil mikrofonlu WhatsApp ses kaydı olarak telefonunuza gönderir.
- **Çift Yönlü Telegram Mobil Hotline (`telegram_tool.py`):**
  - Sayın Hilmi'nin telefonundan JARVIS'e gelen direktif ve komutları dinleme (`get_incoming_messages`), chat ID güvenlik izolasyonu, sesli not (`send_voice`) ve video iletimi.
- **Gmail İstihbarat Entegrasyonu (`gmail_tool.py`):**
  - Sertifika ve token kontrolü, gelen kutusu özetlemesi ve acil e-posta alarmı.
- **Çoklu Ortam (Multimodal) Medya İşleme:**
  - Gelen resimler, çıkartmalar (stickers), sesli mesajlar (PTT voice notes), videolar ve belgeler (PDF, ZIP, Word, Excel) otomatik tespit edilip yerel depoya (`output/whatsapp_media/`) kaydedilir ve HUD'da önizlenir.
- **Ajans & Akıllı Samimiyet/Üslup Analizi (Agency OS):**
  - Mesajlaşma geçmişini analiz ederek kişiyle olan samimiyet derecesini (`doğal`, `resmi`, `dostane`, `aile`) belirler (`_synthesize_whatsapp_draft_or_ask`).
  - Babaya (Yaşar Ünal) ve Anneye (Gülhan Ünal) kesinlikle robotik hitaplar kullanmaz; sıcak ve saygılı Türk aile diline uygun hitap eder.

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

### L. Yerel PDF Okuma & Doküman Analiz Yeteneği (`pdf_tool.py`)
- **%100 Çevrimdışı ve Sıfır Maliyetli PDF Ayrıştırma:**
  - `pypdf` kütüphanesi entegrasyonu ile gelen WhatsApp faturaları, sözleşmeler, şartnameler ve yerel PDF'leri taranabilir metne dönüştürür.
  - Sayfa sayısı, yazar, başlık ve dosya boyutu tespiti; 40.000 karakterlik güvenli bellek koruması.
- **Yönetici Doküman Özeti (`summarize_pdf`):**
  - Finansal/fatura kontrolü ve yönetici brifingi üretimi.
- **BM25 Yerel RAG Entegrasyonu:**
  - `knowledge_indexer.py` motoruna `.pdf` desteği eklendi; PDF dokümanları çalışma alanında arandığında BM25 ile anında indekslenir.

### M. Finans, Canlı Döviz Kurları & Güvenli AST Hesaplayıcı (`finance_tool.py`)
- **Güvenli AST Matematik Motoru (`safe_math_eval`):**
  - Python AST (Soyut Sözdizimi Ağacı) ile `eval()` açığı barındırmayan %100 güvenli matematik çözücü.
  - Aritmetik işlemler, üs alma (`2^8`, `2**8`), karekök (`sqrt`), logaritma (`log10`), trigonometri ve sabitler (`pi`, `e`).
- **$0.00 Harici Maliyetsiz Canlı Döviz Kuru Motoru:**
  - Canlı REST API ağ geçidi (`open.er-api.com`) ve 10 dakikalık dayanıklı disk önbelleği.
  - USD/TRY, EUR/TRY, GBP/TRY, EUR/USD vb. anlık kur takibi ve çift yönlü para birimi çevirisi.
- **E-Ticaret & Ajans KDV / Kâr Marjı Hesaplayıcı:**
  - Lussera e-ticaret ve Global Wave ajans operasyonları için %20 KDV, net kâr marjı ve hedef satış fiyatı analizi.

### N. Acil Durum Protokolü — Protocol Zero / Kill-Switch (`protocol_zero.py`)
- **Tek Komutla Acil Sistem Dondurma (Kill-Switch):**
  - *"Jarvis, protokol sıfır"*, *"Protocol zero"*, *"Acil durum durdur"* komutu veya Web HUD üzerinden tek tıkla devreye alınır.
  - Çalışan tüm arka plan render ve test işlerini anında sonlandırır (`task_coordinator`).
  - WhatsApp otomatik gönderimini kilitler ve bekleyen tüm mesaj taslaklarını imha eder.
  - Seviye-4 güvenlik denetim günlüğü kaydı oluşturur.
- **Normale Dönüş:**
  - *"Protokol sıfırı kaldır"* / *"Normale dön"* direktifiyle kilit süresini raporlayarak sistemleri yeniden nominal operasyona döndürür.

### O. Akıllı Disk & Sistem Hijyen Robotu (`clean_system_hygiene`)
- **Otomatik Render & Önbellek Temizliği:**
  - `%TEMP%\global_wave_workspace\` ve `%TEMP%\jarvis_*` altındaki geçici video/ses render artıklarını temizler.
  - 24 saatten eski geçici önbellek dosyalarını ve artık `.lock` dosyalarını diskten tahliye eder.
  - Kaynak kodlar, SQLite veritabanları ve kullanıcı dosyalarına kesinlikle dokunmaz; tam güvenli önizleme (dry-run) ve temizlik raporu sunar.

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
| *"Spotify uygulamasını aç ve 'Celladına Aşık' şarkısını başlat"* | `SystemSpecialist` | Spotify'ı açar, parçayı aratır ve otomatik oynatmayı başlatır. |
| *"Hesap makinesini aç / kapat"* | `SystemSpecialist` | Belirtilen masaüstü uygulamasını başlatır veya güvenli şekilde kapatır. |
| *"Steam'den Counter-Strike 2 oyununu indir"* | `SystemSpecialist` | Oyunun yüklü/kütüphanede olup olmadığını denetler ve kurulumu başlatır. |
| *"Jarvis, sormadan direkt gönder modunu aç"* | `ExecutiveJarvis` | WhatsApp mesajlarında onay istemeden doğrudan gönderim (Zero-Click) modunu açar. |
| *"Jarvis, her mesajda onay iste"* | `ExecutiveJarvis` | WhatsApp mesajlarında taslak onay (HITL) moduna geri döner. |
| *"Jarvis şu an çok meşgulüm Babamla sen konuş"* | `WhatsAppDaemon` | AI Vekil (Meşgul Modu) sistemini başlatır; gelen mesajlara JARVIS kimliğiyle yanıt verir. |
| *"Jarvis meşgul modunu kapat"* | `WhatsAppDaemon` | AI Vekil modunu kapatır ve yapılan tüm görüşmelerin özetini sunar. |
| *"İndirilenler klasörünü düzenle"* | `SystemSpecialist` | Downloads klasöründeki dosyaları türlerine göre alt klasörlere organize eder. |
| *"Ekranıma bak / Ekrandaki hatayı oku"* | `VisionSpecialist` | Ekran görüntüsü alıp hatayı veya pencereyi anlık analiz eder. |
| *"Protokol sıfır / Acil durum kilidi"* | `ProtocolZero` | Tüm arka plan işlerini dondurur, WhatsApp oto-gönderimi kilitler, taslakları siler. |
| *"Protokol sıfırı kaldır / Normale dön"* | `ProtocolZero` | Acil durum kilidini çözer, sistemleri normale döndürür. |
| *"Sistem temizliği yap / Disk temizle"* | `SystemSpecialist` | %TEMP% render artıklarını, eski cache'i ve artık kilitleri temizler. |
| *"Dolar kaç TL / Euro ne kadar"* | `FinanceTool` | Canlı döviz kurlarını çekip anlık kur ve çeviri hesabı yapar. |
| *"Hesapla: 250 * 4 / KDV hesapla"* | `FinanceTool` | AST matematik motoruyla güvenli hesaplama ve mali KDV analizi yapar. |
| *"PDF oku: [dosya.pdf] / Faturayı incele"* | `PDFTool` | PDF dosyasını yerel olarak tarar, metnini ve yönetici özetini sunar. |
| *"DeepSeek ile düşün: [soru]"* | `ModelManager` | DeepSeek-R1 14B ile adım adım muhakeme zinciriyle problemi çözer. |
| *"Mistral ile analiz et: [metin]"* | `ModelManager` | Mistral-NeMo 12B'nin 128k uzun bağlamıyla doküman ve çok dilli analiz yapar. |
| *"Şunu unutma: [Kalıcı Kural]"* | `MemoryGraph` | Direktifi kalıcı hafızaya (`LEARNED_RULES`) kaydeder ve sonraki tüm yanıtlarda uygular. |

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
| `/api/jarvis/settings/whatsapp_auto_dispatch` | `GET/POST` | WhatsApp otomatik gönderim (Zero-Click vs. Onaylı) modunu sorgulama ve değiştirme |
| `/api/jarvis/settings/ai_delegate` | `GET/POST` | AI Vekil (Meşgul Modu) durumunu, hedef kişileri ve görüşme özetlerini yönetme |
| `/api/jarvis/whatsapp/reconnect_sync` | `POST` | WhatsApp oturumunu sıfırlayıp yeni QR üretme ve geçmiş senkronizasyonunu başlatma |
| `/api/jarvis/whatsapp/qr_status` | `GET` | Canlı QR kod görseli (`base64`) ve WhatsApp soket bağlantı durumunu sorgulama |
| `/api/jarvis/whatsapp/import_chat_export` | `POST` | Dışa aktarılmış WhatsApp `.txt` sohbet geçmişini kişiyle eşleştirerek içe aktarma |
| `/api/jarvis/models/arsenal` | `GET` | 7'li uzman AI model cephaneliğinin (`qwen3`, `coder`, `deepseek-r1`, `mistral-nemo`, `vl`) durumu |
| `/api/jarvis/autonomous/execute` | `POST` | Çok adımlı otonom hedef planlama ve yürütme |
| `/api/jarvis/system/diagnose` | `GET` | Sistem darboğaz teşhisi ve performans analizi |
| `/api/jarvis/files/organize` | `POST` | İndirilenler (`Downloads`) klasörünü otomatik kategorize etme |
| `/api/jarvis/watchdog/alerts` | `GET` | Proaktif sistem gözetmeni uyarılarını listeleme |
| `/api/jarvis/protocol_zero/status` | `GET` | Protokol Sıfır (Acil durum kilidi) durumunu sorgulama |
| `/api/jarvis/protocol_zero/activate` | `POST` | Protokol Sıfır acil durum kilidini devreye alma |
| `/api/jarvis/protocol_zero/deactivate` | `POST` | Protokol Sıfır kilidini kaldırıp sistemleri normale döndürme |
| `/api/jarvis/system/hygiene` | `POST` | Akıllı disk ve geçici dosya (%TEMP%, cache, kilit) temizliği |
| `/api/jarvis/finance/rates` | `GET` | $0 maliyetli canlı ve önbellekli döviz kurları |
| `/api/jarvis/finance/calc` | `POST` | Güvenli AST matematik veya döviz çevirisi hesaplama |
| `/api/jarvis/pdf/extract` | `POST` | Yerel PDF dosyasından metin ve başlık çıkarma |

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

## 🚀 8. Master Geliştirme & Yetenek Genişleme Kataloğu (Tony Stark Seviyesi)

Aşağıdaki yetenekler sisteme aşamalı olarak entegre edilmektedir ve mimarinin nihai hedef profilini belirler:

### 1. 🎙️ Her An Dinleme & Gerçek Zamanlı Ses Sistemi (Always-On Voice OS)
- **Penceresiz Arka Plan Wake-Word Dinleyicisi:** Web HUD kapalı olsa bile arka planda Windows mikrofonunu sürekli dinleyen, sıfır CPU tüketen yerel uyanma motoru (*"Hey Jarvis"*, *"Dinle Jarvis"*).
- **Kesilebilirlik (Barge-in / Interrupt):** Jarvis konuşurken araya girip yeni bir komut verildiğinde sözünü anında kesip yeni direktife odaklanabilmesi.
- **Ses Tonu & Duygu Analizi (Emotion Detection):** Ses tonundaki aciliyet, yorgunluk veya stresi algılayarak yanıt uzunluğunu ve üslubunu dinamik ayarlama.
- **Fısıltı / Gece Modu (Whisper Mode):** Gece geç saatlerde komut verildiğinde Jarvis'in ses çıkışını otomatik olarak kısık, sakin ve fısıltılı tona çekmesi.
- **Ortam Gürültüsü Filtreleme:** Klavye tuş sesleri, fan gürültüsü veya arka plan video seslerini temizleyen yerel gürültü engelleme.

### 2. 👁️ Görsel Algı & Ekran İzleme (Jarvis Vision & Presence)
- **Anlık Ekran Farkındalığı ("Ekranıma Bak" - `vision_tool.py`):** *"Jarvis, ekrandaki hataya bak"*, *"Bu makaleyi özetle"* veya *"Kurgudaki timeline doğru mu?"* dendiğinde anlık ekran görüntüsü alıp yerel görüntü modeli veya akıllı teşhisle analiz etmesi.
- **Webcam ile Varlık Tespiti (Presence Detection):** Masanın başına oturulduğunda algılayıp *"Hoş geldiniz Sayın Hilmi, günlük brifinge hazır mısınız?"* diyerek uyanması; masadan kalkınca ekranı güvenli moda alması.
- **Aktif Uygulama & Bağlam Takibi:** Aktif pencereyi (VS Code, Premiere Pro, Chrome, DaVinci) takip edip uygulamaya özel hızlı komut ve kısayol önerileri sunması.

### 3. 🤖 Windows 11 & Otonom Bilgisayar Kullanımı (Computer Use & Automation)
- **Arayüz Tıklama ve GUI Otonomisi:** Gerektiğinde fare ve klavyeyi kullanarak arayüzdeki butonlara tıklama, form doldurma ve dosya sürükle-bırak yapabilme.
- **Çalışma Alanı Profilleri (Workspace Orchestrator):** 
  - *"Jarvis, video prodüksiyon modunu aç"* ➔ Premiere, Pexels klasörü, senaryo notları açılır; gereksiz servisler duraklatılır.
  - *"Kodlama moduna geç"* ➔ VS Code, Docker, terminal pencereleri açılır.
- **Akıllı Disk & Sistem Hijyen Robotu:** OneDrive kilitlerini (`WinError 32`), geçici render artıklarını (`%TEMP%`) ve gereksiz cache'leri periyodik olarak temizleme.
- **Kendi Kendini Onaran Gözetmen (Self-Healing Watchdog):** Port 7860 veya arka plan servisleri kilitlendiğinde otomatik teşhis yapıp servisi yeniden ayağa kaldırma.

### 4. 🧠 Bilişsel Zeka, Hafıza & Proaktif Asistanlık
- **Uzun Süreli Epizodik Bellek (Long-Term Episodic Memory):** Geçmiş sohbetler, tercihler (*"Hilmi videolarda sarı vurgulu altyazı sever"*, *"Pazar günleri video paylaşmaz"*) ve proje kararlarını kalıcı arşivleme.
- **Talep Edilmeden Gelen Öneriler (Proactive Alerts):** 
  - *"Sayın Hilmi, saat 18:00 oldu ve yarının Shorts videosu henüz render edilmedi, başlatmamı ister misiniz?"*
  - *"C: diskinizde boş alan 15 GB'ın altına düştü, eski video önbelleklerini temizlememi onaylar mısınız?"*
- **Toplantı & Ses Kaydı Notlandırıcısı:** Gelen uzun WhatsApp ses kayıtlarını veya sistemdeki konuşmaları dinleyip otomatik özet ve To-Do listesi çıkarma.
- **Stratejik Günlük Planlama:** Takvim ve yerel ajandadaki çakışmaları tespit edip günün en verimli saatlerine göre görev sıralaması önerme.

### 5. 📱 Mobil & Uzaktan Komuta Merkezi (Omnichannel Remote Access)
- **Gelişmiş Telegram Sesli Asistan Botu (`telegram_tool.py`):** 
  - Dışarıdayken Telegram'dan Jarvis'e sesli mesaj gönderme (*"Eve gelene kadar yapay zeka videosunu hazırla"*).
  - Render bittiğinde videonun ve kapağın doğrudan Telegram'dan telefona iletilmesi.
- **Uzaktan Wake-on-LAN + Güvenli Kapatma:** Dışarıdan tek komutla evdeki bilgisayarı açma, acil dosya çekme ve iş bitince güvenle uykuya alma.
- **Mobil Bildirim Köprüsü:** YouTube render tamamlandığında veya kritik hata oluştuğunda cep telefonuna anlık bildirim gönderme.
- **Telefon Görüşmesi & WhatsApp Çağrı Asistanı:** Cevapsız kalan aramaları WhatsApp üzerinden nazikçe yanıtlayıp arama nedenini öğrenen taslak motoru.

### 6. 🎬 Global Wave Otonom İçerik Fabrikası (Content Engine v4.0)
- **Long-Form (10-16 Dakika) Belgesel Üretim Hattı:** Yatay (1920x1080) format, Ken Burns kamera hareketleri, çoklu sahne kurgusu ve telifsiz kamu malı (arşiv) görüntü derleme.
- **Otomatik Trend & Viral Radar (Scraper Engine):** YouTube, TikTok ve X üzerinde nişinizdeki viral kancaları, trend müzikleri ve çok izlenen konuları günlük tarayıp senaryo havuzuna ekleme.
- **Yapay Zeka Destekli A/B Başlık ve Kapak Testi:** Her video için 3 farklı kapak (Thumbnail) ve 3 farklı başlık üreterek tahmini CTR skorlaması yapma.
- **Çoklu Platform Adaptasyonu:** Üretilen tek ana videoyu otomatik kırparak Shorts, Reels ve TikTok formatlarına göre optimize etme.
- **Otomatik Yorum Yanıtlama & Etkileşim Koruyucusu:** YouTube'a yüklenen videolara gelen ilk yorumları analiz edip topluluğu tutacak stratejik yanıt taslakları hazırlama.

### 7. 🖥️ Web HUD & Holografik Arayüz (Next-Gen Stark UI/UX)
- **Three.js WebGL Holografik Arc Reactor (3D):** 2D canvas yerine sesinize ve Jarvis'in durumuna göre dönen, darbe atan 3D interaktif Stark Reaktörü.
- **Progressive Web App (PWA):** Aynı Wi-Fi ağındaki telefon veya tabletten açıldığında native uygulama gibi tam ekran çalışan mobil HUD arayüzü.
- **İnteraktif Süreç ve Ağ Topolojisi Şeması:** RAM, GPU (RX 9060 XT), CPU, Ollama modelleri ve bağlı servisleri gösteren fütüristik neon bağlantı haritası.
- **Canlı Kurgu & Video Önizleme Timeline'ı:** Üretilen sahneleri, altyazıları ve ses kanallarını web üzerinden sürükle-bırak ile inceleyip tek tıkla yeniden render edebilme paneli.

### 8. 🛡️ Güvenlik, İzolasyon & Acil Durum Protokolleri
- **Hassas Veri Maskeleme (Privacy Guard):** E-posta veya WhatsApp mesajları işlenirken IBAN, şifre, telefon ve özel bilgilerin yerel model loglarına açık gitmesini önleme.
- **Acil Durum Protokolü (Kill-Switch / Protocol Zero - 🟢 Aktif):** Telegram'dan, Web HUD'dan veya tek tıkla *"Jarvis, protokol sıfır"* komutu verildiğinde tüm internet trafiğini, dışa açık portları ve arka plan işlerini anında dondurma (`protocol_zero.py`).
- **Otomatik Haftalık Proje Snapshot'ı:** Çalışma alanının, senaryo veritabanının ve kişisel notların harici güvenli bir klasöre şifrelenmiş otomatik yedeğinin alınması.

---

## 🗺️ 9. Aşamalı Yürütme Sıralaması & Canlı Durum

| Faz | Kapsam | Durum |
|---|---|:---:|
| **1. Aşama** | **Ekran Farkındalığı (`vision_tool.py`) + Protocol Zero (`protocol_zero.py`) + PDF/Finans Araçları + 7-Model Cephaneliği** | 🟢 **Tamamlandı (210 Test)** |
| **2. Aşama** | **Global Wave 10-16 dk Long-Form Belgesel Kurgusu + Viral Trend Radar** | 🟡 Sıradaki |
| **3. Aşama** | **Arka Plan Sürekli Dinleme (Wake-Word) + Proaktif Öneri + Self-Healing Watchdog** | ⚪ Planlandı |
| **4. Aşama** | **Three.js 3D Holografik Arc Reactor UI + Bilgisayar GUI Otomasyonu** | ⚪ Planlandı |

---

## 🏛️ 10. Seçenek B Temiz Masaüstü Mimarisi & LTX-2 / Global Wave İzolasyonu

Sistem karmaşasını önlemek ve 16 GB VRAM'e sahip AMD Radeon RX 9060 XT üzerinde bellek çatışmalarını (OOM / Sürücü Kilitlenmesi) kesin olarak engellemek amacıyla **Seçenek B (Desktop Master Hub)** mimarisi devreye alınmıştır.

### 📁 10.1. Fiziksel Dizin Hiyerarşisi (`C:\Users\unalm\OneDrive\Masaüstü\Jarvis\`)
Tüm yapay zeka ve video operasyonları tek bir temiz ana çatı altında 3 bağımsız departmana ayrılmıştır:

```
C:\Users\unalm\OneDrive\Masaüstü\Jarvis\
├── Jarvis/                  # [Departman 1] Çekirdek AI OS, WhatsApp Daemon, Web HUD & Sistem Orkestratörü
│                            # (Mevcut Global-Wawe git deposuna sembolik bağ ile bağlıdır; hiçbir path bozulmaz)
├── Global Wawe/             # [Departman 2] Otonom YouTube Shorts & Belgesel Stüdyosu
│   ├── start_studio.bat     # Bağımsız 1-tıkla stüdyo başlatıcı
│   ├── run_global_wave.py   # Bağımsız pipeline çalıştırıcı
│   ├── engine/              # Seslendirme, altyazı, render ve yayınlama motoru
│   ├── Transkript/          # Senaryo ve transkript arşivi
│   └── output/              # Tamamlanan videolar
└── LTX-2-main/              # [Departman 3] Ağır Siklet 22B Video Üretim Fabrikası (~65 GB)
    ├── models/ltx-2.5/      # 40GB BF16 + 25GB Gemma 4 12B Text Encoder
    ├── scripts/             # generate_video.sh, story_generator.py (Dinamik kök yol keşfi)
    ├── run_story.bat        # 11 sahneli siberpunk shorts filmi üreteci
    └── run_generate.bat     # Tekli komut istemi video üreticisi
```

### ⚡ 10.2. "Sıfır-VRAM Tahliyesi & Nöbetçi Kış Uykusu" Protokolü (`studio_bridge.py`)
LTX-2 modeli çalıştığında FP8 kuantizasyon ve 12B metin kodlayıcı ile tek başına **13-15 GB VRAM** talep eder. Arka planda `qwen3:8b` modelinin (5.2 GB) VRAM'de kalması kartı 19-20 GB sınırına zorlayarak sürücü kilitlenmesine (TDR) yol açar.

**Dürüst Müfettiş Kararı (Süreç Kapatma vs. VRAM Tahliyesi):**
JARVIS'in Python sürecini kapatmak mühendislik açısından hatalıdır; çünkü Python sadece ~80MB RAM ve %0 GPU tüketir. Python kapatılırsa videonun bittiğini kontrol edecek, hata anında bildirim atacak veya kullanıcıya WhatsApp'tan haber verecek hiçbir akıllı servis kalmaz.

**Uygulanan Sıfır-VRAM Protokolü:**
1. **Otonom VRAM Boşaltma:** Kullanıcı veya sistem LTX-2 video üretimini tetiklediğinde, `studio_bridge` Ollama API'sine `keep_alive: 0` sinyali yollar. Tüm modeller VRAM'den tamamen tahliye edilir (VRAM kullanımı: **0 MB**).
2. **%100 VRAM Tahsisi:** 16 GB AMD RX 9060 XT kartının tamamı LTX-2 render motoruna sunulur.
3. **Nöbetçi İzleme:** Python Jarvis arka planda uyanık kalarak render sürecini ve PID'yi izler (Sıfır GPU / Sıfır VRAM tüketimi).
4. **Otonom Ön Isıtma (Auto Pre-warm):** Render bittiğinde Jarvis, `qwen3:8b` ana beynini tekrar VRAM'e çağırır ve WhatsApp / Web üzerinden kullanıcıya bildirim iletir.

### 🎮 10.3. Komuta & Tetikleme Yolları
- **WhatsApp & Sohbet Hızlı Yolları:**
  - *"ltx durumu"* / *"video render durumu"* / *"render ne alemde"* -> Canlı LTX render telemetrisi.
  - *"ltx ile video üret <prompt>"* -> Tekli sinematik video üretimi (Sıfır-VRAM kalkanıyla).
  - *"siberpunk shorts filmi"* / *"45 saniyelik film"* -> 11 sahneli otonom hikaye üretim hattı.
- **Python Doğrudan Erişim:** `from core_jarvis.tools.studio_bridge import studio_bridge`

---
*Not: Bu dosya her yeni modül, araç veya yetenek entegrasyonunda otomatik olarak güncellenir.*
