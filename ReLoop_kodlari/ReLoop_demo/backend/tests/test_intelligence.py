"""
Dalga 3 — eşleştirme zekâsı testleri: kaskad (yerleşim %100), lot birleştirme,
Pareto çok-amaçlı (ağırlık → yeniden sıralama + cephe), proaktif tahmin + bildirim,
"neden eşleşmedi", ontoloji, ağırlık öğrenme kancası.
"""


def _hub_factory_id(client, city="Uşak"):
    """Alıcıların bulunduğu bir merkez şehirdeki satıcı fabrika id'si. Ulusal veride
    fabrika 1 alıcıya uzak bir ilde olabilir → forecast eşleşmesi için hub fabrika seç."""
    facs = client.get("/public/factories", params={"role": "seller"}).json()
    return next(f["id"] for f in facs if f["city"] == city)


def test_cascade_full_placement(client):
    s = client.get("/matching/cascade-summary").json()
    assert s["placement_rate_pct"] == 100.0                       # hiçbir fire yerleşimsiz kalmaz
    assert sum(s["channels"].values()) == s["total"]
    assert s["channels"]["textile"] > 0                           # tekstil-önce çekirdek korunur


def test_cascade_single_textile(client):
    # Taze, yüksek saflıkta bir parti oluştur (paylaşılan DB mutasyonlarından bağımsız)
    b = client.post("/passports", json={
        "factory_id": 1, "city": "Uşak", "lat": 38.68, "lon": 29.41,
        "pamuk": 100, "polyester": 0, "elastan": 0, "kumas": "suprem",
        "gramaj": 180, "en_m": 1.8, "miktar_kg": 800, "kalite": "A", "min_fiyat": 18}).json()
    r = client.get(f"/matching/cascade/{b['code']}").json()
    assert r["cascade"]["tier"] == 1                              # %100 pamuk A → tekstil rotası
    assert r["cascade"]["channel"] == "textile"


def test_lot_merge(client):
    lm = client.get("/matching/demand/T001/lot-merge").json()
    assert lm["need_kg"] > 0
    assert lm["lots"] >= 1
    if lm["covers"]:
        assert lm["total_kg"] >= lm["need_kg"]


def test_pareto_reranks_and_front(client):
    carbon = client.get("/matching/demand/T001/pareto",
                        params={"w_carbon": 0.7, "w_cost": 0.1, "w_distance": 0.1, "w_value": 0.1}).json()
    dist = client.get("/matching/demand/T001/pareto",
                     params={"w_carbon": 0.1, "w_cost": 0.1, "w_distance": 0.7, "w_value": 0.1}).json()
    assert carbon["ranked"] and dist["ranked"]
    # sıralama pareto_score'a göre azalan
    scores = [r["pareto_score"] for r in carbon["ranked"]]
    assert scores == sorted(scores, reverse=True)
    # Pareto cephesi boş değil ve domine edilmeyenleri içerir
    assert len(carbon["front"]) >= 1
    # Pozitif-ağırlıklı toplamın argmax'ı daima domine edilmeyendir → #1 cephede olmalı.
    assert dist["ranked"][0]["on_front"] is True
    # Mesafe ağırlığı baskınken (0.7) #1 adayın mesafesi, sıralı listenin
    # ortancasından büyük olmamalı (yakınlık gerçekten önceliklendiriliyor).
    ds = sorted(r["distance_km"] for r in dist["ranked"])
    assert dist["ranked"][0]["distance_km"] <= ds[len(ds) // 2] + 1e-6


def test_pareto_does_not_leak_reserve_price(client):
    """Pareto 'cost' ekseni PİYASA REFERANS fiyatını verir; satıcının gizli rezervini
    (Batch.min_fiyat, kör teklifte kullanılır) ASLA dışa vermez. Rezervi sızdırmak
    kör-teklif moat'ını çökertirdi (denetim bulgusu)."""
    r = client.get("/matching/demand/T001/pareto").json()
    assert r["ranked"]
    from app import pricing as P
    from app.db import SessionLocal
    from app.models import Batch
    db = SessionLocal()
    try:
        for row in r["ranked"]:
            b = db.query(Batch).filter(Batch.code == row["batch_code"]).first()
            # Güvence: cost = PİYASA REFERANS fiyatı (ref_price), ham rezerv DEĞİL.
            assert abs(row["cost"] - P.ref_price(b)) < 1e-6, \
                f"{row['batch_code']}: cost referans fiyat olmalı, rezerv değil"
    finally:
        db.close()


def test_rejections_have_reasons(client):
    rj = client.get("/matching/demand/T001/rejections").json()
    assert isinstance(rj, list)
    if rj:
        assert all("reason" in x for x in rj)


def test_forecast_creates_notifications(client):
    r = client.post("/matching/forecast", json={
        "factory_id": _hub_factory_id(client), "monthly_kg": 40000, "fire_rate_pct": 5,
        "kumas": "suprem", "pamuk": 100, "polyester": 0, "elastan": 0,
        "gramaj": 180, "kalite": "A"}).json()
    assert r["forecast_fire_kg"] == 2000.0                        # 40000 * 5%
    n = client.get("/notifications").json()
    assert len(n) >= 1
    assert n[0]["kind"] == "prematch"


def test_forecast_notifications_idempotent(client):
    # REGRESYON: aynı forecast tekrar çağrılınca bildirim ŞİŞMEMELİ (dedup)
    body = {"factory_id": 1, "monthly_kg": 30000, "fire_rate_pct": 5,
            "kumas": "suprem", "pamuk": 100, "polyester": 0, "elastan": 0,
            "gramaj": 180, "kalite": "A"}
    client.post("/matching/forecast", json=body)
    n1 = len(client.get("/notifications").json())
    client.post("/matching/forecast", json=body)
    client.post("/matching/forecast", json=body)
    n2 = len(client.get("/notifications").json())
    assert n2 == n1                                                # tekrarda yeni bildirim yok


def test_reseed_clears_notifications_and_rejects_bad_dataset(client):
    # REGRESYON: reseed bayat bildirimleri temizler (#3) + geçersiz dataset 400 (#4)
    client.post("/matching/forecast", json={
        "factory_id": _hub_factory_id(client), "monthly_kg": 30000, "fire_rate_pct": 5,
        "kumas": "suprem", "pamuk": 100, "polyester": 0, "elastan": 0,
        "gramaj": 180, "kalite": "A"})
    assert len(client.get("/notifications").json()) >= 1
    client.post("/admin/seed", params={"dataset": "canonical"})
    assert client.get("/notifications").json() == []               # reseed bildirimleri sildi
    bad = client.post("/admin/seed", params={"dataset": "HEDEFYOK"})
    assert bad.status_code == 400                                   # geçersiz dataset reddedilir


def test_ontology_and_learn(client):
    on = client.get("/matching/ontology").json()
    keys = [r["key"] for r in on["routes"]]
    assert "textile" in keys and "rdf" in keys
    lr = client.get("/matching/learn").json()
    assert "current" in lr                                        # canlı ağırlıklar korunur (öneri ayrı)
