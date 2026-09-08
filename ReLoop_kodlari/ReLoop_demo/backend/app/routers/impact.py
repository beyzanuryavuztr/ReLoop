"""
Kamu & politika etki motoru (Dalga 5) — karşılaştırma, atık önleme, fabrika panosu,
NDC projeksiyonu, "ne olurdu" simülatörü, karbon sertifikası PDF, UÇBS/TABS uyum,
formalizasyon sayacı, denetim modu.
"""
from __future__ import annotations
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import compliance as C
from .. import engine_service as ES
from .. import impact_calc as IC
from .. import ontology
from ..auth import require_actor
from ..db import get_db
from ..models import Batch, Demand, Transaction, TxState

router = APIRouter(prefix="/impact", tags=["Kamu & Politika Etki"])
comp_router = APIRouter(tags=["Kayıt & Denetim"])


def _gov_only(actor: str):
    """Devlet/denetim görünümü: yalnız tarafsız aktör (denetçi/bakanlık). Firma (satıcı/
    alıcı) bu agregeleri göremez → firma tarafı ile devlet tarafı erişimce AYRIDIR.
    actor 'anon' (demo, auth kapalı) ise serbest."""
    if actor != "anon" and actor not in ("auditor", "ministry"):
        raise HTTPException(403, f"'{actor}' rolü devlet/denetim görünümüne erişemez")


class SimIn(BaseModel):
    participation_pct: float = Field(ge=0, le=100, default=20)
    carbon_price_tl_per_ton: float = Field(ge=0, default=1000)
    new_facilities: int = Field(ge=0, default=0)


@router.get("/comparison", summary="CO₂/su/enerji: virgin vs geri kazanılan")
def comparison():
    return IC.comparison_table()


@router.get("/waste-prevention", summary="Atık önleme (kaskad; çöpe giden ~0)")
def waste_prevention(db: Session = Depends(get_db)):
    return IC.waste_prevention(db)


@router.get("/factory/{factory_id}", summary="Fabrika etki panosu")
def factory_panel(factory_id: int, db: Session = Depends(get_db),
                  actor: str = Depends(require_actor)):
    r = IC.factory_panel(db, factory_id)
    if r.get("error"):
        raise HTTPException(404, r["error"])
    return r


@router.get("/ndc", summary="NDC ulusal projeksiyon (rota-ağırlıklı CO₂; benimseme slider)")
def ndc(adoption_pct: float = Query(20.0, ge=0, le=100), db: Session = Depends(get_db)):
    return IC.national_projection(adoption_pct, IC.blended_co2_coeff(db))


@router.post("/simulate", summary="'Ne olurdu?' simülatörü (ulusal iklim/NDC, rota-ağırlıklı)")
def simulate(payload: SimIn, db: Session = Depends(get_db)):
    return IC.simulator(payload.participation_pct, payload.carbon_price_tl_per_ton,
                        payload.new_facilities, IC.blended_co2_coeff(db))


@router.get("/unit-economics", summary="Birim ekonomisi (komisyon − doğrulama = katkı marjı)")
def unit_economics(qty_kg: float = Query(2350, gt=0), price_tl_per_kg: float = Query(18, gt=0),
                   commission_pct: float = Query(3.0, ge=0, le=100), verified: bool = True):
    return IC.unit_economics(qty_kg, price_tl_per_kg, commission_pct, verified=verified)


@router.get("/revenue-model", summary="Üç katmanlı gelir modeli")
def revenue_model():
    return {"layers": IC.REVENUE_MODEL,
            "note": "Komisyon → Verified abonelik → veri lisansı."}


@router.get("/assumptions", summary="Şeffaflık: varsayım + yöntem + kaynak")
def assumptions():
    return {"coefficients": IC.COEFF, "sources": IC.SOURCES,
            "national_anchor_t": IC.NATIONAL_PRECONSUMER_T,
            "system_boundary": "Lif düzeyi; virgin pamuk vs mekanik geri kazanılan pamuk.",
            "note": "Her sayı varsayım+yöntem+kaynak ile sunulur; sentetik/yarı-gerçek veri."}


@router.get("/certificate/{tx_code}.pdf", summary="Karbon tasarruf sertifikası (işlem bazlı)")
def certificate(tx_code: str, db: Session = Depends(get_db)):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                    TableStyle)

    tx = db.query(Transaction).filter(Transaction.code == tx_code).first()
    if not tx:
        raise HTTPException(404, f"İşlem {tx_code} yok")
    if tx.status != TxState.COMPLETED:
        raise HTTPException(409, "Sertifika yalnız TAMAMLANMIŞ işlem için üretilir")
    b = db.get(Batch, tx.batch_id)
    if not b:
        raise HTTPException(404, "Parti bulunamadı")
    qty = tx.agreed_qty_kg or b.miktar_kg
    # Rota-ağırlıklı katsayı: sertifika, partinin GERÇEK kaskad rotasına göre CO₂
    # tasarrufu bildirir (tekstil-tekstile 1,60; downcycling/RDF daha düşük) — düz
    # 1,60 varsayımıyla abartılmaz (denetim bulgusu 1.5). Tamamlanan işlem geçerli bir
    # eşleşmeden gelir (open_trade sert filtre kontrolü) → tipik olarak tier-1 tekstil.
    best = ES.best_match_for_batch(b, db.query(Demand).all())
    route = ontology.cascade_route(b, best["score"] if best else None)
    co2_coeff = route.get("co2_saving_kg_per_kg") or IC.COEFF["co2_conservative_kg_per_kg"]
    co2_lo = qty * co2_coeff
    co2_hi = qty * IC.COEFF["co2_ecoinvent_kg_per_kg"]
    water = qty * IC.COEFF["water_l_per_kg"]

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20 * mm)
    st = getSampleStyleSheet()
    green = colors.HexColor("#2f7d5b")
    elems = [
        Paragraph("Karbon Tasarruf Sertifikası", st["Title"]),
        Paragraph("<i>ReLoop · döngüsel tekstil ticaret rayı</i>", st["Normal"]),
        Spacer(1, 8 * mm),
        Paragraph(f"İşlem <b>{tx.code}</b> · Pasaport <b>{b.code}</b> ({b.kumas}, "
                  f"{qty:.0f} kg geri kazanılan pamuk lifi)", st["Normal"]),
        Spacer(1, 4 * mm),
    ]
    tr = IC.tr_sayi
    rows = [["Gösterge", "Değer", "Hesap"],
            ["Geri kazanım rotası", route.get("label", "Tekstilden tekstile"), ""],
            ["Önlenen CO₂e (rota-ağırlıklı)", f"{tr(co2_lo)} kg",
             f"{tr(qty)} kg × {co2_coeff} kg/kg"],
            ["Önlenen CO₂e (ecoinvent üst sınır)", f"{tr(co2_hi)} kg",
             f"{tr(qty)} kg × {IC.COEFF['co2_ecoinvent_kg_per_kg']} kg/kg"],
            ["Su tasarrufu", f"{tr(water)} litre",
             f"{tr(qty)} kg × {IC.COEFF['water_l_per_kg']:.0f} litre/kg"]]
    t = Table(rows, colWidths=[55 * mm, 45 * mm, 60 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cfe8dd")),
                           ("BACKGROUND", (0, 0), (-1, 0), green),
                           ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    elems += [t, Spacer(1, 6 * mm),
              Paragraph("<font size=8 color='#666'>Sistem sınırı: lif düzeyi (virgin pamuk vs "
                        "mekanik geri kazanılan pamuk). Katsayılar: PE-International/Miljögiraff "
                        "(konservatif), ecoinvent (üst sınır). Sentetik/yarı-gerçek demo verisi; "
                        "akredite bir karbon kredisi değildir.</font>", st["Normal"])]
    doc.build(elems)
    return Response(buf.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": f"inline; filename=sertifika_{tx_code}.pdf"})


# --- Kayıt & denetim (Pillar G) ---
@comp_router.get("/compliance/tabs/{batch_code}", summary="UÇBS/TABS uyum kontrolü")
def tabs_check(batch_code: str, db: Session = Depends(get_db)):
    b = db.query(Batch).filter(Batch.code == batch_code).first()
    if not b:
        raise HTTPException(404, f"DMP {batch_code} yok")
    return C.tabs_check(b)


@comp_router.get("/compliance/eligibility/{batch_code}",
                 summary="Çift mevzuat uygunluğu: parti × alıcı firma (UYGUN/UYARI/ENGELLİ)")
def compliance_eligibility(batch_code: str, db: Session = Depends(get_db),
                           actor: str = Depends(require_actor)):
    """Devlet mevzuatı (UÇBS/TABS beyan tutarlılığı, atık kodu) + firma mevzuatı
    (GRS/OEKO-TEX/ZDHC'ten türetilmiş kabul kriteri) birlikte değerlendirilir.
    Yasal katman sağlanmazsa ENGELLİ; firma katmanı sağlanmazsa UYARI."""
    b = db.query(Batch).filter(Batch.code == batch_code).first()
    if not b:
        raise HTTPException(404, f"DMP {batch_code} bulunamadı")
    return ES.eligibility(b)


@comp_router.get("/compliance/formalization", summary="Kayıt dışı formalizasyon sayacı")
def formalization(db: Session = Depends(get_db), actor: str = Depends(require_actor)):
    _gov_only(actor)
    return C.formalization_counter(db)


@comp_router.get("/audit/{factory_name}", summary="Denetim modu: aktörün tüm geçmişi")
def audit(factory_name: str, db: Session = Depends(get_db),
          actor: str = Depends(require_actor)):
    _gov_only(actor)
    r = C.audit_view(db, factory_name)
    if r.get("error"):
        raise HTTPException(404, r["error"])
    return r
