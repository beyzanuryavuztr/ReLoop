"""
Kamu uçları — dashboard (anonim/agrega), aktör listesi, yönetim (seed).
UÇBS/TABS ön-uyum, denetim modu ve açık veri `impact.py` / `compliance.py`'de mevcuttur.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..db import get_db
from ..impact_calc import dashboard_metrics
from ..models import AuditLog, Batch, Factory
from ..schemas import DashboardOut, FactoryOut, SeedResult
from ..seed_loader import load as seed_load

router = APIRouter(tags=["Kamu & Yönetim"])


def _current_dataset(db: Session) -> str:
    row = (db.query(AuditLog).filter(AuditLog.action == "seed")
             .order_by(AuditLog.id.desc()).first())
    return row.entity_id if row else "canonical"


@router.get("/public/dashboard", response_model=DashboardOut,
            summary="Kamu/OSB dashboard metrikleri (anonim-agrega)")
def dashboard(db: Session = Depends(get_db)):
    return dashboard_metrics(db, _current_dataset(db))


@router.get("/public/factories", response_model=list[FactoryOut],
            summary="Aktörler (harita için) — satıcı/geri dönüşümcü")
def factories(role: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Factory)
    if role:
        q = q.filter(Factory.role == role)
    return [FactoryOut.model_validate(f, from_attributes=True) for f in q.all()]


@router.get("/public/opendata/aggregate", summary="Açık veri: anonim/agrega bölgesel istatistik (#35)")
def opendata_aggregate(db: Session = Depends(get_db)):
    from ..models import Batch
    from ..pricing import ref_price
    rows: dict[str, dict] = {}
    for b in db.query(Batch).all():
        r = rows.setdefault(b.city, {"region": b.city, "batches": 0, "total_kg": 0.0,
                                     "price_sum": 0.0, "verified": 0})
        r["batches"] += 1
        r["total_kg"] += b.miktar_kg
        # Satıcının gizli rezervi (min_fiyat) DEĞİL, platformun ürettiği piyasa
        # referans fiyatı toplulaştırılır (denetim bulgusu 2.1: reserve sızıntısı kapandı).
        r["price_sum"] += ref_price(b)
        r["verified"] += 1 if b.dogrulanmis else 0
    out = []
    for r in rows.values():
        n = r["batches"]
        out.append({"region": r["region"], "batches": n,
                    "total_tonnes": round(r["total_kg"] / 1000, 1),
                    "avg_ref_price_tl": round(r["price_sum"] / n, 2),
                    "verified_share_pct": round(r["verified"] / n * 100, 0)})
    return {"license": "CC-BY 4.0 (örnek)", "pii": "yok (anonim/agrega)",
            "regions": sorted(out, key=lambda x: -x["total_tonnes"]),
            "note": ("Kişisel/firma verisi içermez; bölge düzeyinde toplulaştırılmıştır. "
                     "Fiyat = platform piyasa referansı (satıcı rezervi değil).")}


@router.get("/public/opendata/records", summary="Açık veri: filtrelenebilir anonim kayıtlar (araştırmacı, #36)")
def opendata_records(city: str | None = None, kumas: str | None = None,
                     kalite: str | None = None, limit: int = 100,
                     db: Session = Depends(get_db)):
    from ..models import Batch
    from ..pricing import fiber_class
    q = db.query(Batch)
    if city:
        q = q.filter(Batch.city == city)
    if kumas:
        q = q.filter(Batch.kumas == kumas)
    if kalite:
        q = q.filter(Batch.kalite == kalite)
    rows = []
    for b in q.limit(min(limit, 500)).all():
        # Anonim: firma adı ve tam fiyat gizli; bölge + lif sınıfı + kalite + miktar bandı
        band = ("<250" if b.miktar_kg < 250 else "250-800" if b.miktar_kg < 800
                else "800-1500" if b.miktar_kg < 1500 else "1500+")
        rows.append({"region": b.city, "fiber_class": fiber_class(b.pamuk, b.polyester),
                     "kumas": b.kumas, "kalite": b.kalite, "qty_band_kg": band,
                     "verified": b.dogrulanmis})
    return {"license": "CC-BY 4.0 (örnek)", "count": len(rows), "records": rows,
            "note": "Araştırmacı erişimi: firma kimliği ve kesin fiyat anonimleştirilmiştir."}


@router.post("/admin/seed", response_model=SeedResult,
             summary="Ekosistemi yükle/yenile (canonical | semireal)")
def reseed(dataset: str = "canonical", db: Session = Depends(get_db),
           _: bool = Depends(require_admin)):
    try:
        r = seed_load(db, dataset=dataset)
    except ValueError as e:
        raise HTTPException(400, str(e))
    msg = ("Referans ekosistem (80 fabrika / 250 parti / 60 talep, seed=42)"
           if r["dataset"] == "canonical"
           else "Yarı-gerçek ikinci koşu (gerçek coğrafya: 120/400/90, seed=2026)")
    return SeedResult(message=msg, **r)
