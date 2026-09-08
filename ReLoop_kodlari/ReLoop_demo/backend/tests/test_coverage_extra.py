"""
Ek kapsam — denetimde test edilmediği tespit edilen uçlar + admin fail-closed:
  • GET /demands, GET /demands/{code}          (talep listesi / tekil + 404)
  • GET /matching/batch/{code}                 (parti → en iyi talep + 404)
  • GET /passports/{code}/inconsistencies      (DMP tutarsızlık raporu + 404)
  • GET /trade                                 (işlem listesi + durum filtresi)
  • GET /impact/assumptions                    (şeffaflık: varsayım/yöntem/kaynak)
  • POST /notifications/{nid}/read             (okundu işaretle + 404)
  • require_admin fail-closed                  (anahtar boşsa /admin/* açılmaz → 503)
"""
from app.config import settings


def _hub_factory_id(client, city="Uşak"):
    """Alıcıya yakın merkez şehir fabrikası (ulusal veride forecast eşleşmesi için)."""
    facs = client.get("/public/factories", params={"role": "seller"}).json()
    return next(f["id"] for f in facs if f["city"] == city)


def test_list_and_get_demand(client):
    ds = client.get("/demands", params={"limit": 5}).json()
    assert isinstance(ds, list) and len(ds) == 5
    code = ds[0]["code"]
    one = client.get(f"/demands/{code}").json()
    assert one["code"] == code
    assert client.get("/demands/YOKBOYLE").status_code == 404


def test_match_for_batch(client):
    b = client.get("/passports", params={"limit": 1}).json()[0]
    r = client.get(f"/matching/batch/{b['code']}").json()
    assert r["batch_code"] == b["code"]
    assert "best" in r                                  # en iyi talep + skor kırılımı (None olabilir)
    assert client.get("/matching/batch/YOKBOYLE").status_code == 404


def test_passport_inconsistencies(client):
    b = client.get("/passports", params={"limit": 1}).json()[0]
    r = client.get(f"/passports/{b['code']}/inconsistencies").json()
    assert r["batch_code"] == b["code"]
    assert isinstance(r["inconsistencies"], list)
    assert r["consistent"] is (len(r["inconsistencies"]) == 0)   # tutarlı == uyarı yok
    assert client.get("/passports/YOKBOYLE/inconsistencies").status_code == 404


def test_list_trades_and_status_filter(client):
    all_tx = client.get("/trade").json()
    assert isinstance(all_tx, list)
    # geçersiz durum → boş küme (filtre dalı çalışır, sızıntı yok)
    assert client.get("/trade", params={"status": "YOKBOYLE"}).json() == []


def test_impact_assumptions(client):
    a = client.get("/impact/assumptions").json()
    for k in ("coefficients", "sources", "national_anchor_t", "system_boundary", "note"):
        assert k in a
    assert a["national_anchor_t"] > 0


def test_notification_mark_read(client):
    # Bildirim üret (proaktif tahmin) → listele → okundu işaretle → doğrula
    client.post("/matching/forecast", json={
        "factory_id": _hub_factory_id(client), "monthly_kg": 40000, "fire_rate_pct": 5,
        "kumas": "suprem", "pamuk": 100, "polyester": 0, "elastan": 0,
        "gramaj": 180, "kalite": "A"})
    notes = client.get("/notifications").json()
    assert notes and notes[0]["read"] is False
    nid = notes[0]["id"]
    r = client.post(f"/notifications/{nid}/read").json()
    assert r == {"id": nid, "read": True}
    # artık okunmamışlarda görünmemeli
    unread_ids = [n["id"] for n in client.get("/notifications", params={"unread": True}).json()]
    assert nid not in unread_ids
    assert client.post("/notifications/999999/read").status_code == 404


def test_compliance_eligibility_dual_mevzuat(client):
    # Çift mevzuat uygunluğu: parti × 8 alıcı firma (UYGUN/UYARI/ENGELLİ)
    ps = client.get("/passports", params={"limit": 3}).json()
    code = ps[0]["code"]
    d = client.get(f"/compliance/eligibility/{code}").json()
    s = d["summary"]
    assert set(s) == {"UYGUN", "UYARI", "ENGELLİ"}
    assert s["UYGUN"] + s["UYARI"] + s["ENGELLİ"] == 8       # 8 firma
    assert len(d["firms"]) == 8
    # Yasal katman parti düzeyinde: beyan tutarsızsa (legal_ok False) TÜM firmalar ENGELLİ
    if not d["legal_ok"]:
        assert s["UYGUN"] == 0 and s["UYARI"] == 0 and s["ENGELLİ"] == 8
    # her firma kaydı dürüstlük kaynağı taşır (gerçek/temsili)
    assert all("kaynak" in f for f in d["firms"])
    assert client.get("/compliance/eligibility/YOKKOD").status_code == 404


def test_admin_fail_closed_when_key_unset(client, monkeypatch):
    # Anahtar YAPILANDIRILMAMIŞSA yıkıcı /admin/* sessizce açılmamalı → 503.
    monkeypatch.setattr(settings, "admin_key", "")
    r = client.post("/admin/seed", params={"dataset": "canonical"})
    assert r.status_code == 503
