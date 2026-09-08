"""
Eşleştirme uçları — açıklanabilir iki aşamalı motor (sert filtre + kademeli skor).
Kaskad/lot-birleştirme/Pareto/proaktif uçlar `intelligence.py`'de yer alır.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import engine_service as ES
from ..db import get_db
from ..models import Batch, Demand
from ..schemas import DemandOut, MatchOut

router = APIRouter(prefix="/matching", tags=["Eşleştirme"])
demand_router = APIRouter(prefix="/demands", tags=["Talep"])


@demand_router.get("", response_model=list[DemandOut], summary="Talep listesi")
def list_demands(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    rows = db.query(Demand).order_by(Demand.id).offset(offset).limit(min(limit, 500)).all()
    return [DemandOut.model_validate(d, from_attributes=True) for d in rows]


@demand_router.get("/{code}", response_model=DemandOut, summary="Tek talep")
def get_demand(code: str, db: Session = Depends(get_db)):
    d = db.query(Demand).filter(Demand.code == code).first()
    if not d:
        raise HTTPException(404, f"Talep {code} bulunamadı")
    return DemandOut.model_validate(d, from_attributes=True)


@router.get("/demand/{code}", response_model=list[MatchOut],
            summary="Bir talep için sıralı, açıklanabilir eşleşmeler")
def match_for_demand(code: str, top: int = 10, db: Session = Depends(get_db)):
    d = db.query(Demand).filter(Demand.code == code).first()
    if not d:
        raise HTTPException(404, f"Talep {code} bulunamadı")
    batches = db.query(Batch).filter(Batch.status != "sold").all()   # yalnız mevcut envanter
    return ES.best_matches_for_demand(d, batches, top=top)


@router.get("/batch/{code}", summary="Bir parti için en iyi talep + skor kırılımı")
def match_for_batch(code: str, db: Session = Depends(get_db)):
    b = db.query(Batch).filter(Batch.code == code).first()
    if not b:
        raise HTTPException(404, f"DMP {code} bulunamadı")
    demands = db.query(Demand).all()
    best = ES.best_match_for_batch(b, demands)
    return {"batch_code": code, "best": best}
