"""
Dalga 4 — ticari fiyat (#16-18) + AB-DPP (#19-20) testleri.
Hedonik model 'semireal' (gerçekçi ekonomili) veri setinde doğrulanır; DPP kanonikte.
"""


def test_price_index_structure(client):
    idx = client.get("/pricing/index").json()
    assert idx["unit"] == "TL/kg"
    assert idx["overall"]["min"] <= idx["overall"]["mean"] <= idx["overall"]["max"]
    assert len(idx["by_group"]) > 0
    tr = client.get("/pricing/trend").json()
    assert len(tr["series"]) >= 2


def test_hedonic_model_on_semireal(client):
    client.post("/admin/seed", params={"dataset": "semireal"})
    try:
        m = client.get("/pricing/model").json()
        assert m["ok"] is True
        assert m["r2"] > 0.5                                   # gerçekçi fiyatta güçlü uyum
        c = m["coefficients"]
        assert c["pamuk"] > 0                                  # pamuk saflığı primi
        assert c["kalite_ord"] > 0                             # kalite primi
        assert c["elastan"] < 0                                # kontaminant iskontosu
        s_hi = client.post("/pricing/suggest", json={
            "pamuk": 100, "polyester": 0, "elastan": 0, "kalite": "A",
            "dogrulanmis": True, "miktar_kg": 800, "gramaj": 180}).json()
        s_lo = client.post("/pricing/suggest", json={
            "pamuk": 65, "polyester": 35, "elastan": 0, "kalite": "C",
            "dogrulanmis": False, "miktar_kg": 200, "gramaj": 250}).json()
        assert s_hi["predicted_tl_per_kg"] > s_lo["predicted_tl_per_kg"]
        assert len(s_hi["ci90"]) == 2 and s_hi["ci90"][0] < s_hi["ci90"][1]
    finally:
        client.post("/admin/seed", params={"dataset": "canonical"})   # paritesini geri yükle


def test_recommend_bid(client):
    b = client.get("/passports", params={"limit": 1}).json()[0]["code"]
    r = client.get(f"/pricing/recommend/{b}").json()
    assert "recommended_band" in r and "market_ref_tl_per_kg" in r
    # Satıcının gizli rezervi (min_fiyat) SIZMAMALI (denetim bulgusu 2.1)
    assert "declared_min_fiyat" not in r and "min_fiyat" not in r


def test_dpp_jsonld_signed(client):
    b = client.get("/passports", params={"limit": 1}).json()[0]["code"]
    r = client.get(f"/passports/{b}/dpp.jsonld")
    assert r.status_code == 200
    assert "application/ld+json" in r.headers["content-type"]
    d = r.json()
    assert "@context" in d and d["identifier"] == b
    assert d["proof"]["algorithm"] == "SHA-256"
    assert d["proof"]["chainHead"]                            # hash zincirine bağlı (imzalı)
    assert len(d["materialComposition"]) == 3


def test_espr_mapping(client):
    b = client.get("/passports", params={"limit": 1}).json()[0]["code"]
    e = client.get(f"/passports/{b}/espr").json()
    assert "material_composition" in e["espr_data"]
    assert "origin_traceability" in e["espr_data"]
    mp = client.get("/dpp/espr-mapping").json()
    assert len(mp["mapping"]) >= 5
