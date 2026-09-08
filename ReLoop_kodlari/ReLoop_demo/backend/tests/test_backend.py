"""
Dalga 1 backend testleri:
  • sağlık + kimlik
  • kanonik dashboard motor tutarlılığı (110/250 · 80,6 ton · 129 ton CO₂ konservatif · su 169,3 M L · %80 · 15 uyarı)
  • DMP listesi/oluşturma + tutarsızlık dedektörü
  • motor eşitliği (engine_service == reloop çekirdeği)
  • SHA-256 hash zinciri: geçerlilik + kurcalama (tamper) tespiti
  • yarı-gerçek ikinci koşu yüklenebiliyor
"""
from app.chain import event_hash, verify_chain


def test_root_health(client):
    assert client.get("/").json()["engine"].startswith("reloop.py")
    assert client.get("/health").json()["status"] == "ok"


def test_canonical_dashboard_engine_consistency(client):
    """Kamu dashboard değerleri motorla tutarlı (ULUSAL veri seti; rapor sabiti değil —
    aynı sayılar reloop.py/JS motorunda da üretilir, parite_testi.js doğrular)."""
    d = client.get("/public/dashboard").json()
    assert d["dataset"] == "canonical"
    assert (d["batches"], d["demands"]) == (250, 60)
    assert d["matched"] == 110                     # ulusal: 110/250 (%44)
    assert d["routed_tonnes"] == 80.6
    assert d["co2_tonnes_conservative"] == 129.0
    assert 230 <= d["co2_tonnes_ecoinvent"] <= 240
    assert d["water_million_l"] == 169.3           # 2100 L/kg
    assert d["factories"] == 80                    # 80 satıcı fabrika
    assert 0 < d["absorbed_tonnes"] <= d["routed_tonnes"]  # konservatif ≤ potansiyel
    assert d["avg_score_pct"] == 80.0
    assert d["inconsistencies_flagged"] == 15      # ~%6 kasıtlı tutarsızlık


def test_passport_list_and_get(client):
    ps = client.get("/passports", params={"limit": 5}).json()
    assert len(ps) == 5
    one = client.get(f"/passports/{ps[0]['code']}").json()
    assert one["code"] == ps[0]["code"]
    assert one["waste_code"] == "04 02 22"
    # Satıcının kör-teklif rezervi (min_fiyat) API'de AÇILMAMALI
    assert "min_fiyat" not in one and "min_fiyat" not in ps[0]


def test_inconsistency_detector(client):
    # polar tipik polyesterdir; %70 pamuk + aralık dışı gramaj → iki uyarı
    u = client.post("/passports/check", json={
        "factory_id": 1, "city": "Uşak", "lat": 38.68, "lon": 29.41,
        "pamuk": 70, "polyester": 30, "elastan": 0, "kumas": "polar",
        "gramaj": 600, "en_m": 1.8, "miktar_kg": 500, "kalite": "B", "min_fiyat": 18,
    }).json()
    assert len(u) >= 2
    assert any("polar" in x for x in u)


def test_create_dmp_and_chain(client):
    r = client.post("/passports", json={
        "factory_id": 1, "city": "Uşak", "lat": 38.68, "lon": 29.41,
        "pamuk": 100, "polyester": 0, "elastan": 0, "kumas": "suprem",
        "gramaj": 180, "en_m": 1.8, "miktar_kg": 800, "kalite": "A",
        "min_fiyat": 18, "dogrulanmis": True,
    })
    assert r.status_code == 201
    code = r.json()["code"]
    ev = client.get(f"/passports/{code}/events").json()
    assert ev["verification"]["valid"] is True
    assert ev["chain"][0]["event_type"] == "DMP_CREATED"


def test_engine_equivalence():
    """engine_service çekirdeği DEĞİŞTİRMEZ — reloop.py ile birebir aynı skor."""
    import reloop as R
    from app import engine_service as ES
    from app.models import Batch, Demand, Factory

    b = Batch(code="P-X", factory_id=1, city="Uşak", lat=38.680, lon=29.410,
              pamuk=100, polyester=0, elastan=0, kumas="suprem", gramaj=180,
              en_m=1.8, miktar_kg=800, kalite="A", min_fiyat=18, depo_gun=20,
              dogrulanmis=True, reputation=0.85)
    b.factory = Factory(name="X", city="Uşak", lat=38.68, lon=29.41)
    d = Demand(code="T-X", buyer="Y", city="Uşak", lat=38.905, lon=29.410,
               min_pamuk=95, max_elastan=0, ihtiyac_kg=1000, max_fiyat=22, min_kalite="B")

    wrapped = ES.score_pair(b, d)["score"]
    p, t = ES.batch_to_parti(b), ES.demand_to_talep(d)
    direct = R.match_score(R.skorla(p, t)["bilesen"])
    assert abs(wrapped - round(direct, 4)) < 1e-9
    assert abs(direct - 0.8995) < 0.01   # rapor §9 örneği ≈ %90


def test_hash_chain_tamper_detection(client):
    """Bir olayın payload'ı değişirse zincir doğrulaması BOZULMALI."""
    from app.db import SessionLocal
    from app.models import Batch, PassportEvent

    db = SessionLocal()
    try:
        b = db.query(Batch).first()
        events = list(db.query(PassportEvent)
                        .filter(PassportEvent.batch_id == b.id).all())
        assert verify_chain(events)["valid"] is True
        # Kurcala: genesis payload'ını değiştir (hash sabit kalır → tutmaz)
        ev0 = events[0]
        tampered_payload = dict(ev0.payload)
        tampered_payload["miktar_kg"] = tampered_payload.get("miktar_kg", 0) + 999
        recomputed = event_hash(ev0.prev_hash, ev0.seq, ev0.event_type, tampered_payload)
        assert recomputed != ev0.hash   # değişiklik hash'i bozar → tamper-evident
    finally:
        db.close()


def test_opendata_aggregate_no_pii(client):
    d = client.get("/public/opendata/aggregate").json()
    assert d["regions"] and all("region" in r and "total_tonnes" in r for r in d["regions"])
    # anonim: firma adı / kesin fiyat alanı yok
    assert all("factory" not in r and "name" not in r for r in d["regions"])


def test_opendata_records_anonymized(client):
    d = client.get("/public/opendata/records", params={"kumas": "suprem", "limit": 5}).json()
    assert d["count"] >= 1
    r = d["records"][0]
    assert set(r) >= {"region", "fiber_class", "kumas", "kalite", "qty_band_kg"}
    assert "factory" not in r and "min_fiyat" not in r   # kimlik/kesin fiyat gizli


def test_semireal_second_run(client):
    r = client.post("/admin/seed", params={"dataset": "semireal"}).json()
    assert r["dataset"] == "semireal"
    assert r["batches"] == 400
    d = client.get("/public/dashboard").json()
    assert d["dataset"] == "semireal"
    assert d["batches"] == 400 and d["matched"] > 0
    # Kanoniğe geri dön (diğer testler etkilenmesin — session fixture paylaşımlı)
    client.post("/admin/seed", params={"dataset": "canonical"})
