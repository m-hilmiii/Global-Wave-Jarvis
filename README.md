# Global-Wave / JARVIS Executive AI & WhatsApp Operations OS

> **Yapay Zeka Destekli Otonom Ajans & Yönetici Komuta Merkezi**  
> Yerel Qwen 3 (8B) Modeli, Baileys WhatsApp Soketi, Faster-Whisper Ses Tanıma ve Kokoro TTS Entegrasyonu.

---

## 🌟 Temel Özellikler

### 1. 🤖 JARVIS Executive AI Brain
* **Yerel Model Gücü:** Ollama üzerinden yerel **Qwen 3 (8B)** modeli ile çalışır ($0 API maliyeti, %100 yerel gizlilik).
* **Human-in-the-Loop (HITL) WhatsApp Taslak Onayı:** JARVIS kafasına göre mesaj göndermez. Karşı tarafa gönderilecek zarif mesaj taslağını hazırlar, kullanıcının onayına sunar. Kullanıcı onaylamadan tek bir mesaj dahi iletilmez.
* **Seçici & Kısa Sesli Yanıt (TTS):** Ekranda zengin detaylar görünürken, sesli asistan gereksiz sistem etiketlerini veya numaraları okumaz; doğrudan taslak metnini okur ve onayınızı sorar.
* **STT Fonetik Hata Düzeltme:** Faster-Whisper ile Türkçe ses tanımadaki yaygın fonetik bozulmaları (örn. *üründür* -> *gönder*, *hali hatru* -> *hali hatrı*, *wp* -> *WhatsApp*) otomatik olarak normalize eder.

### 2. 📱 Baileys Canlı WhatsApp Yönetim Paneli
* **Gerçek Zamanlı İki Yönlü Soket:** Simülasyon değil, Baileys kütüphanesiyle doğrudan WhatsApp Web soketine bağlanır.
* **Kişi ve Sohbet Sekmeleri:** Adem, Babam, Annem, Emre vb. rehber kişileriyle geçmiş ve canlı mesajlaşma.
* **Canlı Gelen Mesaj Bildirimi (Toast Alert):** Arka planda yeni bir mesaj geldiğinde sesli zil ile ekrana bildirim düşer; bildirime tıklayınca anında o kişinin sohbet sekmesi açılır.
* **Mesaj Yönetimi:**
  * ❌ **Herkesten Sil (Baileys Revoke):** WhatsApp protokolü üzerinden mesajı sunucudan ve herkesten siler.
  * 🗑️ **Benden Sil:** Mesajı yerel akıştan kaldırır.
  * 📞 **Sesli Arama:** WhatsApp arama tetikleyicisi.
  * ✨ **JARVIS ile Yanıt Tasarla:** Belirli bir kişinin sohbetindeyken JARVIS'e o kişiye özel şık yanıt yazdırabilirsiniz.

### 3. 🎬 Global-Wave Otonom Video ve Sosyal Medya Motoru
* **YouTube Canlı Telemetrisi & İzleyici Yorum Analizi**
* **Otomatik Senaryo ve Karaoke Altyazı Üretimi**
* **VRAM ve Donanım Kalkanı**

---

## 🚀 Kurulum ve Çalıştırma

### Gereksinimler
* Python 3.10+
* Node.js v18+
* Ollama (`ollama run qwen3:8b`)
* FFmpeg

### Adımlar

1. **Bağımlılıkları Kurun:**
```bash
pip install -r requirements.txt
cd core_jarvis/whatsapp_bridge
npm install
npm run build
cd ../..
```

2. **Sistemi Başlatın:**
```bash
python run_global_wave.py
```

3. **Tarayıcıdan Açın:**
```
http://127.0.0.1:7860
```

---

## 🔒 Güvenlik & Gizlilik
* Baileys oturum anahtarları ve OAuth tokenları `.gitignore` ile yerel ortamda korunur.
* Asla hassas oturum bilgileri uzak repolara commit edilmez.
