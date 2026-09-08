"""
ReLoop API — döngüsel tekstil için güvenilir ticari ray.

Çalıştırma (yerel, SQLite):
    uvicorn app.main:app --reload
Swagger:  http://127.0.0.1:8000/docs
Prod (Postgres):  RELOOP_DATABASE_URL=postgresql+psycopg://... uvicorn app.main:app
"""
from __future__ import annotations
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import settings
from .db import Base, SessionLocal, engine
from .models import Batch
from .routers import (commerce, impact, intelligence, matching, passports,
                      public, trade, trust)
from .seed_loader import load as seed_load

DESCRIPTION = """
**ReLoop** — pre-consumer tekstil firesini ekonomiye kazandıran, kamu-entegre
B2B döngüsellik platformunun gerçek işlem omurgası.

Bu API tüm işlem/güven zincirini kalıcı bir veritabanına yazar:
Dijital Malzeme Pasaportu (DMP) → açıklanabilir eşleştirme → kör teklif/emanet →
teslim doğrulama → **SHA-256 menşe hash zinciri**.

Motor `reloop.py` çekirdeğini birebir kullanır (tek doğruluk kaynağı); sentetik ve
yarı-gerçek (gerçek coğrafya/katsayı) iki veri seti ile doğrulanır.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Şema doğruluk kaynağı: prod'da (Postgres) Alembic migration'larıdır.
    # create_all yalnız SQLite (dev/sandbox) kolaylığı için; Postgres'te ATLANIR
    # → şema tek kaynaktan (alembic upgrade head) yönetilir.
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
    # DB boşsa referans (kanonik) ekosistemi otomatik yükle.
    db = SessionLocal()
    try:
        if db.query(Batch).count() == 0:
            seed_load(db, dataset="canonical")
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description=DESCRIPTION,
    lifespan=lifespan,
    contact={"name": "ReLoop", "url": "https://reloop.example"},
    license_info={"name": "Pilot / ticari değerlendirme"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # file:// arayüz (Origin: null) + wildcard için credentials KAPALI olmalı
    # (CORS spec wildcard+credentials'ı yasaklar). Çerez kullanmıyoruz.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(passports.router)
app.include_router(matching.router)
app.include_router(matching.demand_router)
app.include_router(trade.router)
app.include_router(trust.router)
app.include_router(intelligence.router)
app.include_router(intelligence.notif_router)
app.include_router(commerce.pricing_router)
app.include_router(commerce.dpp_router)
app.include_router(impact.router)
app.include_router(impact.comp_router)
app.include_router(public.router)


# Görüntü Zekâsı için yerel TF.js + MobileNet (CDN yok; CNN tarayıcıda çalışır).
_VENDOR = Path(__file__).resolve().parent.parent / "vendor"
if _VENDOR.exists():
    app.mount("/vendor", StaticFiles(directory=str(_VENDOR)), name="vendor")


# Arayüzü backend'in KENDİSİNDEN servis et → tek adres (http://127.0.0.1:8000/app),
# file:// sürtünmesi yok, aynı origin olduğu için 12 sekme de otomatik CANLI gelir
# (arayüz API_BASE'i location.origin yapar; ?api= gerekmez, CORS gerekmez).
_APP_HTML = Path(__file__).resolve().parent.parent.parent / "reloop_app.html"


@app.get("/app", tags=["Sistem"], summary="ReLoop arayüzü (tek sayfa)", include_in_schema=False)
def app_ui():
    if _APP_HTML.exists():
        return FileResponse(str(_APP_HTML), media_type="text/html; charset=utf-8")
    return RedirectResponse("/docs")


@app.get("/", tags=["Sistem"], summary="Sağlık + kimlik")
def root():
    return {
        "name": settings.app_name,
        "version": __version__,
        "engine": "reloop.py (tek doğruluk kaynağı)",
        "app": "/app",
        "docs": "/docs",
        "tagline": "Döngüsel tekstil için güvenilir ticari ray",
    }


@app.get("/health", tags=["Sistem"], summary="Sağlık kontrolü")
def health():
    return {"status": "ok", "db": settings.database_url.split(":")[0]}
