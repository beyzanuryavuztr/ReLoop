"""
Güven servisi — ticari zincir durum makinesi + teslim doğrulama + itibar.

Her durum geçişi, ilgili DMP'nin SHA-256 hash zincirine değişmez bir olay yazar
(chain.append_event). Böylece "kim, ne zaman, neyi" sırası tamper-evident kalır.
Teslimde beyan↔gözlem karşılaştırılır; uyuşmazlıkta emanet OTOMATİK askıya alınır.
"""
from __future__ import annotations

from .chain import append_event
from .models import AuditLog, Batch, PassportEvent, Transaction, TxState

# Teslim doğrulama toleransları (beyan ile gözlem arasında kabul edilebilir sapma)
TOLERANCE = {
    "pamuk": 5.0,       # ± % puan
    "polyester": 5.0,
    "elastan": 1.0,     # kontaminant — SIKI (küçük sapma bile önemli)
    "gramaj": 40.0,     # ± g/m²
    "miktar_kg_ratio": 0.90,  # teslim, mutabık miktarın en az %90'ı olmalı
}
CONTAMINANT_CAP = 2.0   # mekanik geri dönüşümü bozan mutlak elastan tavanı
CRITICAL_FIELDS = ("pamuk", "kumas", "kalite", "miktar_kg")  # teslimde bildirilmeli
KALITE_SIRA = {"A": 3, "B": 2, "C": 1}


def _yok(v) -> bool:
    """Gözlem 'yok' mu — None VEYA boş string (boş string kaçışını kapatır)."""
    return v is None or (isinstance(v, str) and v.strip() == "")


def compare_declared_observed(declared: dict, observed: dict, agreed_qty: float | None = None) -> dict:
    """Beyan (DMP) ile teslimde gözlenen değerleri karşılaştırır → uyuşmazlık alanları."""
    mm: dict = {}
    # Eksik kritik alan = eksik doğrulama (askıya alınır; boş string de eksiktir)
    eksik = [f for f in CRITICAL_FIELDS if f in declared and _yok(observed.get(f))]
    # Kontaminant (elastan) teslimde MUTLAKA ölçülmeli; ölçülmezse doğrulama eksik sayılır
    if _yok(observed.get("elastan")):
        eksik.append("elastan")
    if eksik:
        mm["_eksik_gozlem"] = eksik
    for f in ("pamuk", "polyester", "elastan", "gramaj"):
        if not _yok(observed.get(f)) and f in declared:
            if abs(float(observed[f]) - float(declared[f])) > TOLERANCE[f]:
                mm[f] = {"beyan": declared[f], "gozlem": observed[f],
                         "tolerans": TOLERANCE[f]}
    # Kontaminant mutlak tavan (beyanla farktan bağımsız)
    if not _yok(observed.get("elastan")) and float(observed["elastan"]) > CONTAMINANT_CAP:
        mm["elastan_tavan"] = {"gozlem": observed["elastan"], "tavan": CONTAMINANT_CAP,
                               "not": "mekanik geri dönüşüm kontaminant eşiği aşıldı"}
    if not _yok(observed.get("kumas")) and declared.get("kumas") and observed["kumas"] != declared["kumas"]:
        mm["kumas"] = {"beyan": declared["kumas"], "gozlem": observed["kumas"]}
    if not _yok(observed.get("kalite")) and declared.get("kalite"):
        if KALITE_SIRA.get(observed["kalite"], 0) < KALITE_SIRA.get(declared["kalite"], 0):
            mm["kalite"] = {"beyan": declared["kalite"], "gozlem": observed["kalite"],
                            "not": "teslim kalitesi beyandan düşük"}
    ref = agreed_qty if agreed_qty else declared.get("miktar_kg")
    if ref and observed.get("miktar_kg") is not None:
        if float(observed["miktar_kg"]) < TOLERANCE["miktar_kg_ratio"] * float(ref):
            mm["miktar_kg"] = {"beklenen_min": round(TOLERANCE["miktar_kg_ratio"] * ref, 1),
                               "gozlem": observed["miktar_kg"]}
    return mm


def batch_of(db, tx: Transaction) -> Batch:
    return db.get(Batch, tx.batch_id)


def transition(db, tx: Transaction, new_state: str, event_type: str,
               payload: dict | None = None, actor: str = "system", commit: bool = True):
    """Durumu güncelle + DMP zincirine değişmez olay yaz + denetim logu."""
    tx.status = new_state
    b = batch_of(db, tx)
    body = {"tx": tx.code, "state": new_state}
    if payload:
        body.update(payload)
    append_event(db, b, event_type, body, commit=False)
    db.add(AuditLog(actor=actor, action=f"tx_{new_state.lower()}",
                    entity="transaction", entity_id=tx.code,
                    detail=event_type))
    if commit:
        db.commit()
        db.refresh(tx)
    return tx


def update_reputation(db, batch: Batch, success: bool, commit: bool = False):
    """Teslim sonucuna göre satıcı fabrikanın itibarını günceller (0.50–0.99)."""
    f = batch.factory
    if not f:
        return
    if success:
        f.reputation = min(0.99, round(f.reputation + 0.01, 4))
    else:
        f.reputation = max(0.50, round(f.reputation - 0.05, 4))
    # İtibar tek kaynak (Factory); fabrikanın TÜM partilerine senkronla (bayat skoru önler)
    db.query(Batch).filter(Batch.factory_id == f.id).update(
        {Batch.reputation: f.reputation}, synchronize_session=False)
    if commit:
        db.commit()


def chain_events(db, batch_id: int):
    return (db.query(PassportEvent)
              .filter(PassportEvent.batch_id == batch_id)
              .order_by(PassportEvent.seq).all())
