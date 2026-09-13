# ReLoop — Döngüsel Tekstil Platformu

**Yarışma:** TEKNOFEST 2026 Sıfır Atık & Döngüsel Ekonomi Yarışması
**Takım Adı:** Arge-T ZeroCode
**Takım ID:** 1003758
**Başvuru ID:** 538788
**Kategori:** Endüstriyel Atık Yönetimi ve Yeniden Kullanım

## Takım

| Rol | İsim | Sorumluluk |
|---|---|---|
| Danışman | Dr. Öğr. Üyesi Tuğçem Partal | Mimari ve algoritma gözetimi, mevzuat uyumu |
| Takım Kaptanı | Beyzanur Yavuz | Koordinasyon, iş modeli, arka uç/API |
| Üye | Şevval Asi | Yazılım mimarisi, eşleştirme motoru, arayüz |
| Üye | Zehra Ürkmez | Matematiksel modelleme, veri analizi |

## Projenin Amacı

ReLoop, Türkiye tekstil sektöründeki **üretim öncesi fireyi** — temiz ve geri kazanılabilir ama alıcı bulamayan kumaş atığını — doğru alıcıyla otomatik ve güvenli biçimde buluşturan bir B2B platformudur.

Fabrika fireyi fotoğraflar → yapay zekâ dijital bir **Malzeme Pasaportu** oluşturur → açıklanabilir bir eşleştirme motoru en uygun alıcıyı bulur → kimlikler anlaşma sağlanana kadar **gizli** kalır → işlem tamamlanınca veriler anonim olarak kamu sistemine (UÇBS/TABS) raporlanır.

Bu depo, Ön Değerlendirme Raporu'ndaki açıklanabilir iki aşamalı eşleştirme motorunun **gerçekten çalışan uygulamasını** içerir. Sentetik veriyle (Şartname md. 5.2/10.7 gereği) çalışan, internet bağlantısı gerektirmeyen tek dosyalık bir web sistemidir.

---

## Nasıl Çalıştırılır?

### 1. Python kurulu mu kontrol edin

Bilgisayarınızda Terminal (Mac) ya da Komut İstemi (Windows) açın, şunu yazın:

```
python3 --version
```

**3.9 veya üstü** bir sürüm görürseniz devam edin. Görmezseniz ya da hata alırsanız, [python.org/downloads](https://www.python.org/downloads/) adresinden indirip kurun.

> **Windows kullanıcıları dikkat:** Kurulum ekranında en altta çıkan **"Add Python to PATH"** kutusunu mutlaka işaretleyin — işaretlemezseniz sistem Python'ı bulamaz.

### 2. macOS'ta çalıştırma

1. Bu klasördeki **`baslat_mac.command`** dosyasına çift tıklayın.
2. İlk açılışta *"geliştirici doğrulanamadığı için açılamıyor"* uyarısı çıkarsa: dosyaya **sağ tıklayın → Aç → tekrar Aç**. (Bu sadece ilk seferde gerekir.)
3. Çift tıklayınca hiçbir şey olmuyorsa: Terminal'i açıp bu klasöre gelin (`cd` komutuyla), şunu yazın:
   ```
   chmod +x baslat_mac.command
   ```
   Sonra tekrar çift tıklayın.
4. Bir Terminal penceresi açılacak; otomatik olarak sanal ortam kurup gerekli paketleri indirecek (ilk seferde ~1-2 dakika, internet gerekir), ardından tarayıcıda otomatik olarak şu adres açılacak:
   **http://127.0.0.1:8000/app**

### 3. Windows'ta çalıştırma

1. Bu klasördeki **`baslat_windows.bat`** dosyasına çift tıklayın.
2. *"Windows PC'nizi korudu"* uyarısı çıkarsa: **Diğer bilgiler → Yine de çalıştır**.
3. Gerisi otomatik — paketler kurulur, tarayıcı açılır.

### 4. Kapatma

Açılan Terminal/Komut İstemi penceresinde **Ctrl+C** tuşlayın, ya da pencereyi doğrudan kapatın.

Herhangi bir sorunla karşılaşırsanız adım adım çözümler için **`BASLAT_OKU.txt`** dosyasına bakın.

---

## Arayüz — 12 Sekme (Firma 9 · Kamu 4)

Arayüz iki persona ile açılır (üstteki Firma/Kamu anahtarı). 7 sekme gömülü veriyle çevrimdışı çalışır; 5 sekme (Optimizasyon, Fiyat, Etki, Menşe, Görüntü) gerçek backend açıksa canlı çalışır.

| Sekme | Persona | İçerik |
|---|---|---|
| Genel Bakış | ortak | Canlı KPI'lar, uçtan uca akış, formül kırılımı, skor dağılımı |
| DMP Oluştur | firma | Pasaport formu → anında tutarsızlık kontrolü + canlı en iyi eşleşme |
| Pazar & Eşleştirme | firma | Talep seç → sıralı eşleşmeler → açıklanabilir skor kırılımı + menzil haritası |
| Fiyat & Endeks *(canlı)* | firma | Fire endeksi (lif×kalite×bölge) + hedonik fiyat önerisi |
| Menşe & Güven *(canlı)* | firma | Pasaport zaman tüneli (SHA-256) + QR + GRS PDF / DPP JSON-LD |
| Görüntü Zekâsı *(canlı)* | firma | Fotoğraftan renk/doku/kontaminasyon + gerçek MobileNet CNN (tarayıcıda) |
| Optimizasyon *(canlı)* | firma | Pareto slider (karbon/maliyet/mesafe/değer) + kaskad Sankey/MFA |
| Mevzuat & Uygunluk | firma | Çift mevzuat uygunluğu (yasal + firma) → UYGUN/UYARI/ENGELLİ |
| Neden ReLoop? | firma | Anti-aracı karşılaştırması: komisyon + kör-teklif + escrow |
| Kamu Panosu | kamu | Anonim-agrega metrikler + ulusal harita + etki eşdeğerliği |
| UÇBS / TABS | kamu | Atık kodu 04 02 22 ile örnek JSON + şema doğrulaması |
| Etki & Politika *(canlı)* | kamu | İklim çerçevesi (2053 net-sıfır · 2030 NDC · AB ESPR/DÜP) + simülatör |

## Gerçek Backend — `backend/` (FastAPI)

```
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger arayüzü: http://127.0.0.1:8000/docs

63 testi çalıştırmak için: `pip install -r requirements-dev.txt` sonra `pytest -q`

## Eşleştirme Formülü

**Aşama 1 — Sert filtre:** kontaminant elastan eşik altında · miktar ≥ 100 kg · kalite taban üzeri · mesafe ≤ 150 km

**Aşama 2 — Kademeli skor (0-1):**
`MatchScore = 0.30×lif + 0.20×lojistik + 0.15×miktar + 0.15×fiyat + 0.10×kalite + 0.10×güven`

## Dürüstlük Notu

- Etki metrikleri **varsayım** etiketlidir (CO₂ 1,6 kg/kg konservatif, su 2100 L/kg; lif düzeyinde). Kaynak: PE-International/Miljögiraff + ecoinvent (Şartname md. 10.9).
- Kamu Panosu, ulusal sentetik taban anlık görüntüsünü gösterir: **110/250 eşleşme · %44 başarı · 80,6 ton yönlendirilen · %80 ortalama skor**.
- Görüntü zekâsı (renk/doku/kontaminasyon) istemci tarafında gerçektir; lif ailesi sınıflandırması few-shot **kavram kanıtıdır**.
- Kör teklif → pazarlık → escrow gerçek bir istemci-taraflı durum makinesidir.

## Motor Dosyaları

| Dosya | İçerik |
|---|---|
| `reloop.py` | Ontoloji, DMP tutarsızlık kontrolü, iki aşamalı eşleştirme |
| `seed.py` | Sentetik seed: 80 fabrika, 250 fire partisi, 60 alıcı talebi (deterministik, seed=42) |
| `build_app.py` | Şablon + veri → `reloop_app.html` (tek dosya) |
| `parite_testi.js` | JS motoru == Python motoru doğrulaması (20 kontrol) |
