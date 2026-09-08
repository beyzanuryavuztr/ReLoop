# ReLoop Backend — Gerçek İşlem Omurgası (FastAPI + PostgreSQL)

Döngüsel tekstil için **güvenilir ticari ray**. Tüm işlem/güven zinciri kalıcı bir
veritabanına yazılır; motor `../reloop.py` çekirdeğini **birebir** kullanır (tek doğruluk
kaynağı — arayüz ve rapor da aynı formülü paylaşır).

## Neden bu katman?
Önceki sürüm saf istemci taraflıydı (tek dosya HTML + gömülü JS motoru). Bu backend,
jüriye "gerçek sistem" kanıtı sunar: **kalıcı DB, migrasyonlar, OpenAPI/Swagger,
denetlenebilir hash zinciri**. Arayüz canlıysa buradan okur; backend kapalıysa gömülü
veriyle çevrimdışı çalışmaya devam eder (sahne güvenliği).

## Hızlı başlangıç (yerel, SQLite — sıfır kurulum)
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # macOS/Linux (önerilir)
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000    # http://127.0.0.1:8000
```
İlk açılışta tablolar oluşur ve **kanonik ekosistem** (rapor paritesi: 80 fabrika /
250 parti / 60 talep, seed=42) otomatik yüklenir.

- **Arayüz:** <http://127.0.0.1:8000/app>  ← backend'in servis ettiği tek sayfa;
  aynı origin olduğu için **12 sekme de canlı** gelir (`?api=` / CORS gerekmez).
- Swagger: <http://127.0.0.1:8000/docs>
- Sağlık:  <http://127.0.0.1:8000/health>

> macOS'ta tek tık: kök klasördeki **`baslat_mac.command`** dosyasına çift tıkla —
> venv + kurulum + backend + tarayıcı otomatik.

## Prod (PostgreSQL — docker-compose)
```bash
cd backend
docker compose up --build               # api + postgres, migrasyonlar otomatik
```
`RELOOP_DATABASE_URL` ile herhangi bir Postgres'e bağlanabilirsin (bkz. `.env.example`).

## Migrasyonlar (Alembic)
```bash
PYTHONPATH=. alembic upgrade head                 # şemayı uygula
PYTHONPATH=. alembic revision --autogenerate -m "…"  # yeni migrasyon
```

## Testler
```bash
PYTHONPATH=. pytest -q
```
Kapsam: dashboard paritesi (110/250 · %44 eşleşme · 129 t CO₂ · 15 uyarı), motor eşitliği
(`engine_service == reloop.py`), **SHA-256 hash zinciri + kurcalama (tamper) tespiti**,
tutarsızlık dedektörü, yarı-gerçek ikinci koşu.

## İki veri seti
| Veri seti | Ne | Amaç |
|---|---|---|
| `canonical` | `../seed.py` (80/250/60, seed=42) | **Rapor paritesi** — sertifikalı anlık görüntü |
| `semireal`  | `app/seed_semireal.py` (120/400/90, gerçek OSB coğrafyası, seed=2026) | **İkinci bağımsız test koşusu** (#2), dürüst raporlanır |

`POST /admin/seed?dataset=canonical|semireal` ile geçiş.

## Uç noktalar (Dalga 1)
| Grup | Uç | Açıklama |
|---|---|---|
| Sistem | `GET /`, `GET /health` | kimlik + sağlık |
| DMP | `GET /passports`, `GET /passports/{code}` | pasaport listesi/tekil |
| DMP | `POST /passports` | yeni DMP (tutarsızlık + genesis hash olayı) |
| DMP | `POST /passports/check` | aday DMP tutarsızlık kontrolü (kaydetmeden) |
| DMP | `GET /passports/{code}/events` | **hash zinciri + doğrulama** |
| Talep | `GET /demands`, `GET /demands/{code}` | talep listesi/tekil |
| Eşleştirme | `GET /matching/demand/{code}` | sıralı, açıklanabilir eşleşmeler |
| Eşleştirme | `GET /matching/batch/{code}` | bir parti için en iyi talep |
| Kamu | `GET /public/dashboard` | anonim/agrega metrikler + varsayım/kaynak |
| Kamu | `GET /public/factories` | aktörler (harita) |
| Yönetim | `POST /admin/seed` | ekosistemi yükle/yenile |

> Sonraki dalgalar bu omurgaya ticari zinciri (teklif/emanet/teslim), güven rayını
> (QR/NFC/GRS PDF), fiyat endeksini, AB-DPP export'unu ve kamu/politika etki motorunu
> ekleyecek — hepsi aynı DB'ye ve aynı hash zincirine yazar.

## Mimari kural
`reloop.py` **tek motor doğruluk kaynağıdır**. Backend onu sarar (`app/engine_service.py`),
JS arayüz onu yansıtır, `../parite_testi.js` üçünü senkron tutar. Skor/etki formülü burada
tekrarlanmaz; yalnızca çağrılır. Rapor sayıları korunur.
