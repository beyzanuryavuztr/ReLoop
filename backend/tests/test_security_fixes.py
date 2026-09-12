"""
Güvenlik/doğruluk regresyon testleri (denetim TOP-10 düzeltmeleri):
  • Para hareketi olan uçlarda çıkar çatışması koruması:
      - satıcı KENDİ emanetini serbest bırakamaz (complete)
      - uyuşmazlığı yalnız TARAFSIZ aktör (denetçi/bakanlık) çözer (resolve)
  • Sert filtreyi geçmeyen parti-talep çiftinde işlem AÇILAMAZ (sahte etki/sertifika önlenir)
  • Gizli rezerv fiyatı (min_fiyat) açık veri / öneri uçlarından SIZMAZ
Bu testler eski kodda BAŞARISIZ olurdu; düzeltmeleri kilitler.
"""
SELLER = {"X-API-Key": "demo-seller-key"}
RECYCLER = {"X-API-Key": "demo-recycler-key"}
MINISTRY = {"X-API-Key": "demo-ministry-key"}


def _verified_trade(client, demand):
    m = client.get(f"/matching/demand/{demand}", params={"top": 1}).json()[0]
    b = m["batch_code"]
    tx = client.post("/trade/open", json={"batch_code": b, "demand_code": demand},
                     headers=SELLER).json()["code"]
    client.post(f"/trade/{tx}/bid", json={"by_role": "seller", "kind": "bid",
                "amount": 21, "qty_kg": 500}, headers=SELLER)
    client.post(f"/trade/{tx}/bid", json={"by_role": "buyer", "kind": "accept",
                "amount": 21, "qty_kg": 500}, headers=RECYCLER)
    client.post(f"/trade/{tx}/escrow", headers=RECYCLER)
    client.post(f"/trade/{tx}/ship", headers=SELLER)
    p = client.get(f"/passports/{b}").json()
    client.post(f"/trade/{tx}/deliver", json={k: p[k] for k in
                ("pamuk", "polyester", "elastan", "kumas", "gramaj", "kalite", "miktar_kg")},
                headers=RECYCLER)
    return b, tx


def test_seller_cannot_complete_own_escrow(client):
    _, tx = _verified_trade(client, "T031")
    # Satıcı (beneficiary) kendi emanetini serbest bırakamaz → 403
    assert client.post(f"/trade/{tx}/complete", headers=SELLER).status_code == 403
    # Alıcı serbest bırakır → 200
    assert client.post(f"/trade/{tx}/complete", headers=RECYCLER).status_code == 200


def test_dispute_resolution_is_neutral_only(client):
    m = client.get("/matching/demand/T030", params={"top": 1}).json()[0]
    b = m["batch_code"]
    tx = client.post("/trade/open", json={"batch_code": b, "demand_code": "T030"},
                     headers=SELLER).json()["code"]
    client.post(f"/trade/{tx}/bid", json={"by_role": "seller", "kind": "bid",
                "amount": 21, "qty_kg": 500}, headers=SELLER)
    client.post(f"/trade/{tx}/bid", json={"by_role": "buyer", "kind": "accept",
                "amount": 21, "qty_kg": 500}, headers=RECYCLER)
    client.post(f"/trade/{tx}/escrow", headers=RECYCLER)
    client.post(f"/trade/{tx}/ship", headers=SELLER)
    bad = client.post(f"/trade/{tx}/deliver",
                      json={"kalite": "C", "elastan": 9, "miktar_kg": 50},
                      headers=RECYCLER).json()
    assert bad["transaction"]["status"] == "SUSPENDED"
    client.post(f"/trade/{tx}/dispute", json={"reason": "uyuşmuyor"}, headers=RECYCLER)
    # Ne satıcı ne alıcı kendi lehine karar veremez → 403
    assert client.post(f"/trade/{tx}/resolve", json={"outcome": "release"},
                       headers=SELLER).status_code == 403
    assert client.post(f"/trade/{tx}/resolve", json={"outcome": "refund"},
                       headers=RECYCLER).status_code == 403
    # Tarafsız aktör (bakanlık) çözer → 200
    assert client.post(f"/trade/{tx}/resolve", json={"outcome": "refund"},
                       headers=MINISTRY).status_code == 200


def test_open_trade_rejects_nonmatching_pair(client):
    rej = client.get("/matching/demand/T032/rejections").json()
    assert rej, "en az bir sert-filtre reddi beklenir"
    bad_batch = rej[0]["batch_code"]
    r = client.post("/trade/open",
                    json={"batch_code": bad_batch, "demand_code": "T032"})
    assert r.status_code == 422   # eşleşmeyen çiftte işlem açılamaz


def test_opendata_does_not_leak_reserve_price(client):
    d = client.get("/public/opendata/aggregate").json()
    assert d["regions"]
    for r in d["regions"]:
        assert "min_fiyat" not in r and "avg_price_tl" not in r
        assert "avg_ref_price_tl" in r   # yalnız hesaplanan piyasa referansı
