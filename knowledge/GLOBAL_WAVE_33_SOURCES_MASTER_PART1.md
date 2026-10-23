# 📚 GLOBAL WAVE v3.0: 33 KAYNAK MASTER ANSİKLOPEDİ - BÖLÜM 1 / 3
> **Doküman Kapsamı:** 33 Kaynağın Tamamından Süzülen Algoritma Mühendisliği, Matematiksel Formüller, Keşif Motoru ve Paylaşım Zamanlamaları
> **İlgili Kaynaklar:** 1864708.1864770.pdf (Davidson et al.), 45530.pdf (Covington et al.), On YouTube’s recommendation system.txt (Cristos Goodrow), Search & discovery tips-shorts.txt, Search & discovery tips-video.txt, How TikTok recommends videos #ForYou.txt, Best Time to Post on YouTube in 2026 (301k Video Analizi), Uzun video algoritmasını 592 saniyede açıklıyorum..., Bu YouTube Shorts Strajtejisi Kanallarımı Patlatıyor...

---

## 🏛️ 1. YOUTUBE VE TİKTOK ALGORİTMA MÜHENDİSLİĞİ & KEŞİF MOTORU

### 1.1. Akademik YouTube Tavsiye Sistemi Mimarisi (Davidson et al., RecSys 2010)
YouTube öneri motoru temelde **Top-N Recommender** olarak çalışır ve "Unarticulated Want" (kullanıcının dile getirmediği arzusunu) tatmin etmeyi hedefler.

1. **Birlikte İzlenme Grafiği (Co-visitation Graph):**
   * Kullanıcı oturumlarındaki (24 saatlik pencere) video çiftleri (v_i, v_j) taranır ve c_ij ortak izlenme sayısı hesaplanır.
   * **İlişkisellik Skoru Formülü:**
     r(v_i, v_j) = c_ij / f(v_i, v_j)
     Burada f(v_i, v_j) = c_i * c_j (küresel popülerlik normalizasyonu) kullanılarak popüler videoların niş videoları baskılaması engellenir.
2. **Aday Üretimi (Candidate Generation):**
   * Kullanıcının geçmiş izlediği, beğendiği ve favorilediği videolardan oluşan **Tohum Kümesi (Seed Set S)** oluşturulur.
   * Grafik üzerinde n adımlı geçişli kapanım (Transitive Closure C_n(S)) uygulanarak aday kümesi C_final elde edilir:
     C_final = ( U_{i=0}^N C_i ) \ S
3. **Sıralama (Ranking):**
   * Adaylar 3 katmanlı sinyallerle puanlanır:
     * **Video Kalitesi Sinyalleri:** Toplam izlenme, derecelendirme, yorum, favori, paylaşım ve yükleme zamanı.
     * **Kullanıcıya Özel Sinyaller:** Tohum video ile etkileşim zamanı ve izleme sıklığı.
     * **Çeşitlendirme (Diversification):** Tek bir tohum videodan veya aynı kanaldan gelen aday sayısı kısıtlanarak kategori çeşitliliği sağlanır.
4. **Sistem Mimarisi & MMoE Sinyalleri:**
   * Log biriktirme -> Bigtable depolama -> MapReduce toplu ön-hesaplama -> Read-Only Bigtable ile düşük gecikmeli (low latency) canlı sunum.
   * CTR, Long-CTR (uzun izlemeli tıklama), Oturum Süresi (Session Length) ve Memnuniyet Anketleri ana değerlendirme metrikleridir.

---

### 1.2. Derin Derin Öğrenme Ağları Mimarisi (Covington et al., Google Brain, RecSys 2016)
Sistem milyonlarca videoyu kullanıcıya sunulan birkaç özel öneriye indiren iki aşamalı bir "Huni" (Funnel) mimarisidir.

[ Milyonlarca Video ] ──► ( Derin Aday Üretimi / Candidate Generation ) ──► [ Yüzlerce Aday ] ──► ( Derin Sıralama / Ranking ) ──► [ Dozinlerce Öneri ]

#### A. Aday Üretim Ağı (Candidate Generation Neural Network)
* **Aşırı Çok Sınıflı Sınıflandırma (Extreme Multiclass Classification):**
  P(w_t = i | U, C) = e^{v_i * u} / sum_{j in V} e^{v_j * u}
  Burada u in R^N kullanıcı/bağlam vektörü gömmesi, v_j in R^N aday video gömmesidir.
* **Örneklemeli Softmax (Sampled Softmax):** Milyonlarca sınıf için işlem yükünü azaltmak amacıyla birkaç bin negatif örnekleme (Negative Sampling) yapılarak 100 kat hızlandırma sağlanır.
* **Özellik Birleştirme & Örnek Yaşı (Example Age Feature):**
  * Kullanıcının izleme ve arama geçmişi vektörleri ortalanır (average pooling). Coğrafya, cihaz ve demografik veriler eklenir.
  * **Tazelik Çözümü (Example Age):** Makine öğreniminin geçmiş veriye olan eğilimini (historical bias) kırmak için eğitim sırasında örneğin yaşı (t_max - t_N) bir özellik olarak modele verilir. Serving anında bu değer 0 (veya hafif negatif) verilerek algoritmanın **yeni ve viral videoları otomatik öne çıkarması (bootstrapping)** sağlanır.
* **Geleceği Tahmin Etme (Predicting Future Watch):**
  * Rastgele bir videoyu gizleyip tahmin etmek yerine, kullanıcının geçmişini geriye sarıp (t anı) sadece geçmiş adımlarla bir sonraki izleyeceği videoyu tahmin etmek (t+1), asimetrik izleme kalıplarını doğru yakalar ve bilgi sızıntısını (data leakage) engeller.

#### B. Derin Sıralama Ağı (Deep Ranking Neural Network)
* **Ağırlıklı Lojistik Regresyon (Weighted Logistic Regression):**
  * Tıklama olasılığı (CTR) yerine **Beklenen İzleme Süresini (Expected Watch Time)** tahmin eder.
  * Tıklanan (pozitif) örnekler izlenme süresi T_i ile ağırlıklandırılır, tıklanmayan (negatif) örnekler 1 ağırlığı alır.
  * Lojistik regresyonun öğrendiği oranlar sum T_i / (N - k) approx E[T](1 + P) approx E[T] formülü ile doğrudan beklenen izleme süresine eşitlenir.
* **Özellik Mühendisliği & Continuous Powers:**
  * Sürekli özellikler quantile normalizasyonu ile [0, 1) aralığına çekilir. Ayrıca x, x^2 ve sqrt(x) güçleri modele beslenerek doğrusal olmayan ilişkiler kolayca modellenir.
  * Kanal geçmişi, son izleme zamanı ve Aday Üretim katmanından gelen puanlar doğrudan sıralamaya aktarılır.

---

### 1.3. Cristos Goodrow (YouTube Blog) & Resmi Keşif İpuçları
* **80 Milyar Sinyal:** Öneri motoru her gün 80 milyar sinyali işler.
* **Valued Watchtime (Değerli İzleme Süresi):** Sadece izleme süresi yetmez; 1-5 yıldızlı memnuniyet anketleri ile eğitilen yapay zeka modelleri **Valued Watchtime** puanı üretir.
* **Borderline (Sınırda) İçerik Baskılama:** Yanıltıcı, komplo teorisi veya sınırda içerikler insan değerlendiriciler ve onaylı uzmanlar tarafından puanlanarak önerilerden %70+ oranında düşürülür (Borderline watchtime %0.5 altında tutulur).

---

## 📊 2. KESİN ALGORİTMİK EŞİKLER VE MASAÜSTÜ / MOBİL GEOMETRİSİ

### 2.1. Algoritma Performans Eşikleri (Benchmarks)
1. **VVSA (Viewed vs Swiped Away / % Chose to View):**
   * Shorts akışında izleyicinin videoyu pas geçmeyip izlemeyi seçme oranı **minimum %70** olmalıdır. %70 altı videolar akıştan hızla çekilir.
2. **APV (Average Percentage Viewed / Retention):**
   * **30 Saniyelik Shorts:** Minimum **%120 - %150** APV (Seamless Loop ile 2. tura geçiş).
   * **60 Saniyelik Shorts:** Minimum **%90 - %110** APV.
   * **Uzun Form (8+ dk):** İlk 30 saniye tutundurması > %60, genel izlenme oranı > %45.
3. **Metrik Ağırlık Hiyerarşisi:**
   * Paylaşım (Share) > Kaydetme (Save) > Yorum (Comment) > Beğeni (Like)
   * Reels ve TikTok tarafında DM'den paylaşma katsayısı algoritma puanını 5x katlar.

### 2.2. Mobil Arayüz ve Safe-Zone (Güvenli Alan) Kuralları
* **Title Cutoff (Başlık Kırpılması):** Mobil akışta başlığın **ilk 40 karakteri** görünür. En sarsıcı kanca anahtar kelimeleri ilk 40 karaktere yazılmalıdır.
* **Altyazı Güvenli Alanı (Subtitle Safe-Zone):**
  * Ekranın en alt %20'lik kısmı (başlık ve kanal adı alanı) ve en sağ %15'lik kısmı (beğeni, yorum, paylaş, ses ikonu butonları) altyazı ve kritik görsellerden ari tutulmalıdır.
  * Altyazı Y-koordinatı: 1920 x 0.75 = 1440px ile 1600px arasına yerleştirilmelidir.

---

## ⏰ 3. 2026 GÜNCEL PAYLAŞIM ZAMANLAMALARI VE ISINMA HARİTALARI (SocialPilot 301k Video Analizi)

### 3.1. "Publish Before Peak" (Zirveden Önce Yükle) Kuralı
Videoyu hedef kitlenin en aktif olduğu saatte yüklemek hatadır. Videolar **zirve saatinden 1-2 saat önce** yüklenmelidir. Bu süre boyunca YouTube:
1. Videoyu işler, .srt altyazıları dizine ekler ve görselleri tarar.
2. Küçük bir test grubunda kapak/kanca testleri yapar.
3. Bildirimleri hazırlar ve **Engagement Velocity (İlk 24-48 Saat Etkileşim Hızı)** sinyallerini toplar.

### 3.2. Format Bazlı En İyi Yayın Zamanları
* **Uzun Form Videolar (8+ dk):**
  * Hafta İçi: **14:00 – 16:00** (Zirve: 18:00 – 21:00). En güçlü günler: Çarşamba, Perşembe, Cuma.
  * Hafta Sonu: **08:00 – 10:00** (Pazar sabahı tekil en yüksek uzun form slotudur).
* **YouTube Shorts:**
  * Öğle Arası Kaydırması: **12:00 – 14:00**.
  * Akşam Dinlenme Akışı: **18:00 – 19:00**.
  * En güçlü Shorts günü: **Cuma 16:00 – 19:00**.
* **Kaçınılacak Saatler:** Hafta içi sabah 09:00 öncesi ve gece 22:00 sonrası.
