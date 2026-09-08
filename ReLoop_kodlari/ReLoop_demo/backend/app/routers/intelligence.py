"""
Eşleştirme zekâsı uçları (Dalga 3) — kaskad, lot birleştirme, Pareto çok-amaçlı,
proaktif tahmin + bildirim, "neden eşleşmedi", ağırlık öğrenme.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import matching_advanced as MA
from .. import ontology
from ..auth import require_actor
from ..db import get_db
from ..models import Batch, Demand, Factory, Notification, Transaction, TxState

router = APIRouter(prefix="/matching", tags=["Eşleştirme Zekâsı"])
notif_router = APIRouter(prefix="/notifications", tags=["Bildirimler"])


class ForecastIn(BaseModel):
    factory_id: int
    monthly_kg: float = Field(gt=0)
    fire_rate_pct: float = Field(gt=0, le=100)
    kumas: str = "suprem"
    pamuk: float = 100
    polyester: float = 0
    elastan: float = 0
    gramaj: int = 180
    kalite: str = "B"


@router.get("/ontology", summary="Çapraz sektör downcycling rotaları (şeffaflık)")
def get_ontology():
    return {"textile_threshold": ontology.TEXTILE_ESIK, "routes": ontology.all_routes(),
            "note": "Tekstil-önce; sınırlı ve tanımlı rotalar. Genel çok-sektör platformu değil."}


@router.get("/cascade/{batch_code}", summary="Kaskad yerleşim (tekstil→downcycling→RDF)")
def cascade(batch_code: str, db: Session = Depends(get_db)):
    b = db.query(Batch).filter(Batch.code == batch_code).first()
    if not b:
        raise HTTPException(404, f"DMP {batch_code} bulunamadı")
    return MA.cascade_for_batch(b, db.query(Demand).all())


@router.get("/cascade-summary", summary="Kaskad özeti (yerleşim %100; kanal kırılımı)")
def cascade_summary(db: Session = Depends(get_db)):
    return MA.cascade_summary(db.query(Batch).all(), db.query(Demand).all())


@router.get("/demand/{code}/lot-merge", summary="Küçük lotları birleştirerek talebi karşıla")
def lot_merge(code: str, radius_km: float = Query(60.0, gt=0), db: Session = Depends(get_db)):
    d = db.query(Demand).filter(Demand.code == code).first()
    if not d:
        raise HTTPException(404, f"Talep {code} bulunamadı")
    avail = db.query(Batch).filter(Batch.status != "sold").all()
    return MA.lot_merge_for_demand(d, avail, radius_km=radius_km)


@router.get("/demand/{code}/pareto", summary="Pareto: karbon/maliyet/mesafe/değer + cephe")
def pareto(code: str, w_carbon: float = Query(0.25, ge=0), w_cost: float = Query(0.25, ge=0),
           w_distance: float = Query(0.25, ge=0), w_value: float = Query(0.25, ge=0),
           db: Session = Depends(get_db)):
    d = db.query(Demand).filter(Demand.code == code).first()
    if not d:
        raise HTTPException(404, f"Talep {code} bulunamadı")
    avail = db.query(Batch).filter(Batch.status != "sold").all()
    return MA.pareto_for_demand(d, avail, w_carbon, w_cost, w_distance, w_value)


@router.get("/demand/{code}/rejections", summary="Neden eşleşmedi (sert filtre gerekçeleri)")
def rejections(code: str, db: Session = Depends(get_db)):
    d = db.query(Demand).filter(Demand.code == code).first()
    if not d:
        raise HTTPException(404, f"Talep {code} bulunamadı")
    avail = db.query(Batch).filter(Batch.status != "sold").all()
    return MA.rejections_for_demand(d, avail)


@router.post("/forecast", summary="Proaktif: üretim planından fire tahmini + alıcı bildirimi")
def forecast(payload: ForecastIn, db: Session = Depends(get_db),
             _: str = Depends(require_actor)):
    f = db.get(Factory, payload.factory_id)
    if not f:
        raise HTTPException(400, f"Fabrika {payload.factory_id} yok")
    res = MA.forecast(f, db.query(Demand).all(), payload.monthly_kg, payload.fire_rate_pct,
                      payload.kumas, payload.pamuk, payload.polyester, payload.elastan,
                      payload.gramaj, payload.kalite)
    # Önceden eşleşen alıcılara bildirim yaz (panel için). İDEMPOTAN: aynı alıcı+talep
    # için okunmamış bir öngörü bildirimi varsa yenisi eklenmez (tekrar çağrıda şişmez);
    # var olan mesaj/skor güncellenir.
    for pm in res["prematched_buyers"]:
        msg = (f"{f.name}: ~{res['forecast_fire_kg']:.0f} kg {payload.kumas} firesi "
               f"öngörülüyor (uyum %{pm['score']*100:.0f}).")
        existing = (db.query(Notification)
                      .filter(Notification.recipient == pm["buyer"],
                              Notification.kind == "prematch",
                              Notification.demand_code == pm["demand_code"],
                              Notification.batch_ref == "FORECAST",
                              Notification.read.is_(False))
                      .first())
        if existing:
            existing.score, existing.message = pm["score"], msg
        else:
            db.add(Notification(
                recipient=pm["buyer"], kind="prematch", demand_code=pm["demand_code"],
                batch_ref="FORECAST", score=pm["score"], message=msg))
    db.commit()
    return res


@router.get("/learn", summary="Ağırlık öğrenme önerisi (tamamlanan işlemlerden; canlıyı değiştirmez)")
def learn(db: Session = Depends(get_db)):
    from .. import engine_service as ES
    comps = []
    for tx in db.query(Transaction).filter(Transaction.status == TxState.COMPLETED).all():
        b = db.get(Batch, tx.batch_id)
        d = db.get(Demand, tx.demand_id)
        if b and d:
            comps.append(ES.score_pair(b, d)["components"])
    return MA.propose_weights(comps)


@notif_router.get("", summary="Bildirim listesi (proaktif eşleşmeler)")
def list_notifications(recipient: str | None = None, unread: bool = False,
                       limit: int = Query(50, ge=1, le=200),
                       db: Session = Depends(get_db)):
    q = db.query(Notification)
    if recipient:
        q = q.filter(Notification.recipient == recipient)
    if unread:
        q = q.filter(Notification.read.is_(False))
    rows = q.order_by(Notification.id.desc()).limit(limit).all()
    return [{"id": n.id, "recipient": n.recipient, "kind": n.kind,
             "demand_code": n.demand_code, "score": n.score, "message": n.message,
             "read": n.read, "created_at": n.created_at} for n in rows]


@notif_router.post("/{nid}/read", summary="Bildirimi okundu işaretle")
def mark_read(nid: int, db: Session = Depends(get_db)):
    n = db.get(Notification, nid)
    if not n:
        raise HTTPException(404, "Bildirim yok")
    n.read = True
    db.commit()
    return {"id": nid, "read": True}
