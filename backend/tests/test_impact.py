"""
Dalga 5 — kamu & politika etki motoru testleri: karşılaştırma, atık önleme,
NDC projeksiyon (doğrusal), simülatör, fabrika panosu, karbon sertifikası PDF,
UÇBS/TABS uyum, formalizasyon, denetim modu.
"""


def test_comparison_and_waste_prevention(client):
    cmp = client.get("/impact/comparison").json()
    assert len(cmp["rows"]) == 3
    wp = client.get("/impact/waste-prevention").json()
    assert wp["landfill_diversion_rate_pct"] == 100.0
    tot = wp["recycled_textile_t"] + wp["downcycled_t"] + wp["energy_recovery_t"]
    assert abs(tot - wp["total_fire_t"]) < 0.5


def test_ndc_linear_and_simulator(client):
    a20 = client.get("/impact/ndc", params={"adoption_pct": 20}).json()
    a40 = client.get("/impact/ndc", params={"adoption_pct": 40}).json()
    # doğrusal ölçekleme: %40, %20'nin ~2 katı
    assert abs(a40["recovered_t"] - 2 * a20["recovered_t"]) < 1.0
    assert a20["co2e_saving_t"]["ecoinvent"] > a20["co2e_saving_t"]["conservative"]

    sim = client.post("/impact/simulate", json={
        "participation_pct": 30, "carbon_price_tl_per_ton": 1000, "new_facilities": 5}).json()
    assert sim["effective_reach_pct"] == 40.0          # 30 + 5*2
    assert sim["carbon_credit_value_tl"] == sim["co2e_saving_t"]["conservative"] * 1000
    assert "NDC" in sim["climate_framing"] and "net-sıfır" in sim["climate_framing"]


def test_factory_panel(client):
    fp = client.get("/impact/factory/1").json()
    assert fp["batches"] >= 1 and fp["total_kg"] > 0
    assert fp["co2_saving_t"] >= 0


def _complete_a_trade(client, demand="T006"):
    m = client.get(f"/matching/demand/{demand}", params={"top": 1}).json()[0]
    b = m["batch_code"]
    tx = client.post("/trade/open", json={"batch_code": b, "demand_code": demand}).json()["code"]
    # İki taraflı mutabakat: satıcı teklif verir, alıcı kabul eder
    client.post(f"/trade/{tx}/bid", json={"by_role": "seller", "kind": "bid", "amount": 21, "qty_kg": 800})
    client.post(f"/trade/{tx}/bid", json={"by_role": "buyer", "kind": "accept", "amount": 21, "qty_kg": 800})
    client.post(f"/trade/{tx}/escrow")
    client.post(f"/trade/{tx}/ship")
    p = client.get(f"/passports/{b}").json()
    client.post(f"/trade/{tx}/deliver", json={
        "pamuk": p["pamuk"], "polyester": p["polyester"], "elastan": p["elastan"],
        "kumas": p["kumas"], "gramaj": p["gramaj"], "kalite": p["kalite"],
        "miktar_kg": p["miktar_kg"]})
    client.post(f"/trade/{tx}/complete")
    return tx, b


def test_carbon_certificate_pdf(client):
    tx, _ = _complete_a_trade(client, "T006")
    r = client.get(f"/impact/certificate/{tx}.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-"


def test_tabs_compliance_and_formalization(client):
    b = client.get("/passports", params={"limit": 1}).json()[0]["code"]
    t = client.get(f"/compliance/tabs/{b}").json()
    assert t["waste_code"] == "04 02 22"
    assert t["waste_code_format_ok"] is True
    fm = client.get("/compliance/formalization").json()
    assert "formalized_value_tl" in fm and fm["registered_passports"] > 0


def test_unit_economics_and_revenue(client):
    u = client.get("/impact/unit-economics", params={"qty_kg": 2350, "price_tl_per_kg": 18}).json()
    assert u["gross_transaction_tl"] == 2350 * 18
    assert u["contribution_margin_tl"] == u["commission_revenue_tl"] - u["verification_cost_tl"]
    assert len(u["revenue_model"]) == 3
    rm = client.get("/impact/revenue-model").json()
    assert len(rm["layers"]) == 3


def test_audit_mode(client):
    facs = client.get("/public/factories").json()
    name = facs[0]["name"]
    a = client.get(f"/audit/{name}").json()
    assert a["batch_count"] >= 1
    assert all("chain_valid" in b for b in a["batches"])
