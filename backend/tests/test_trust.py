"""
Dalga 2 — güven & menşe rayı testleri:
  • tam ticari zincir (open→accept→escrow→ship→deliver→verified→complete) + itibar +
  • tutarsız teslimde emanet OTOMATİK askı + uyuşmazlık → iade + itibar −
  • hash zinciri yaşam döngüsü boyunca geçerli kalır
  • durum makinesi guard'ları (yanlış sırada 409)
  • QR (svg/png), herkese açık DMP sayfası (NFC), GRS PDF üretimi
"""


def _open_verified_trade(client, demand="T001"):
    m = client.get(f"/matching/demand/{demand}", params={"top": 1}).json()[0]
    bcode = m["batch_code"]
    tx = client.post("/trade/open", json={"batch_code": bcode, "demand_code": demand}).json()
    return bcode, tx["code"]


def _agree(client, tx, amount, qty, initiator="seller", accepter="buyer"):
    """İki taraflı mutabakat kısayolu: bir taraf teklif verir, KARŞI taraf kabul eder.
    (Tek-tık 'accept' artık yasak — önce ortada bir teklif olmalı.)"""
    client.post(f"/trade/{tx}/bid",
                json={"by_role": initiator, "kind": "bid", "amount": amount, "qty_kg": qty})
    return client.post(f"/trade/{tx}/bid",
                       json={"by_role": accepter, "kind": "accept", "amount": amount, "qty_kg": qty})


def test_full_trade_lifecycle_and_reputation(client):
    bcode, tx = _open_verified_trade(client, "T001")
    before = client.get(f"/passports/{bcode}").json()["reputation"]

    client.post(f"/trade/{tx}/bid", json={"by_role": "buyer", "kind": "bid", "amount": 20, "qty_kg": 800})
    # Karşı taraf (satıcı) son teklifi kabul eder — iki taraflı rıza
    r = client.post(f"/trade/{tx}/bid", json={"by_role": "seller", "kind": "accept", "amount": 20, "qty_kg": 800}).json()
    assert r["transaction"]["status"] == "ACCEPTED"
    assert client.post(f"/trade/{tx}/escrow").json()["status"] == "ESCROW"
    assert client.post(f"/trade/{tx}/ship").json()["status"] == "SHIPPED"

    p = client.get(f"/passports/{bcode}").json()
    d = client.post(f"/trade/{tx}/deliver", json={
        "pamuk": p["pamuk"], "polyester": p["polyester"], "elastan": p["elastan"],
        "kumas": p["kumas"], "gramaj": p["gramaj"], "kalite": p["kalite"],
        "miktar_kg": p["miktar_kg"], "photo_ref": "foto.jpg"}).json()
    assert d["mismatch"] is False
    assert d["transaction"]["status"] == "VERIFIED"
    assert client.post(f"/trade/{tx}/complete").json()["status"] == "COMPLETED"

    after = client.get(f"/passports/{bcode}").json()["reputation"]
    assert after >= before                       # başarılı teslim → itibar artar/korunur
    v = client.get(f"/trust/{bcode}/verify").json()
    assert v["valid"] is True                     # zincir yaşam döngüsü boyunca geçerli
    events = [e["event"] for e in client.get(f"/trust/{bcode}/provenance").json()["timeline"]]
    assert "DELIVERED" in events and "VERIFIED" in events   # teslim + doğrulama adımları görünür


def test_escrow_auto_suspend_on_mismatch(client):
    bcode, tx = _open_verified_trade(client, "T003")
    _agree(client, tx, 20, 500)
    client.post(f"/trade/{tx}/escrow")
    client.post(f"/trade/{tx}/ship")
    bad = client.post(f"/trade/{tx}/deliver", json={"kalite": "C", "elastan": 9, "miktar_kg": 50}).json()
    assert bad["mismatch"] is True
    assert bad["transaction"]["status"] == "SUSPENDED"     # emanet OTOMATİK askıya alındı
    assert set(bad["mismatch_fields"]) & {"elastan", "kalite", "miktar_kg"}

    before = client.get(f"/passports/{bcode}").json()["reputation"]
    client.post(f"/trade/{tx}/dispute", json={"reason": "kalite/elastan uyuşmuyor"})
    rr = client.post(f"/trade/{tx}/resolve", json={"outcome": "refund"}).json()
    assert rr["status"] == "CANCELLED"
    after = client.get(f"/passports/{bcode}").json()["reputation"]
    assert after <= before                        # başarısız teslim → itibar düşer
    assert client.get(f"/trust/{bcode}/verify").json()["valid"] is True


def test_state_machine_guard(client):
    _, tx = _open_verified_trade(client, "T004")
    # OPEN durumunda escrow denemesi → 409
    assert client.post(f"/trade/{tx}/escrow").status_code == 409


def test_qr_and_public_page(client):
    bcode = client.get("/passports", params={"limit": 1}).json()[0]["code"]
    svg = client.get(f"/passports/{bcode}/qr.svg")
    png = client.get(f"/passports/{bcode}/qr.png")
    assert svg.status_code == 200 and svg.headers["content-type"] == "image/svg+xml"
    assert png.status_code == 200 and png.headers["content-type"] == "image/png"
    pub = client.get(f"/public/dmp/{bcode}")
    assert pub.status_code == 200 and bcode in pub.text
    assert "NDEFReader" in pub.text                # gerçek Web NFC kodu
    assert "Menşe zinciri" in pub.text


def test_grs_pdf(client):
    bcode = client.get("/passports", params={"limit": 1}).json()[0]["code"]
    pdf = client.get(f"/trust/{bcode}/grs.pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content[:5] == b"%PDF-"


def test_double_sell_guard_and_inventory(client):
    m = client.get("/matching/demand/T010", params={"top": 1}).json()[0]
    bcode = m["batch_code"]
    tx = client.post("/trade/open", json={"batch_code": bcode, "demand_code": "T010"}).json()["code"]
    # Aynı parti + aktif işlem → 409
    dup = client.post("/trade/open", json={"batch_code": bcode, "demand_code": "T010"})
    assert dup.status_code == 409
    # İşlemi tamamla → parti satılır
    _agree(client, tx, 21, 500)
    client.post(f"/trade/{tx}/escrow"); client.post(f"/trade/{tx}/ship")
    p = client.get(f"/passports/{bcode}").json()
    client.post(f"/trade/{tx}/deliver", json={k: p[k] for k in
                ("pamuk", "polyester", "elastan", "kumas", "gramaj", "kalite", "miktar_kg")})
    client.post(f"/trade/{tx}/complete")
    # Satılmış parti yeni işleme kapalı → 409
    assert client.post("/trade/open", json={"batch_code": bcode, "demand_code": "T010"}).status_code == 409
    # ...ve eşleştirmede artık görünmez
    matches = client.get("/matching/demand/T010", params={"top": 50}).json()
    assert bcode not in [x["batch_code"] for x in matches]


def test_delivery_verification_is_tight(client):
    # Kontaminant sızıntısı kapandı: beyan-0 partide elastan 1.5 artık uyuşmazlık
    m = client.get("/matching/demand/T011", params={"top": 1}).json()[0]
    bcode = m["batch_code"]
    p = client.get(f"/passports/{bcode}").json()
    if p["elastan"] > 0:
        return  # bu test 0-elastan parti gerektirir
    tx = client.post("/trade/open", json={"batch_code": bcode, "demand_code": "T011"}).json()["code"]
    _agree(client, tx, 21, 500)
    client.post(f"/trade/{tx}/escrow"); client.post(f"/trade/{tx}/ship")
    r = client.post(f"/trade/{tx}/deliver", json={
        "pamuk": p["pamuk"], "polyester": p["polyester"], "elastan": 1.5,
        "kumas": p["kumas"], "gramaj": p["gramaj"], "kalite": p["kalite"],
        "miktar_kg": p["miktar_kg"]}).json()
    assert r["mismatch"] is True                      # küçük kontaminant bile yakalanır
    assert r["transaction"]["status"] == "SUSPENDED"


def test_delivery_missing_field_flagged(client):
    m = client.get("/matching/demand/T012", params={"top": 1}).json()[0]
    bcode = m["batch_code"]
    tx = client.post("/trade/open", json={"batch_code": bcode, "demand_code": "T012"}).json()["code"]
    _agree(client, tx, 21, 500)
    client.post(f"/trade/{tx}/escrow"); client.post(f"/trade/{tx}/ship")
    # Kritik alan (kumas/pamuk) bildirilmedi → eksik doğrulama → askıya alınır
    r = client.post(f"/trade/{tx}/deliver", json={"kalite": "A", "miktar_kg": 800}).json()
    assert r["mismatch"] is True


def test_accept_requires_two_parties_and_matching_amount(client):
    m = client.get("/matching/demand/T007", params={"top": 1}).json()[0]
    tx = client.post("/trade/open", json={"batch_code": m["batch_code"], "demand_code": "T007"}).json()["code"]
    client.post(f"/trade/{tx}/bid", json={"by_role": "buyer", "kind": "bid", "amount": 20, "qty_kg": 500})
    # Kendi teklifini kabul → 409
    assert client.post(f"/trade/{tx}/bid", json={"by_role": "buyer", "kind": "accept", "amount": 20, "qty_kg": 500}).status_code == 409
    # Farklı fiyatla kabul → 409
    assert client.post(f"/trade/{tx}/bid", json={"by_role": "seller", "kind": "accept", "amount": 25, "qty_kg": 500}).status_code == 409
    # Doğru: karşı taraf, son teklifle → ACCEPTED
    ok = client.post(f"/trade/{tx}/bid", json={"by_role": "seller", "kind": "accept", "amount": 20, "qty_kg": 500}).json()
    assert ok["transaction"]["status"] == "ACCEPTED" and ok["transaction"]["agreed_price"] == 20


def test_accept_with_no_prior_bid_rejected(client):
    # REGRESYON: OPEN işlemde hiç teklif yokken tek taraflı 'accept' KABUL EDİLMEMELİ
    # (iki-taraflı rıza atlanamaz; aksi halde tek taraf keyfi fiyatı dayatır).
    m = client.get("/matching/demand/T009", params={"top": 1}).json()[0]
    tx = client.post("/trade/open",
                     json={"batch_code": m["batch_code"], "demand_code": "T009"}).json()["code"]
    r = client.post(f"/trade/{tx}/bid",
                    json={"by_role": "buyer", "kind": "accept", "amount": 999, "qty_kg": 1})
    assert r.status_code == 409
    # İşlem hâlâ OPEN, sahte fiyat yazılmadı
    t = client.get(f"/trade/{tx}").json()["transaction"]
    assert t["status"] == "OPEN" and t["agreed_price"] is None


def test_delivery_empty_string_not_bypass(client):
    m = client.get("/matching/demand/T008", params={"top": 1}).json()[0]
    b = m["batch_code"]
    tx = client.post("/trade/open", json={"batch_code": b, "demand_code": "T008"}).json()["code"]
    _agree(client, tx, 21, 500)
    client.post(f"/trade/{tx}/escrow"); client.post(f"/trade/{tx}/ship")
    p = client.get(f"/passports/{b}").json()
    # Boş string kumas artık "eksik" sayılır → sızıntı kapandı (VERIFIED olmamalı)
    r = client.post(f"/trade/{tx}/deliver", json={
        "pamuk": p["pamuk"], "polyester": p["polyester"], "elastan": p["elastan"],
        "kumas": "", "gramaj": p["gramaj"], "kalite": p["kalite"], "miktar_kg": p["miktar_kg"]}).json()
    assert r["mismatch"] is True and r["transaction"]["status"] == "SUSPENDED"


def test_reputation_syncs_across_sibling_batches(client):
    # İtibar güncellemesi fabrikanın TÜM partilerine yansımalı (bayat skor yok)
    from app import trust_service as TS
    from app.db import SessionLocal
    from app.models import Batch, Factory
    db = SessionLocal()
    try:
        f = db.query(Factory).filter(Factory.role == "seller").first()
        some = db.query(Batch).filter(Batch.factory_id == f.id).first()
        TS.update_reputation(db, some, success=False, commit=True)
        reps = {round(s.reputation, 4) for s in
                db.query(Batch).filter(Batch.factory_id == f.id).all()}
        assert len(reps) == 1                         # tüm kardeş partiler tek değerde
        assert abs(next(iter(reps)) - round(f.reputation, 4)) < 1e-6
    finally:
        db.close()


def test_provenance_timeline(client):
    bcode, tx = _open_verified_trade(client, "T005")
    pv = client.get(f"/trust/{bcode}/provenance").json()
    assert pv["verification"]["valid"] is True
    events = [e["event"] for e in pv["timeline"]]
    assert events[0] == "DMP_CREATED" and "MATCHED" in events
