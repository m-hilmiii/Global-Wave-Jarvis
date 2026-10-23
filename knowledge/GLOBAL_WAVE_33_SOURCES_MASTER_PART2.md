# 📚 GLOBAL WAVE v3.0: 33 KAYNAK MASTER ANSİKLOPEDİ - BÖLÜM 2 / 3
> **Doküman Kapsamı:** YPP Politikaları, Özgünlük, Üretken Yapay Zeka Şartnamesi, Telif Hakları, Container Metadata, Anti-Bot Zırhı ve Shadowban Protokolü
> **İlgili Kaynaklar:** YouTube İş Ortağı Programı'nda yapılan değişiklikler.txt, YouTube İş Ortağı Programına genel bakış ve uygunluk.txt, Üretken yapay zeka içeriklerinin kullanımını açıklama.txt, Telif hakkına ilişkin düzenlemeler.txt, YouTube'un içerikleri inceleme şekli.txt, TikTok to launch Transparency Center..., Kanalınız algoritma tarafından engellendi mi?..., YouTube Data API'ye Genel Bakış.txt, GLOBAL_WAVE_v3_FINAL_MASTER_BLUEPRIN.md

---

## ⚖️ 1. YPP MONETİZASYON, ÖZGÜNLÜK VE YAPAY ZEKA (AI) ŞARTNAMESİ

### 1.1. Özgün Olmayan (Unoriginal) & Yeniden Kullanılan (Reused) İçerik
* **15 Temmuz 2025 Kuralı (Unoriginal Content):**
  * Otomatik slayt gösterileri, anlatı değeri taşımayan sadece ses senteziyle okunan metinler, kalıp şablon videolar ve insani dokunuş taşımayan kitlesel yapay zeka içerikleri para kazanma engeline takılır.
  * **Çözüm:** Her videoda %30 insani kurgu, orijinal senaryo, özgün anlatı mimarisi ve dinamik montaj bulunmalıdır.
* **Yeniden Kullanılan İçerik (Reused Content):**
  * Başkalarına ait videoları veya stok videoları olduğu gibi kullanmak yasaktır.
  * **Stok Video (Pexels/Pixabay) Görsel Dönüşüm Şartı (FFmpeg Rules):**
    * `scale` + `crop` (dikey dönüştürme ve boyutlandırma).
    * `zoompan` (yumuşak dinamik kamera yakınlaşması/uzaklaşması).
    * Hız ayarı (`setpts=0.9*PTS` %10 hızlandırma).
    * LUT / Color Grading (renk tonlaması değiştirme).
    * Zaman damgalı `.srt` / `.ass` vurgulu altyazı yakma.

### 1.2. Üretken Yapay Zeka (Altered/Synthetic Media) Bildirim Zorunluluğu
YouTube Studio yükleme ekranındaki **"Altered/Synthetic Media"** işaret kutusunun resmi kuralları:
* **MECBURİ OLDUĞU DURUMLAR (İşaretlenmelidir):**
  1. Gerçek bir insanın söylemediği bir şeyi söylüyor veya yapmadığı bir şeyi yapıyor gibi gösterildiği durumlar.
  2. Gerçek bir olayın veya mekanın fotogerçekçi (gören kişinin gerçek sandığı) yapay zeka ile simüle edilmesi.
  3. Gerçekçi duran acil durum, felaket veya tarihi olay canlandırmaları.
* **MUAFTIR (İşaretlenmemelidir! İşaretlenirse Dağıtım Haksız Kısılır):**
  1. Senaryo yazımı, fikir üretimi ve metin taslağı (Claude/ChatGPT).
  2. Fantezi, bilimkurgu, anime veya gerçekçi olmayan animasyon/çizim karakterler.
  3. Yeşil ekran, arka plan temizleme, güzellik/ışık filtreleri, renk düzeltmeleri.
  4. Ses kalitesi artırma veya standart ses sentezi (eğer gerçek bir ünlünün taklidi değilse).
* **İhlal Cezası:** Bildirimin yapılmaması durumunda video kaldırılır, telif ihtarı verilir ve YPP üyeliği askıya alınır.

### 1.3. YMYL (Your Money Your Life) Yasakları & 2027 YPP Eşikleri
* **YMYL Kısıtlaması:** Sağlık, hukuk, finans ve siyaset gibi hassas konularda kendini gerçek bir tıp doktoru, avukat veya yatırım uzmanı gibi tanıtan yapay zeka avatarlarının kullanımı yasaktır.
* **1 Şubat 2027 YPP Güncelleme Eşikleri:**
  * **Tam Monetizasyon:** 1.000 Abone + 20 Milyon Shorts İzlenmesi (veya 8.000 İzlenme Saati).
  * **Erken Erişim (Hayran Desteği):** 500 Abone + 3 Milyon Shorts (veya 3.000 Saat).
  * **Aktiflik Şartı:** 90 günde en az 5 Shorts veya 2 uzun video yüklenme zorunluluğu.

---

## 🛡️ 2. CONTAINER METADATA, PLAYWRIGHT STEALTH VE SHADOWBAN PROTOKOLÜ

### 2.1. FFmpeg Container Metadata Temizliği
Bot yükleme tespit algoritmaları, video konteynerindeki `Lavf` (FFmpeg kütüphanesi) izlerini tarar. Otomasyonda videolar yayınlanmadan önce tüm teknik meta veriler temizlenmelidir:
```bash
ffmpeg -i input.mp4 -map_metadata -1 -metadata title="Clean Title" -metadata artist="Organic Creator" -c:v copy -c:a copy output.mp4
```

### 2.2. Playwright-Stealth Anti-Bot Yükleme Otomasyonu
Mekanik tıklama hızları ve milisaniyelik sabit zamanlamalar platformların bot radarına takılır.
* **`playwright-stealth` kullanımı:** CDP/Puppeteer izlerini gizler.
* **`human_delay()` Katmanı:** Tıklamalar arasına `random.uniform(1.2, 3.8)` saniyelik insansı rastgele beklemeler eklenir.
* **BezIer Fare Kavisleri:** Tıklamalara düz çizgi yerine kavisli fare hareket simülasyonu verilir.

### 2.3. Shadowban (Sıfır İzlenme Hapishanesi) 4 İşareti ve Çözüm Protokolü
1. **Dikey Çöküş:** Gösterimlerin 1 gün içerisinde dikey olarak %70-%90 oranında aniden kesilmesi.
2. **Aramadan Silinme:** Tam video başlığını gizli sekmede (Incognito) birebir aratınca videonun hiçbir yerde çıkmaması.
3. **Öneri Metriklerinin Sıfırlanması:** Browse ve Suggested trafik kaynaklarının tam 0'a düşmesi.
4. **Gizli Yaş Kısıtlaması Anomalisi:** İzleyici yaş dağılımında aniden belirli bir yaş grubunun tamamen sıfırlanması.

* **Çözüm (Kanal Isıtma / Warm-Up Protokolü):**
  * Eski/güvenilir Gmail kullanmak ve 2FA/SMS güvenlik adımlarını açmak.
  * Kanal açıldıktan sonra **ilk 7 gün boyunca hiç video yüklemeden** bir insan gibi günlük 15-20 dakika video izlemek, beğenmek ve 2-3 videoya doğal yorum yazmak.
  * 7. gün 1 adet test Shorts yükleyip *Gizli (Unlisted)* bırakarak arka plan telif/güvenlik taramasının tamamlanmasını beklemek.

---

## 💻 3. YOUTUBE DATA API v3 & ETAG PERFORMANS OPTİMİZASYONU

* **Resource Part Parametresi:** API isteklerinde gereksiz veri çekmemek için `part=snippet,contentDetails,statistics,status` parametreleri spesifik olarak çağrılır.
* **ETag ve HTTP 304 Önbellekleme:**
  * Uygulama, ETag verisini önbelleğe alır. Değişiklik yoksa sunucu `HTTP 304 (Not Modified)` yanıtı dönerek kota ve bant genişliği harcamasını sıfırlar.
