"""
Dijital Malzeme Pasaportu (DMP) uçları — CRUD + tutarsızlık + hash zinciri.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import engine_service as ES
from ..auth import require_actor
from ..chain import append_event, verify_chain
from ..db import atomic, get_db
from ..models import AuditLog, Batch, Factory
from ..schemas import BatchIn, BatchOut, InconsistencyOut

router = APIRouter(prefix="/passports", tags=["DMP (Dijital Malzeme Pasaportu)"])


def _out(b: Batch) -> BatchOut:
    data = BatchOut.model_validate(b, from_attributes=True)
    return data


@router.get("", response_model=list[BatchOut], summary="DMP listesi")
def list_passports(limit: int = 50, offset: int = 0, city: str | None = None,
                   db: Session = Depends(get_db)):
    q = db.query(Batch)
    if city:
        q = q.filter(Batch.city == city)
    rows = q.order_by(Batch.id).offset(offset).limit(min(limit, 500)).all()
    return [_out(b) for b in rows]


@router.get("/{code}", response_model=BatchOut, summary="Tek DMP")
def get_passport(code: str, db: Session = Depends(get_db)):
    b = db.query(Batch).filter(Batch.code == code).first()
    if not b:
        raise HTTPException(404, f"DMP {code} bulunamadı")
    return _out(b)


@router.post("/check", response_model=list[str],
             summary="Aday DMP tutarsızlık kontrolü (kaydetmeden)")
def check_inconsistencies(payload: BatchIn, db: Session = Depends(get_db)):
    """Formda anlık tutarsızlık denetimi için — parti kaydedilmez."""
    tmp = Batch(code="P-CHECK", factory_id=payload.factory_id, city=payload.city,
                lat=payload.lat, lon=payload.lon, pamuk=payload.pamuk,
                polyester=payload.polyester, elastan=payload.elastan, kumas=payload.kumas,
                gramaj=payload.gramaj, en_m=payload.en_m, miktar_kg=payload.miktar_kg,
                kalite=payload.kalite, min_fiyat=payload.min_fiyat)
    return ES.inconsistencies_for(tmp)


@router.post("", response_model=BatchOut, status_code=201, summary="Yeni DMP oluştur")
def create_passport(payload: BatchIn, db: Session = Depends(get_db),
                    _: str = Depends(require_actor)):
    f = db.get(Factory, payload.factory_id)
    if not f:
        raise HTTPException(400, f"Fabrika {payload.factory_id} yok")

    # Sıradaki parti kodu (P####)
    last = db.query(Batch).order_by(Batch.id.desc()).first()
    n = (int(last.code[1:]) + 1) if last and last.code[1:].isdigit() else 1
    code = f"P{n:04d}"

    with atomic(db):                             # eşzamanlı kod/seq çakışması → 409 (flush dahil)
        b = Batch(code=code, factory_id=f.id, city=payload.city, lat=payload.lat,
                  lon=payload.lon, pamuk=payload.pamuk, polyester=payload.polyester,
                  elastan=payload.elastan, kumas=payload.kumas, gramaj=payload.gramaj,
                  en_m=payload.en_m, miktar_kg=payload.miktar_kg, kalite=payload.kalite,
                  min_fiyat=payload.min_fiyat, depo_gun=payload.depo_gun,
                  dogrulanmis=payload.dogrulanmis, reputation=f.reputation,
                  waste_code=payload.waste_code, status="listed")
        db.add(b)
        db.flush()
        uyari = ES.inconsistencies_for(b)
        b.inconsistencies = uyari or None
        append_event(db, b, "DMP_CREATED", {
            "code": b.code, "kumas": b.kumas, "miktar_kg": b.miktar_kg, "kalite": b.kalite,
            "pamuk": b.pamuk, "polyester": b.polyester, "elastan": b.elastan,
            "gramaj": b.gramaj, "sehir": b.city, "dogrulanmis": b.dogrulanmis,
            "waste_code": b.waste_code, "inconsistencies": uyari,
        }, commit=False)
        db.add(AuditLog(actor=f.name, action="create_dmp", entity="batch", entity_id=code,
                        detail=f"{b.kumas} {b.miktar_kg:.0f} kg, {len(uyari)} uyarı"))
    db.refresh(b)
    return _out(b)


@router.get("/{code}/inconsistencies", response_model=InconsistencyOut,
            summary="DMP tutarsızlık raporu")
def passport_inconsistencies(code: str, db: Session = Depends(get_db)):
    b = db.query(Batch).filter(Batch.code == code).first()
    if not b:
        raise HTTPException(404, f"DMP {code} bulunamadı")
    u = ES.inconsistencies_for(b)
    return InconsistencyOut(batch_code=code, inconsistencies=u, consistent=not u)


@router.get("/{code}/events", summary="Pasaport hash zinciri (menşe geçmişi)")
def passport_events(code: str, db: Session = Depends(get_db)):
    b = db.query(Batch).filter(Batch.code == code).first()
    if not b:
        raise HTTPException(404, f"DMP {code} bulunamadı")
    events = list(b.events)
    return {
        "batch_code": code,
        "chain": [{"seq": e.seq, "event_type": e.event_type, "payload": e.payload,
                   "prev_hash": e.prev_hash, "hash": e.hash,
                   "created_at": e.created_at} for e in events],
        "verification": verify_chain(events),
    }
