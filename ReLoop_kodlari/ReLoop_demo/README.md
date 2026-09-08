# ReLoop — Döngüsel Tekstil Platformu (çalışan demo)

Ön Değerlendirme Raporu Bölüm 6-9'daki **açıklanabilir iki aşamalı eşleştirme motorunun**
çalışan uygulaması **ve** jüriye açılıp kullanılabilen, internetsiz çalışan **tek dosyalık
web sistemi**. Sentetik veri kullanır (Şartname md.5.2/10.7 — açıkça serbest).
Harici bağımlılık yoktur (motor: Python 3 standart kütüphanesi; arayüz: saf HTML/JS/SVG, CDN yok).

## macOS'ta çalıştırma (arkadaşına gönderilecek — EN KOLAY yol)
Klasörün tamamını (`ReLoop_demo/`) gönder. macOS'ta:

1. **`baslat_mac.command`** dosyasına **çift tıkla**.
   - İlk açılışta uyarı çıkarsa: sağ tıkla → **Aç** → **Aç** (Gatekeeper bir kereliktir).
   - Script kendi sanal ortamını kurar, bağımlılıkları yükler (ilk sefer ~1–2 dk),
     backend'i başlatır ve tarayıcıda arayüzü açar.
2. Tarayıcı otomatik açılır: **http://127.0.0.1:8000/app** — **12 sekmenin hepsi canlıdır**
   (arayüz backend'in kendisinden servis edilir → aynı origin, `?api=` yok, CORS yok).
3. Kapatmak için Terminal penceresinde **Ctrl+C**.

> Neden bu yol? Arayüzü backend servis edince `file://` sürtünmesi ortadan kalkar ve
> canlı sekmeler ("Optimizasyon/Fiyat/Etki/Menşe/Görüntü") otomatik dolar — "sayfalar
> gözükmüyor" sorunu bununla biter (bkz. **Sorun giderme**).

**Windows'ta:** `baslat_windows.bat` dosyasına çift tıkla (aynı iş). Adım adım tarif
için klasördeki **`BASLAT_OKU.txt`** dosyasına bak.

Elle çalıştırmak isteyen için (aynı sonuç):
```bash
cd ReLoop_demo/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # YALIN liste (SQLite; psycopg GEREKMEZ → kurulum patlamaz)
uvicorn app.main:app --host 127.0.0.1 --port 8000
# sonra tarayıcıda:  http://127.0.0.1:8000/app
```
> **Kurulum notu:** `requirements.txt` bilerek yalındır (yalnızca hazır "wheel"i olan
> paketler) → macOS/Windows'ta derleme gerektirmez, `pip install` takılmaz. PostgreSQL
> sürücüsü (`psycopg`) yalnızca prod için ayrı listede: `requirements-postgres.txt`.
> Testler için: `requirements-dev.txt`.

## Sorun giderme — "sayfalar gözükmüyor"
- **En sağlam çözüm:** arayüzü `reloop_app.html`'e çift tıklayarak DEĞİL,
  **backend üzerinden** aç → `http://127.0.0.1:8000/app`. Böylece 12 sekme de canlı gelir.
- Sadece `reloop_app.html`'e çift tıklarsan **7 sekme çevrimdışı çalışır**; 5 canlı sekme
  (Optimizasyon/Fiyat/Etki/Menşe/Görüntü) "backend gerektirir" der. Onları doldurmak için
  backend'i başlat (yukarıdaki `baslat_mac.command`).
- Ayrı makinede backend çalışıyorsa arayüzü `?api=` ile bağla:
  `reloop_app.html?api=http://SUNUCU:8000`.
- Port 8000 doluysa: `uvicorn ... --port 8010` ver, arayüzü `.../app` ile o porttan aç.

## Hızlı başlangıç (geliştirici / yeniden derleme)
```bash
python3 run_demo.py      # konsol demosu + dashboard.html (kamu metrikleri)
python3 build_app.py     # -> reloop_app.html  (çift tıklayıp tarayıcıda aç)
node    parite_testi.js  # JS motoru == Python motoru + dashboard sayıları (20 kontrol)
python3 figures.py       # rapor görselleri: figures/*.png
```
**`reloop_app.html`** bitmiş sistem arayüzüdür: çift tıkla, tarayıcıda açılır, sunucu gerekmez
(7 sekme çevrimdışı). 12 sekmenin **tamamı canlı** olsun istersen backend'den `/app` ile aç.

## Arayüz — `reloop_app.html` (12 sekme · **firma 9 · kamu 4**, "Genel Bakış" ortak)
Arayüz iki persona ile açılır (üstteki **Firma / Kamu** anahtarı): firma tarafı 9, kamu tarafı 4
sekme görür. **7 sekme** gömülü veriyle **çevrimdışı** çalışır (sunucu gerekmez); **5 sekme**
(Optimizasyon, Fiyat, Etki, Menşe, Görüntü) gerçek backend AÇIKSA **canlı** verilenir, kapalıysa
"backend'e bağlanın" der (sahne güvenliği). Backend adresi `?api=http://SUNUCU:8000` ile verilir;
header'da **● Canlı API** rozeti yanar.
| Sekme | Persona | İçerik |
|---|---|---|
| **Genel Bakış** | ortak | Canlı KPI'lar, uçtan uca akış, formül kırılımı, skor dağılımı, TRL/kimlik rozetleri |
| **DMP Oluştur** | firma | Pasaport formu → **anında tutarsızlık kontrolü** + canlı en iyi eşleşme + **"Pazara ekle"** (`localStorage`) |
| **Pazar & Eşleştirme** | firma | Talep seç → sıralı eşleşmeler → **açıklanabilir skor kırılımı** + **menzil haritası** + **kör teklif → pazarlık → escrow durum makinesi** |
| **Fiyat & Endeks** *(canlı)* | firma | ReLoop fire endeksi (lif×kalite×bölge) + haftalık trend + **hedonik fiyat önerisi** (R²≈0,97) |
| **Menşe & Güven** *(canlı)* | firma | Pasaport zaman tüneli (SHA-256) + zincir doğrulama + **QR** + Açık DMP sayfası / **GRS PDF** / **DPP JSON-LD** |
| **Görüntü Zekâsı** *(canlı)* | firma | Fotoğraftan renk/doku/kontaminasyon (istemci-taraflı) + **gerçek MobileNet CNN tarayıcıda** (sunucu inference yok) → lif ailesi few-shot tahmini → "DMP'ye aktar". Model backend'den yerel servis (`/vendor`, CDN yok) |
| **Optimizasyon** *(canlı)* | firma | Pareto slider (karbon/maliyet/mesafe/değer) → anlık yeniden sıralama + **Pareto cephesi** + **kaskad Sankey/MFA** + proaktif tahmin/bildirim |
| **Mevzuat & Uygunluk** | firma | Parti → 8 firma için **çift mevzuat uygunluğu** (yasal: UÇBS beyan tutarlılığı · firma: elastan/kalite/lot/GRS eşiği) → **UYGUN/UYARI/ENGELLİ** gerekçeli; her satırda "Kaynak:" etiketi (dürüstlük) |
| **Neden ReLoop?** | firma | **Anti-aracı moat**: komisyon + kör-teklif + escrow karşılaştırması → aracıyı atlamanın net kazancı (canlı hesaplayıcı) + "güvenilir ticari ray" tezi |
| **Kamu Panosu** | kamu | Anonim-agrega metrikler + **ulusal harita** (10 şehir) + etki eşdeğerliği + skor dağılımı |
| **UÇBS / TABS** | kamu | Ulusal Çevre Bilgi Sistemi (UÇBS, 19.12.2025'ten beri EÇBS'nin yerine) · atık kodu 04 02 22 ile örnek JSON + **istemci-taraflı şema doğrulaması** (KVKK dahil) |
| **Etki & Politika** *(canlı)* | kamu | İklim çerçevesi (**2053 net-sıfır · 2030 NDC · ulusal ETS · AB ESPR/DÜP**) + simülatör slider'ları + atık önleme + CO₂/su/enerji + **birim ekonomisi & 3 katmanlı gelir** + bölgesel ısı haritası |

Arayüzdeki JS motoru `reloop.py`'yi **birebir yansıtır** (aynı sabitler `build_app.py` ile gömülür);
paritesi `node parite_testi.js` ile **otomatik doğrulanır** (20 kontrol: init + her sekme render yolu +
dashboard sayıları + §9 + çift mevzuat uygunluğu + şema doğrulayıcı). Erişilebilirlik: WAI-ARIA tablist klavye deseni, liste
klavye navigasyonu, focus-visible; iki mobil kırılım (≤900px, ≤480px).

**Cila:** tutarlı inline-SVG ikon seti (emoji yok — platformdan bağımsız), KPI count-up animasyonu,
toast/boş-durum/mikro-etkileşim, `prefers-reduced-motion` desteği.

## Gerçek backend — `backend/` (FastAPI + PostgreSQL)
İşlem/güven zinciri **kalıcı veritabanına** yazar; motor `reloop.py`'yi birebir kullanır.
```bash
cd backend
pip install -r requirements.txt              # yalın (SQLite; demo/geliştirme)
uvicorn app.main:app --reload                # SQLite otomatik seed · Swagger: /docs
# ya da: docker compose up --build           # PostgreSQL (requirements-postgres.txt)
pip install -r requirements-dev.txt && PYTHONPATH=. pytest -q   # 63 test (dev listesi)
```
**63 uç:** DMP CRUD + hash zinciri · eşleştirme/kaskad/lot-merge/Pareto/proaktif · ticari zincir
(teklif→emanet→sevkiyat→teslim doğrulama→tamamla/uyuşmazlık) · QR/açık DMP/GRS PDF · fiyat
endeksi/hedonik · DPP JSON-LD/ESPR · NDC/simülatör/karbon sertifikası PDF · UÇBS/TABS uyum/denetim/açık veri.
**Yetkilendirme (varsayılan AÇIK):** Durum-değiştiren uçlar `X-API-Key` ile doğrulanır; rol
**kimlikten türetilir** (self-declared değil). `RELOOP_REQUIRE_AUTH` varsayılanı **açıktır**;
kapatmak için `RELOOP_REQUIRE_AUTH=false`. Yıkıcı `/admin/*` uçları `X-Admin-Key` ister; demo
anahtarı `reloop-admin-demo` (prod'da `RELOOP_ADMIN_KEY` ile MUTLAKA değiştir). Demo API anahtarları
(seed'de): `demo-seller-key` · `demo-recycler-key` · `demo-auditor-key` · `demo-ministry-key`.
Arayüz canlı POST'larda (`/passports`, `/matching/forecast`) `demo-seller-key`'i otomatik gönderir;
curl örneği: `-H "X-API-Key: demo-seller-key"`. Ticari zincir arayüzde çevrimdışı simüle edilir.

### Demo akışı (jüri anı)
1. `uvicorn` başlat → `reloop_app.html`'i `?api=127.0.0.1:8000` ile aç → **● Canlı API** yanar.
2. **Optimizasyon**: Pareto slider'larını oynat → eşleşmeler canlı yeniden sıralanır.
3. **Menşe & Güven**: partinin QR'ını okut → telefonda **doğrulanmış menşe sayfası**; NFC etiketine dokun.
4. **Etki & Politika**: simülatör slider'ıyla ulusal CO₂ katkısı + iklim çerçevesi (2053 net-sıfır · 2030 NDC · ulusal ETS).
5. Swagger'da işlem zincirini canlı koştur → kayıtların **gerçek DB'ye** yazıldığını göster.

## Motor dosyaları
| Dosya | İçerik |
|---|---|
| `reloop.py` | Ontoloji, DMP tutarsızlık kontrolü, **iki aşamalı eşleştirme** (sert filtre + **kademeli** ağırlıklı skor), açıklanabilir çıktı |
| `seed.py` | Sentetik seed: 80 fabrika (hepsi aktif), 250 fire partisi (DMP), 60 alıcı talebi. Lif↔kumaş **tutarlı**; ~%6 **kasıtlı ekilmiş** gerçek tutarsızlık. Deterministik (`seed=42`) |
| `run_demo.py` | Konsol demosu: tutarsızlık örneği, §9 örnek hesabı, örnek eşleşmeler, kamu dashboard + `dashboard.html` |
| `build_app.py` | `app_shell.template.html` + veri + Türkiye sınırı → `reloop_app.html` (tek dosya) |
| `app_shell.template.html` | Arayüz **şablonu** (veri `__RELOOP_DATA__` yer tutucusuna gömülür; doğrudan açılmaz — `build_app.py` üretir ya da `/app` sunar) |
| `turkiye_sinir.json` | Basitleştirilmiş Türkiye sınırı (offline; build anında ulusal haritaya gömülür) |
| `parite_testi.js` | Node testi: JS motoru == Python + rapor sayıları + sekme duman testi |
| `figures.py` | Rapor görselleri → `figures/*.png` |

## Eşleştirme formülü (rapor Bölüm 6 ile birebir)
```
Aşama 1 — Sert filtre: kontaminant elastan ≤ eşik · miktar ≥ 100 kg · kalite ≥ taban
                        · pamuk ≥ istenen · fiyat ≤ tavan · mesafe ≤ 150 km · (doğrulama şartı)
Aşama 2 — KADEMELİ skor (0–1):
  MatchScore = 0.30·f_lif + 0.20·f_lojistik + 0.15·f_miktar + 0.15·f_fiyat + 0.10·f_kalite + 0.10·f_güven
```
- `f_lif` = pamuk saflığı − kontaminant cezası (polyester hafif, elastan ağır)
- `f_lojistik` = mesafe sönümü · `f_miktar` = talep karşılama oranı · `f_fiyat` = bütçe marjı (kademeli)
- `f_kalite` = A 1.00 / B 0.80 / C 0.60 · `f_güven` = **itibar + doğrulama + tutarlılıktan türetilir** (rasgele değil)

Hiçbir bileşen sert filtreden sonra "ölü sabit" değildir → skorlar tek noktada kümelenmez,
ekosistemi gerçekten sıralar (demo: ~%68–%99 aralığı). Ağırlıklar alan-türevlidir; veri
biriktikçe learning-to-rank ile öğrenilir.

## Dürüstlük notu
- Etki metrikleri **VARSAYIM** etiketlidir (CO₂ 1,6 kg/kg konservatif [ecoinvent üst ~2,93],
  su 2100 L/kg; lif düzeyi). Kaynaklı katsayılar: PE-International/Miljögiraff + ecoinvent (md.10.9).
- Kör teklif → pazarlık → escrow **gerçek bir istemci-taraflı durum makinesidir** (deterministik
  üretici politikası; uydurma fiyat çarpanı yoktur). TABS gönderiminde **doğrulama gerçektir**,
  yalnızca ağ çağrısı (kimlik doğrulamalı REST/OGC) örnektir — sahte "200 OK" kaldırılmıştır.
- Kamu Panosu, ulusal sentetik taban anlık görüntüsünü (**110/250 eşleşme · %44 başarı · 80,6 ton
  yönlendirilen · %80 ort. skor**) gösterir; kullanıcı "Pazara ekle" kayıtları yalnızca Pazar/eşleştirmeye katılır.
- Görüntü zekâsı (renk/doku/kontaminasyon + MobileNet CNN) **istemci tarafında gerçektir**; lif ailesi
  sınıflandırması few-shot **kavram kanıtıdır** (üretimde gerçek pilot foto setiyle eğitilir). WhatsApp
  akışı yol haritasındadır.
- Etki metriklerinde "yönlendirilen ton", tamamlanmış işlemi değil **önerilen eşleşmeyi** esas alan
  konservatif üst-sınır sayımıdır (harmanlı partileri de kapsar).
