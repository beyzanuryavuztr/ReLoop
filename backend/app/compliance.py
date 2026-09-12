"""
Kayıt & denetim (Dalga 5, Pillar G):
  • UÇBS/TABS uyum kontrolü (#32) — zorunlu alanlar + süre/beyan uyarısı
  • Kayıt dışı formalizasyon sayacı (#33) — kayıt içine taşınan ekonomik değer
  • Denetim modu (#34) — bir aktörün tüm geçmişi tek görünümde

UÇBS = Ulusal Çevre Bilgi Sistemi (19.12.2025'te EÇBS'nin yerini aldı; tüm atık
beyanı, lisans, izin ve raporlama tek çatı altında). TABS = Atık Beyan/Takip.
Zorunlu alanlar ve 04 02 22 atık kodu Atık Yönetimi Yönetmeliği ile uyumludur.
"""
from __future__ import annotations

from .chain import verify_chain
from .models import (Batch, Factory, PassportEvent, Transaction, TxState)

TABS_REQUIRED = ["waste_code", "miktar_kg", "kumas", "city", "kalite"]
BEYAN_SURE_GUN = 180   # firenin beyan/sevk için önerilen üst süre (depo_gun eşiği)


def tabs_check(b: Batch) -> dict:
    missing = [f for f in TABS_REQUIRED if getattr(b, f, None) in (None, "", 0)]
    code_ok = bool(b.waste_code) and len(b.waste_code.split()) == 3
    deadline_warn = b.depo_gun is not None and b.depo_gun > BEYAN_SURE_GUN
    ok = (not missing) and code_ok and not deadline_warn
    return {
        "batch_code": b.code, "compliant": ok,
        "required_fields": TABS_REQUIRED, "missing_fields": missing,
        "waste_code": b.waste_code, "waste_code_format_ok": code_ok,
        "storage_days": b.depo_gun,
        "deadline_warning": (f"Depolama {b.depo_gun} gün > {BEYAN_SURE_GUN} gün; "
                             "beyan/sevk süresi yaklaşıyor." if deadline_warn else None),
        "note": "İstemci taraflı ön uyum kontrolü (UÇBS/TABS gönderiminden önce).",
    }


def formalization_counter(db) -> dict:
    """
    Kayıt dışı/gri alanda kalan fire ticaretinin kayıt içine taşınan değeri:
    tamamlanan işlemlerin toplam bedeli + kayıtlı işlem sayısı.
    """
    completed = db.query(Transaction).filter(Transaction.status == TxState.COMPLETED).all()
    value = sum((t.agreed_price or 0) * (t.agreed_qty_kg or 0) for t in completed)
    all_listed = db.query(Batch).count()
    return {
        "formalized_transactions": len(completed),
        "formalized_value_tl": round(value, 0),
        "registered_passports": all_listed,
        "note": ("Her işlem DMP + değişmez menşe zinciri + TABS beyanıyla kayıt içine alınır; "
                 "aracıya dayalı gri ticaret şeffaf, izlenebilir kayda dönüşür."),
    }


def audit_view(db, factory_code_or_name: str) -> dict:
    """Denetim modu: bir fabrikanın tüm partileri + zincirleri + işlemleri tek görünümde."""
    f = (db.query(Factory).filter(Factory.name == factory_code_or_name).first())
    if not f:
        return {"error": f"Fabrika '{factory_code_or_name}' bulunamadı"}
    batches = db.query(Batch).filter(Batch.factory_id == f.id).all()
    out_batches = []
    for b in batches:
        events = (db.query(PassportEvent).filter(PassportEvent.batch_id == b.id)
                    .order_by(PassportEvent.seq).all())
        txs = db.query(Transaction).filter(Transaction.batch_id == b.id).all()
        out_batches.append({
            "batch_code": b.code, "kumas": b.kumas, "miktar_kg": b.miktar_kg,
            "status": b.status, "chain_len": len(events),
            "chain_valid": verify_chain(events)["valid"],
            "transactions": [{"code": t.code, "status": t.status} for t in txs],
            "tabs": tabs_check(b)["compliant"],
        })
    return {
        "factory": f.name, "city": f.city, "reputation": f.reputation,
        "batch_count": len(batches), "batches": out_batches,
        "note": "Denetçi görünümü: tüm menşe zincirleri ve işlem durumları tek ekranda.",
    }
