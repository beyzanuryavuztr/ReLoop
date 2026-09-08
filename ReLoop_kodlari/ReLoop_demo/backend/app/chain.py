"""
Pasaport hash zinciri — değişmez menşe kaydı (SHA-256).

Her DMP olayı bir öncekinin hash'ini içerir:
    hash_n = SHA256( prev_hash || seq || event_type || canonical_json(payload) )
Böylece geçmiş bir olay değiştirilirse sonraki tüm hash'ler tutmaz → tamper-evident.
Bu, blockchain DEĞİLDİR; tek kurumda tutulan denetlenebilir bir hash zinciridir
(GRS chain-of-custody ruhunda). Dürüst konumlandırma budur.
"""
from __future__ import annotations
import hashlib
import json

GENESIS = "0" * 64


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def event_hash(prev_hash: str, seq: int, event_type: str, payload: dict) -> str:
    raw = f"{prev_hash}|{seq}|{event_type}|{_canonical(payload)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def append_event(db, batch, event_type: str, payload: dict, commit: bool = True):
    """Batch'in zincirine yeni olay ekler; seq/prev_hash/hash otomatik hesaplanır."""
    from .models import PassportEvent  # geç import (döngü önleme)
    last = (db.query(PassportEvent)
              .filter(PassportEvent.batch_id == batch.id)
              .order_by(PassportEvent.seq.desc())
              .first())
    seq = 0 if last is None else last.seq + 1
    prev = GENESIS if last is None else last.hash
    h = event_hash(prev, seq, event_type, payload)
    ev = PassportEvent(batch_id=batch.id, seq=seq, event_type=event_type,
                       payload=payload, prev_hash=prev, hash=h)
    db.add(ev)
    db.flush()   # aynı istek içinde birden çok append'te seq monotonluğu (autoflush=False)
    if commit:
        db.commit()
        db.refresh(ev)
    return ev


def verify_chain(events) -> dict:
    """
    Zinciri baştan sona doğrular.
    Dönen: {valid: bool, length: int, broken_at: None|seq}
    """
    prev = GENESIS
    for ev in sorted(events, key=lambda e: e.seq):
        expect = event_hash(prev, ev.seq, ev.event_type, ev.payload)
        if expect != ev.hash or ev.prev_hash != prev:
            return {"valid": False, "length": len(events), "broken_at": ev.seq}
        prev = ev.hash
    return {"valid": True, "length": len(events), "broken_at": None}
