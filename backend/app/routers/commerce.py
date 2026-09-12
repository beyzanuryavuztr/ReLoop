"""
Ticari fiyat (#16-18) + AB-DPP uyumu (#19-20) uçları.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import dpp as DPP
from .. import pricing as P
from ..db import get_db
from ..models import Batch, PassportEvent

pricing_router = APIRouter(prefix="/pricing", tags=["Fiyat Mekanizması"])
dpp_router = APIRouter(tags=["AB-DPP Uyumu"])


class SuggestIn(BaseModel):
    pamuk: float = Field(ge=0, le=100)
    polyester: float = 0
    elastan: float = 0
    kalite: str = Field(default="B", pattern="^[ABC]$")
    dogrulanmis: bool = False
    miktar_kg: float = Field(gt=0)
    gramaj: int = Field(gt=0)


def _last_hash(db: Session, batch_id: int) -> str | None:
    ev = (db.query(PassportEvent).filter(PassportEvent.batch_id == batch_id)
            .order_by(PassportEvent.seq.desc()).first())
    return ev.hash if ev else None


def _clean_model(m: dict) -> dict:
    return {k: v for k, v in m.items() if not k.startswith("_")}


@pricing_router.get("/index", summary="Fire endeksi (lif×kalite×bölge, TL/kg)")
def index(db: Session = Depends(get_db)):
    return P.price_index(db)


@pricing_router.get("/trend", summary="Endeks trendi (illüstratif haftalık)")
def trend(weeks: int = 8, db: Session = Depends(get_db)):
    return P.index_trend(db, weeks=weeks)


@pricing_router.get("/model", summary="Hedonik fiyat modeli (OLS katsayıları + R²)")
def model(db: Session = Depends(get_db)):
    return _clean_model(P.fit_hedonic(db))


@pricing_router.post("/suggest", summary="Önerilen fiyat + %90 güven aralığı")
def suggest(payload: SuggestIn, db: Session = Depends(get_db)):
    return P.suggest_price(db, payload.pamuk, payload.kalite, payload.dogrulanmis,
                           payload.miktar_kg, payload.gramaj, payload.elastan,
                           payload.polyester)


@pricing_router.get("/recommend/{batch_code}", summary="Bir parti için teklif önerisi bandı")
def recommend(batch_code: str, db: Session = Depends(get_db)):
    b = db.query(Batch).filter(Batch.code == batch_code).first()
    if not b:
        raise HTTPException(404, f"DMP {batch_code} bulunamadı")
    s = P.suggest_price(db, b.pamuk, b.kalite, b.dogrulanmis, b.miktar_kg, b.gramaj,
                        b.elastan, b.polyester)
    # Satıcının gizli rezervi (min_fiyat, kör teklifte kullanılır) DIŞARI VERİLMEZ
    # (denetim bulgusu 2.1). Yalnız platformun ürettiği piyasa referans bandı döner.
    return {"batch_code": batch_code, "market_ref_tl_per_kg": P.ref_price(b), **s}


@dpp_router.get("/passports/{code}/dpp.jsonld", summary="AB-DPP JSON-LD export (hash-zincirli)")
def dpp_jsonld(code: str, db: Session = Depends(get_db)):
    b = db.query(Batch).filter(Batch.code == code).first()
    if not b:
        raise HTTPException(404, f"DMP {code} bulunamadı")
    doc = DPP.build_jsonld(b, _last_hash(db, b.id))
    return JSONResponse(doc, media_type="application/ld+json")


@dpp_router.get("/passports/{code}/espr", summary="ESPR veri kategorileri eşlemesi")
def espr(code: str, db: Session = Depends(get_db)):
    b = db.query(Batch).filter(Batch.code == code).first()
    if not b:
        raise HTTPException(404, f"DMP {code} bulunamadı")
    return DPP.espr_view(b, _last_hash(db, b.id))


@dpp_router.get("/dpp/espr-mapping", summary="ESPR ↔ pasaport alan eşleme şeması")
def espr_mapping():
    return {"mapping": DPP.ESPR_MAPPING_SCHEMA}
