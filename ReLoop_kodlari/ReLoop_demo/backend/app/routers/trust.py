"""
Güven & menşe rayı — provenance, hash zinciri doğrulama, QR, herkese açık DMP
sayfası (NFC'li) ve GRS chain-of-custody PDF.

Dürüst konumlandırma: "GRS ruhunda" denetlenebilir menşe zinciri belgesi üretilir;
akredite bir GRS sertifikası DEĞİLDİR (öyle iddia edilmez).
"""
from __future__ import annotations
import html
import io

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from qrcode.image.svg import SvgPathImage
from sqlalchemy.orm import Session

from .. import trust_service as TS
from ..chain import verify_chain
from ..db import get_db
from ..models import Batch, Factory, Transaction

router = APIRouter(tags=["Güven & Menşe"])

EVENT_TR = {
    "DMP_CREATED": "Dijital Malzeme Pasaportu oluşturuldu",
    "DMP_UPDATED": "Pasaport güncellendi", "LISTED": "Pazara listelendi",
    "MATCHED": "Talep ile eşleşti", "BID": "Teklif verildi",
    "ESCROW_OPENED": "Emanet açıldı", "SHIPPED": "Sevkiyat yapıldı",
    "DELIVERED": "Teslim edildi", "VERIFIED": "Teslim doğrulandı",
    "SUSPENDED": "Emanet askıya alındı / uyuşmazlık", "COMPLETED": "İşlem tamamlandı",
    "CANCELLED": "İşlem iptal / iade",
}


def _batch(db, code) -> Batch:
    b = db.query(Batch).filter(Batch.code == code).first()
    if not b:
        raise HTTPException(404, f"DMP {code} bulunamadı")
    return b


def _public_url(request: Request, code: str) -> str:
    return f"{str(request.base_url).rstrip('/')}/public/dmp/{code}"


@router.get("/trust/{code}/provenance", summary="Menşe: pasaport + zaman tüneli + doğrulama")
def provenance(code: str, db: Session = Depends(get_db)):
    b = _batch(db, code)
    events = TS.chain_events(db, b.id)
    txs = db.query(Transaction).filter(Transaction.batch_id == b.id).all()
    return {
        "batch_code": b.code,
        "passport": {
            "kumas": b.kumas, "pamuk": b.pamuk, "polyester": b.polyester,
            "elastan": b.elastan, "gramaj": b.gramaj, "kalite": b.kalite,
            "miktar_kg": b.miktar_kg, "sehir": b.city, "waste_code": b.waste_code,
            "dogrulanmis": b.dogrulanmis, "status": b.status,
        },
        "timeline": [{"seq": e.seq, "event": e.event_type,
                      "label": EVENT_TR.get(e.event_type, e.event_type),
                      "payload": e.payload, "hash": e.hash,
                      "created_at": e.created_at} for e in events],
        "verification": verify_chain(events),
        "transactions": [t.code for t in txs],
    }


@router.get("/trust/{code}/verify", summary="Hash zinciri bütünlük doğrulaması")
def verify(code: str, db: Session = Depends(get_db)):
    b = _batch(db, code)
    return verify_chain(TS.chain_events(db, b.id))


@router.get("/passports/{code}/qr.svg", summary="Parti QR (SVG, herkese açık DMP'ye)")
def qr_svg(code: str, request: Request, db: Session = Depends(get_db)):
    _batch(db, code)
    img = qrcode.make(_public_url(request, code), image_factory=SvgPathImage)
    buf = io.BytesIO()
    img.save(buf)
    return Response(buf.getvalue(), media_type="image/svg+xml")


@router.get("/passports/{code}/qr.png", summary="Parti QR (PNG)")
def qr_png(code: str, request: Request, db: Session = Depends(get_db)):
    _batch(db, code)
    img = qrcode.make(_public_url(request, code))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(buf.getvalue(), media_type="image/png")


@router.get("/public/dmp/{code}", response_class=HTMLResponse,
            summary="Herkese açık DMP sayfası (QR/NFC bunu açar)")
def public_dmp(code: str, request: Request, db: Session = Depends(get_db)):
    b = _batch(db, code)
    events = TS.chain_events(db, b.id)
    v = verify_chain(events)
    f = db.get(Factory, b.factory_id)
    rows = "".join(
        f"<tr><td>{e.seq}</td><td>{html.escape(EVENT_TR.get(e.event_type, e.event_type))}</td>"
        f"<td class='h'>{e.hash[:16]}…</td></tr>" for e in events)
    badge = ("<span class='ok'>✓ Zincir doğrulandı</span>" if v["valid"]
             else "<span class='bad'>✗ Zincir bozulmuş</span>")
    lif = f"%{b.pamuk:.0f} pamuk · %{b.polyester:.0f} polyester · %{b.elastan:.0f} elastan"
    dogr = "Doğrulanmış (NIR/lab)" if b.dogrulanmis else "Beyan (doğrulama bekliyor)"
    qr_url = f"/passports/{code}/qr.svg"
    return HTMLResponse(_PUBLIC_HTML.format(
        code=html.escape(b.code), badge=badge, kumas=html.escape(b.kumas), lif=lif,
        gramaj=b.gramaj, kalite=html.escape(b.kalite), miktar=f"{b.miktar_kg:.0f}",
        sehir=html.escape(b.city), waste=html.escape(b.waste_code), dogr=dogr,
        firma=html.escape(f.city if f else "-"), rows=rows, qr_url=qr_url,
        seq_count=len(events)))


@router.get("/trust/{code}/grs.pdf", summary="GRS ruhunda menşe zinciri PDF (chain-of-custody)")
def grs_pdf(code: str, db: Session = Depends(get_db)):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                    TableStyle)

    b = _batch(db, code)
    events = TS.chain_events(db, b.id)
    v = verify_chain(events)
    f = db.get(Factory, b.factory_id)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=16 * mm)
    st = getSampleStyleSheet()
    green = colors.HexColor("#2f7d5b")
    elems = [
        Paragraph("ReLoop — Menşe Zinciri Belgesi", st["Title"]),
        Paragraph("<i>Chain-of-Custody · GRS ruhunda denetlenebilir menşe kaydı</i>", st["Normal"]),
        Spacer(1, 6 * mm),
        Paragraph(f"<b>Pasaport:</b> {b.code} &nbsp;|&nbsp; <b>Atık kodu:</b> {b.waste_code} "
                  f"&nbsp;|&nbsp; <b>Menşe:</b> {f.city if f else '-'}", st["Normal"]),
        Spacer(1, 3 * mm),
    ]
    info = [["Kumaş", b.kumas],
            ["Lif", f"%{b.pamuk:.0f} pamuk / %{b.polyester:.0f} polyester / %{b.elastan:.0f} elastan"],
            ["Gramaj", f"{b.gramaj} g/m²"], ["Kalite", b.kalite],
            ["Miktar", f"{b.miktar_kg:.0f} kg"],
            ["Doğrulama", "NIR/lab doğrulanmış" if b.dogrulanmis else "Beyan"]]
    t1 = Table(info, colWidths=[45 * mm, 110 * mm])
    t1.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cfe8dd")),
                            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eafff5")),
                            ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    elems += [t1, Spacer(1, 6 * mm),
              Paragraph("<b>Menşe zinciri (SHA-256, tamper-evident)</b>", st["Heading3"])]
    chain = [["#", "Olay", "Önceki hash", "Hash"]]
    for e in events:
        chain.append([str(e.seq), EVENT_TR.get(e.event_type, e.event_type),
                      e.prev_hash[:12] + "…", e.hash[:12] + "…"])
    t2 = Table(chain, colWidths=[10 * mm, 62 * mm, 40 * mm, 40 * mm])
    t2.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cfe8dd")),
                            ("BACKGROUND", (0, 0), (-1, 0), green),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("FONTSIZE", (0, 0), (-1, -1), 8)]))
    verdict = ("✓ Zincir bütünlüğü DOĞRULANDI" if v["valid"]
               else "✗ Zincir bütünlüğü BOZUK")
    elems += [t2, Spacer(1, 5 * mm),
              Paragraph(f"<b>{verdict}</b> — {len(events)} olay, kök hash sabit.", st["Normal"]),
              Spacer(1, 3 * mm),
              Paragraph("<font size=8 color='#666'>Bu belge ReLoop platformunun ürettiği "
                        "denetlenebilir bir menşe kaydıdır; akredite bir GRS sertifikası değildir. "
                        "Sentetik/yarı-gerçek demo verisi.</font>", st["Normal"])]
    doc.build(elems)
    pdf = buf.getvalue()
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"inline; filename=mense_{code}.pdf"})


_PUBLIC_HTML = """<!doctype html><html lang=tr><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>ReLoop DMP · {code}</title>
<style>
:root{{color-scheme:light dark}}
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#0b1f17;color:#eafff5}}
.wrap{{max-width:640px;margin:0 auto;padding:20px}}
.card{{background:#12352a;border:1px solid #1f5a44;border-radius:16px;padding:20px;margin:14px 0}}
h1{{font-size:20px;margin:0 0 4px}} .sub{{opacity:.7;font-size:13px}}
.ok{{color:#3ee6a0;font-weight:700}} .bad{{color:#ff6b6b;font-weight:700}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
td{{padding:6px 8px;border-bottom:1px solid #1f5a44;vertical-align:top}}
.h{{font-family:ui-monospace,monospace;color:#7fdcb6}}
.kv{{display:grid;grid-template-columns:auto 1fr;gap:6px 14px;font-size:14px}}
.kv b{{color:#3ee6a0;font-weight:600}}
.qr{{background:#fff;border-radius:12px;padding:10px;width:150px}}
button{{background:#1f7a57;color:#fff;border:0;border-radius:10px;padding:10px 14px;font-size:14px;cursor:pointer}}
#nfc{{margin-top:10px}} .muted{{opacity:.6;font-size:12px}}
</style></head><body><div class=wrap>
<div class=card>
  <h1>♻️ Dijital Malzeme Pasaportu</h1>
  <div class=sub>{code} · {badge}</div>
</div>
<div class=card>
  <div class=kv>
    <b>Kumaş</b><span>{kumas}</span>
    <b>Lif</b><span>{lif}</span>
    <b>Gramaj</b><span>{gramaj} g/m²</span>
    <b>Kalite</b><span>{kalite}</span>
    <b>Miktar</b><span>{miktar} kg</span>
    <b>Menşe</b><span>{firma} (OSB)</span>
    <b>Atık kodu</b><span>{waste}</span>
    <b>Durum</b><span>{dogr}</span>
  </div>
</div>
<div class=card>
  <h1 style="font-size:16px">Menşe zinciri <span class=muted>({seq_count} olay · SHA-256)</span></h1>
  <table>{rows}</table>
</div>
<div class=card style="display:flex;gap:16px;align-items:center;flex-wrap:wrap">
  <img class=qr src="{qr_url}" alt="QR" width=150 height=150>
  <div>
    <div>Bu pasaportu paylaş / etikete yaz.</div>
    <button id=nfc>📱 NFC etiketine yaz</button>
    <div id=nfcout class=muted style="margin-top:6px"></div>
  </div>
</div>
<p class=muted>ReLoop · denetlenebilir menşe kaydı. Sentetik/yarı-gerçek demo verisi.</p>
</div>
<script>
// Gerçek Web NFC (Android Chrome + NTAG213). Desteklenmiyorsa dürüstçe bildirir.
document.getElementById('nfc').onclick = async () => {{
  const out = document.getElementById('nfcout');
  if (!('NDEFReader' in window)) {{ out.textContent =
    'Bu cihaz/tarayıcı Web NFC desteklemiyor (Android Chrome gerekir). QR kullanın.'; return; }}
  try {{
    const w = new NDEFReader();
    await w.write({{ records: [{{ recordType: 'url', data: location.href }}] }});
    out.textContent = '✓ Pasaport bağlantısı NFC etiketine yazıldı.';
  }} catch (e) {{ out.textContent = 'NFC yazma iptal/hedef bulunamadı: ' + e; }}
}};
</script></body></html>"""
