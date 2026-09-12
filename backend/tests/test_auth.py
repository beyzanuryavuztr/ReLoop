"""
Gerçek API-anahtarı auth testleri: geçersiz anahtar reddi, rol doğrulanmış kimlikten
türetilir (self-declared değil), rol zorlaması. require_auth kapalıyken bile geçersiz
anahtar reddedilir ve geçerli anahtar rolü belirler. Ayrıca: yıkıcı /admin/* koruması
ve require_auth AÇIKKEN anahtarsız durum-değiştiren uçların reddi.
"""
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

BODY = {"factory_id": 1, "city": "Uşak", "lat": 38.68, "lon": 29.41,
        "pamuk": 100, "polyester": 0, "elastan": 0, "kumas": "suprem",
        "gramaj": 180, "en_m": 1.8, "miktar_kg": 800, "kalite": "A", "min_fiyat": 18}


def test_admin_endpoint_requires_key():
    # Yıkıcı /admin/seed X-Admin-Key OLMADAN → 401; DOĞRU anahtarla → 200.
    bare = TestClient(app)                                  # varsayılan admin başlığı YOK
    assert bare.post("/admin/seed", params={"dataset": "canonical"}).status_code == 401
    assert bare.post("/admin/seed", params={"dataset": "canonical"},
                     headers={"X-Admin-Key": "reloop-admin-demo"}).status_code == 200
    # Yanlış anahtar da reddedilir
    assert bare.post("/admin/seed", params={"dataset": "canonical"},
                     headers={"X-Admin-Key": "yanlis"}).status_code == 401


def test_require_auth_blocks_anon(client, monkeypatch):
    # require_auth AÇIKKEN anahtarsız durum-değiştiren uç → 401 (prod varsayılan davranışı).
    monkeypatch.setattr(settings, "require_auth", True)
    assert client.post("/passports", json=BODY).status_code == 401           # anahtar yok
    # Geçerli satıcı anahtarıyla → 201 (arayüzün yaptığı gibi)
    assert client.post("/passports", json=BODY,
                       headers={"X-API-Key": "demo-seller-key"}).status_code == 201


def test_invalid_key_rejected(client):
    assert client.post("/passports", json=BODY, headers={"X-API-Key": "gecersiz"}).status_code == 401


def test_valid_key_authenticates(client):
    assert client.post("/passports", json=BODY, headers={"X-API-Key": "demo-seller-key"}).status_code == 201


def test_role_enforced_from_identity(client):
    m = client.get("/matching/demand/T020", params={"top": 1}).json()[0]
    tx = client.post("/trade/open",
                     json={"batch_code": m["batch_code"], "demand_code": "T020"},
                     headers={"X-API-Key": "demo-seller-key"}).json()["code"]
    # satıcı teklif verir (satıcı kimliğiyle), recycler (=buyer) kabul eder — rol kimlikten türetilir
    client.post(f"/trade/{tx}/bid",
                json={"by_role": "seller", "kind": "bid", "amount": 21, "qty_kg": 500},
                headers={"X-API-Key": "demo-seller-key"})
    client.post(f"/trade/{tx}/bid",
                json={"by_role": "buyer", "kind": "accept", "amount": 21, "qty_kg": 500},
                headers={"X-API-Key": "demo-recycler-key"})
    client.post(f"/trade/{tx}/escrow", headers={"X-API-Key": "demo-seller-key"})
    # recycler SEVKİYAT yapamaz (satıcının işi) → 403
    assert client.post(f"/trade/{tx}/ship", headers={"X-API-Key": "demo-recycler-key"}).status_code == 403
    # seller yapar → 200
    assert client.post(f"/trade/{tx}/ship", headers={"X-API-Key": "demo-seller-key"}).status_code == 200


def test_declared_role_must_match_identity(client):
    m = client.get("/matching/demand/T021", params={"top": 1}).json()[0]
    tx = client.post("/trade/open",
                     json={"batch_code": m["batch_code"], "demand_code": "T021"},
                     headers={"X-API-Key": "demo-seller-key"}).json()["code"]
    # seller kimliğiyle 'buyer' rolünde teklif → 403 (kimlik≠iddia)
    r = client.post(f"/trade/{tx}/bid",
                    json={"by_role": "buyer", "kind": "bid", "amount": 20, "qty_kg": 500},
                    headers={"X-API-Key": "demo-seller-key"})
    assert r.status_code == 403
