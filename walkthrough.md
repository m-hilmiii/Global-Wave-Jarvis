# 🌊 Global Wave v3.1 — Tam Otonom Video Motoru & Web HUD

**Global Wave v3.1**, Blueprint v3'te tanımlanan $0 maliyetli yerel yapay zeka mimarisini, `MoneyPrinterTurbo`'nun telifsiz varlıkları (29 hazır BGM müziği, fontları, video arama mantığı) ve **zırhlandırılmış 2 aşamalı FFmpeg montaj hattı** ile birleştirerek başarıyla inşa edildi.

---

## 🚀 Hızlı Başlangıç (Nasıl Kullanılır?)

Web HUD sunucusu şu anda arka planda aktiftir ve tarayıcınızda açılmaya hazırdır:

```
👉 Web Kontrol Paneli (HUD): http://127.0.0.1:7860
```

Gelecekte sistemi tek tıkla başlatmak için:
- `Global-Wawe/start.bat` dosyasına çift tıklayabilir veya
- Terminalden `python run_global_wave.py` komutunu çalıştırabilirsiniz.

---

## 🛠️ Zırhlandırılmış Mimari ve Uygulanan Mühendislik Çözümleri

### 1. 2 Aşamalı FFmpeg Render Motoru (Pre-Normalize + Master)
- **Problem:** Farklı FPS (24/30/60) ve çözünürlükteki Pexels videoları doğrudan birleştirildiğinde FFmpeg `xfade` veya `concat` anında çöker.
- **Çözüm:** `engine/video_engine.py` içinde her indirilen ham klip önce bağımsız olarak **1080x1920**, **30 FPS**, **yuv420p**, **SAR 1:1** ve sessiz formatına normalize edilir (`normalized_clip_N.mp4`). Ardından master montaja sokulur. Çökme riski sıfırlanmıştır.

### 2. OneDrive `WinError 32` İzolasyonu
- **Problem:** `Global-Wawe` OneDrive altında olduğu için render sırasında oluşturulan geçici `.mp4` parçalarını OneDrive eşitlemeye çalışır ve okuma kilidi koyarak FFmpeg'i durdurur.
- **Çözüm:** Tüm geçici montaj ve ara dosyalar `%LOCALAPPDATA%\Temp\global_wave_workspace\` içine alınmıştır. Sadece **%100 tamamlanmış nihai video** tek seferde `Global-Wawe/output/` klasörüne kopyalanır.

### 3. Sahne Bazlı Ses Sentezi & Ses Merkezli Zamanlayıcı (Audio Master Clock)
- **Problem:** Tüm metni tek parça okutup SRT'den süre tahmin etmek duraksamalarda zaman kaymasına yol açar.
- **Çözüm:** Senaryodaki 5 sahne (Hook, İpucu 1, İpucu 2, İpucu 3, CTA) Edge-TTS ile **5 ayrı MP3 parçası** olarak sentezlenir. Her birinin süresi `ffprobe` ile milisaniyesine kadar ölçülür. Klipler tam bu sürelere kesilir ve sesler FFmpeg ile birleştirilir. Sıfır zaman kayması garantilidir.

### 4. .ass Profesyonel Altyazı Motoru (`srt_to_ass`)
- Kalın font (`Arial` / `Montserrat`), sarı vurgu rengi (`&H0000FFFF&`), kalın siyah kenarlık (`outline=6`) ve TikTok/Shorts güvenli bölgesine uygun alt dikey konumlandırma (`MarginV=300`) ile yüksek izlenme tutma (retention) standardı uygulanmıştır.

### 5. Multi-Tier Fallback (Pexels -> B-Roll -> Acil Durum Jeneratörü)
- Pexels API'den sonuç dönmezse veya kota dolarsa sistem durmaz:
  1. Kademe: Pexels API dikey video araması.
  2. Kademe: `assets/fallback_broll/` yerel nötr dikey video havuzu.
  3. Kademe: FFmpeg dahili renk jeneratörü (`color=c=0x0a1128:s=1080x1920:r=30`) ile dinamik arka plan üretimi.

### 6. Sıfır Kod Dokunma: Token & Ayar Sihirbazı
- Kullanıcı hiçbir dosyaya girip API key yapıştırmakla uğraşmaz.
- Web HUD arayüzündeki **⚙️ Token & Ayar Sihirbazı** üzerinden Pexels, Ollama, ElevenLabs, Supabase ayarları tek tıkla girilir ve `config/tokens.json` dosyasına güvenli şekilde kaydedilir.

---

## 📊 Doğrulama & Test Sonuçları (E2E Test Raporu)

Aşağıdaki entegrasyon testi `scratch/test_e2e_pipeline.py` üzerinden başarıyla yürütülmüştür:

| Test Adımı | Hedef | Çıktı / Durum |
|---|---|---|
| **1. Konfigürasyon** | Token ve Ayarların yüklenmesi | ✅ Pexels Key hazır, FFmpeg WinGet yolu bağlandı |
| **2. Persona Doğrulama** | 5 Persona tanımı | ✅ `us_hustler`, `uk_critic`, `de_engineer`, `jp_zenmaster`, `br_socialite` |
| **3. Senaryo Motoru** | Ollama JSON Mode | ✅ 5 sahneli yapılandırılmış viral senaryo üretildi |
| **4. Ses & Altyazı** | Chunked Audio + ASS | ✅ 2 sahne (3.36s + 3.48s) MP3 + 715 byte ASS altyazı üretildi |
| **5. Stok Malzeme** | Pexels Dikey Video | ✅ Pexels üzerinden 2 dikey video indirildi (4.75MB + 1.71MB) |
| **6. Pre-Normalization** | 1080x1920 30FPS | ✅ 2 klip başarıyla normalize edildi (696KB + 645KB) |
| **7. Master Render** | BGM Ducking + Altyazı | ✅ **Nihai Video Üretildi:** `output/global_wave_short_20260922_011822.mp4` (1.36 MB) |

---

## 📂 Proje Dizin Yapısı

```
Global-Wawe/
├── assets/
│   ├── songs/                 # 29 adet telifsiz fon müziği (MoneyPrinter'dan aktarıldı)
│   ├── fonts/                 # Dinamik altyazı fontları
│   └── fallback_broll/        # 3 adet yerel nötr dikey video klip
├── config/
│   ├── settings.py            # Konfigürasyon ve binary bulucu
│   └── tokens.json            # Kullanıcı tokenları (arayüzden yönetilir)
├── engine/
│   ├── personas.py            # 5 Ülke persona promptları ve sesleri
│   ├── script_engine.py       # Ollama JSON-Mode senaryo üreteci
│   ├── voice_engine.py        # Edge-TTS chunk sentezleyici ve .ass stil motoru
│   ├── material_engine.py     # Pexels API + Fallback yöneticisi
│   └── video_engine.py        # 2 Aşamalı FFmpeg render motoru
├── web/
│   ├── static/
│   │   ├── style.css          # Koyu tema, glassmorphism, responsive CSS
│   │   └── app.js             # HUD kontrolleri, SSE canlı takip dinleyicisi
│   ├── templates/
│   │   └── index.html         # Tek sayfa kontrol paneli (HUD)
│   └── server.py              # FastAPI arka plan asenkron sunucusu
├── output/                    # Üretilen nihai MP4 videolar
├── run_global_wave.py         # Python başlatıcı
└── start.bat                  # Çift tık Windows başlatıcı
```
