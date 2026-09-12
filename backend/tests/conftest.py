"""Pytest ortak fikstürleri — izole geçici SQLite DB üzerinde TestClient."""
import os
import tempfile

# app import edilmeden ÖNCE izole DB'yi ayarla.
_TMP = tempfile.mkdtemp(prefix="reloop_test_")
os.environ["RELOOP_DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
# Testler iş mantığını "anon" (açık) koşar; auth TRANSPORT'u test_auth.py açıkça anahtar
# göndererek + require_auth'ı monkeypatch ederek doğrular. (Prod varsayılanı: require_auth=True.)
os.environ["RELOOP_REQUIRE_AUTH"] = "false"
os.environ["RELOOP_ADMIN_KEY"] = "reloop-admin-demo"   # yıkıcı /admin/* korumalı kalır

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

ADMIN_HEADERS = {"X-Admin-Key": "reloop-admin-demo"}


@pytest.fixture(scope="session")
def client():
    # Context manager lifespan'i tetikler → tablolar + kanonik seed.
    # Varsayılan X-Admin-Key → /admin/seed çağrıları (fixture + testler) yetkili.
    with TestClient(app, headers=ADMIN_HEADERS) as c:
        yield c


@pytest.fixture(autouse=True)
def fresh_canonical(client):
    """Her testten ÖNCE pristine kanonik ekosistem — testler birbirinden İZOLE,
    sıra-bağımsız (paylaşılan session DB'nin kırılganlığını giderir)."""
    client.post("/admin/seed", params={"dataset": "canonical"})
    yield
