"""
Ticari zincir — kör teklif → pazarlık → emanet → sevkiyat → teslim doğrulama.
Her geçiş DMP hash zincirine değişmez olay yazar; tutarsız teslimde emanet
OTOMATİK askıya alınır (trust_service). Durum-değiştiren uçlar require_actor ile
kapılıdır (RELOOP_REQUIRE_AUTH açıksa zorunlu; demo'da açık).
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import engine_service as ES
from .. import trust_service as TS
from ..auth import require_actor
from ..chain import append_event
from ..db import atomic, get_db
from ..models import (Batch, Bid, Demand, DeliveryVerification, Transaction,
                      TxState)
from ..schemas import (BidIn, BidOut, DeliverIn, DisputeIn, ResolveIn,
                       TransactionOut, TradeOpenIn)

router = APIRouter(prefix="/trade", tags=["Ticari Zincir"])


def _next_code(db: Session) -> str:
    last = db.query(Transaction).order_by(Transaction.id.desc()).first()
    n = (int(last.code.split("-")[1]) + 1) if last else 1
    return f"TX-{n:04d}"


def _get(db: Session, code: str) -> Transaction:
    tx = db.query(Transaction).filter(Transaction.code == code).first()
    if not tx:
        raise HTTPException(404, f"İşlem {code} bulunamadı")
    return tx


def _require(tx: Transaction, *states: str):
    if tx.status not in states:
        raise HTTPException(409, f"İşlem durumu '{tx.status}'; beklenen: {', '.join(states)}")


# Doğrulanmış kullanıcı rolü → ticaret rolü (recycler alıcıdır)
_ROLE_TRADE = {"seller": "seller", "recycler": "buyer"}


def _enforce_role(actor: str, allowed: set[str]):
    """actor 'anon' ise (demo, auth kapalı) serbest; değilse rolü doğrulanmış kimlikten gelir."""
    if actor == "anon":
        return
    tr = _ROLE_TRADE.get(actor)
    if tr not in allowed:
        raise HTTPException(403, f"'{actor}' rolü bu işlemi yapamaz")


def _enforce_actor_role(actor: str, allowed_user_roles: set[str]):
    """Kullanıcı rolü (seller/recycler/auditor/ministry) doğrudan yetki kontrolü.
    Para hareketi olan uçlarda (emanet aç/çöz/kapat) taraf çıkar çatışmasını önler:
    örn. uyuşmazlığı yalnız TARAFSIZ bir aktör (denetçi/bakanlık) çözebilir; satıcı
    kendi emanetini serbest bırakamaz. actor 'anon' (demo, auth kapalı) ise serbest."""
    if actor == "anon":
        return
    if actor not in allowed_user_roles:
        raise HTTPException(403, f"'{actor}' rolü bu işlemi yapamaz (çıkar çatışması koruması)")


@router.get("", response_model=list[TransactionOut], summary="İşlem listesi")
def list_trades(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Transaction)
    if status:
        q = q.filter(Transaction.status == status)
    return [TransactionOut.model_validate(t, from_attributes=True)
            for t in q.order_by(Transaction.id).all()]


@router.get("/{code}", summary="İşlem detayı + teklif geçmişi")
def get_trade(code: str, db: Session = Depends(get_db)):
    tx = _get(db, code)
    b = db.get(Batch, tx.batch_id)
    d = db.get(Demand, tx.demand_id)
    return {
        "transaction": TransactionOut.model_validate(tx, from_attributes=True),
        "batch_code": b.code if b else None,
        "demand_code": d.code if d else None,
        "bids": [BidOut.model_validate(x, from_attributes=True) for x in tx.bids],
    }


@router.post("/open", response_model=TransactionOut, status_code=201,
             summary="İşlem aç (eşleşen parti-talep)")
def open_trade(payload: TradeOpenIn, db: Session = Depends(get_db),
               _: str = Depends(require_actor)):
    # Satır kilidi: aynı partiye eşzamanlı iki 'open' çağrısını serialize eder
    # (Postgres FOR UPDATE; SQLite'ta yazma serileştirmesiyle kapanır). Kilit,
    # atomic() commit'ine kadar tutulur → check-then-act yarışı ortadan kalkar.
    b = (db.query(Batch).filter(Batch.code == payload.batch_code)
           .with_for_update().first())
    d = db.query(Demand).filter(Demand.code == payload.demand_code).first()
    if not b or not d:
        raise HTTPException(400, "Parti veya talep bulunamadı")
    # Eşleşme geçerliliği: sert filtreyi geçmeyen parti-talep çiftinde işlem AÇILMAZ.
    # Aksi halde geçersiz bir çift COMPLETED'a sürülüp sahte etki/karbon sertifikası
    # üretebilirdi (denetim bulgusu 1.3/1.6).
    ok, reason = ES.hard_filter(b, d)
    if not ok:
        raise HTTPException(422, f"Parti {b.code} ↔ talep {d.code} eşleşmiyor: {reason}")
    # Envanter kilidi: satılmış ya da aktif işlemi olan parti yeni işleme açılmaz
    if b.status == "sold":
        raise HTTPException(409, f"Parti {b.code} satılmış; yeni işleme kapalı")
    active = (db.query(Transaction)
                .filter(Transaction.batch_id == b.id,
                        Transaction.status.notin_([TxState.COMPLETED, TxState.CANCELLED]))
                .first())
    if active:
        raise HTTPException(409, f"Parti {b.code} için zaten aktif işlem var ({active.code})")
    with atomic(db):
        tx = Transaction(code=_next_code(db), batch_id=b.id, demand_id=d.id,
                         status=TxState.OPEN)
        db.add(tx)
        db.flush()
        append_event(db, b, "MATCHED",
                     {"tx": tx.code, "demand": d.code, "buyer": d.buyer}, commit=False)
    db.refresh(tx)
    return TransactionOut.model_validate(tx, from_attributes=True)


@router.post("/{code}/bid", summary="Kör teklif / karşı teklif / kabul")
def place_bid(code: str, payload: BidIn, db: Session = Depends(get_db),
              actor: str = Depends(require_actor)):
    tx = _get(db, code)
    _require(tx, TxState.OPEN, TxState.BID, TxState.COUNTERED)
    _enforce_role(actor, {"buyer", "seller"})
    if actor != "anon" and payload.by_role != _ROLE_TRADE.get(actor):
        raise HTTPException(403, f"Kimliğin '{actor}'; '{payload.by_role}' rolüyle teklif veremezsin")
    # Son teklif (yeni teklif eklenmeden ÖNCE) — kabul bütünlüğü için gerekli
    last = (db.query(Bid).filter(Bid.transaction_id == tx.id)
              .order_by(Bid.id.desc()).first())
    with atomic(db):
        db.add(Bid(transaction_id=tx.id, by_role=payload.by_role, kind=payload.kind,
                   amount=payload.amount, qty_kg=payload.qty_kg, note=payload.note))
        if payload.kind == "accept":
            # İki taraflı rıza: (1) ortada kabul edilecek bir teklif OLMALI (tek taraflı
            # keyfi kabul yasak), (2) kendi teklifini kabul edemezsin, (3) kabul son
            # teklifle bire bir uyuşmalı. Aksi halde "güvenilir ticari ray" delinir.
            if last is None:
                raise HTTPException(409, "Kabul edilecek bir teklif yok; önce teklif/karşı teklif verilmeli")
            if payload.by_role == last.by_role:
                raise HTTPException(409, "Kendi teklifini kabul edemezsin; karşı taraf onaylamalı")
            if abs(payload.amount - last.amount) > 1e-6 or abs(payload.qty_kg - last.qty_kg) > 1e-6:
                raise HTTPException(409, f"Kabul, son teklifle uyuşmalı "
                                        f"({last.amount:.2f} TL/kg, {last.qty_kg:.0f} kg)")
            tx.agreed_price, tx.agreed_qty_kg = payload.amount, payload.qty_kg
            TS.transition(db, tx, TxState.ACCEPTED, "BID",
                          {"kind": "accept", "price": payload.amount, "qty_kg": payload.qty_kg},
                          actor=payload.by_role, commit=False)
        elif payload.kind == "reject":
            TS.transition(db, tx, TxState.CANCELLED, "BID", {"kind": "reject"},
                          actor=payload.by_role, commit=False)
        else:
            new = TxState.COUNTERED if payload.kind == "counter" else TxState.BID
            TS.transition(db, tx, new, "BID",
                          {"kind": payload.kind, "amount": payload.amount},
                          actor=payload.by_role, commit=False)
    db.refresh(tx)
    return get_trade(code, db)


@router.post("/{code}/escrow", response_model=TransactionOut,
             summary="Emanet aç (bedel kilitlenir)")
def open_escrow(code: str, db: Session = Depends(get_db), actor: str = Depends(require_actor)):
    tx = _get(db, code)
    _require(tx, TxState.ACCEPTED)
    _enforce_actor_role(actor, {"seller", "recycler"})   # emaneti mutabık iki taraftan biri açar
    with atomic(db):
        TS.transition(db, tx, TxState.ESCROW, "ESCROW_OPENED",
                      {"price": tx.agreed_price, "qty_kg": tx.agreed_qty_kg}, commit=False)
    db.refresh(tx)
    return TransactionOut.model_validate(tx, from_attributes=True)


@router.post("/{code}/ship", response_model=TransactionOut,
             summary="Satıcı sevkiyatı yaptı")
def ship(code: str, db: Session = Depends(get_db), actor: str = Depends(require_actor)):
    tx = _get(db, code)
    _require(tx, TxState.ESCROW)
    _enforce_role(actor, {"seller"})             # sevkiyat satıcının işi
    with atomic(db):
        TS.transition(db, tx, TxState.SHIPPED, "SHIPPED", {}, actor="seller", commit=False)
    db.refresh(tx)
    return TransactionOut.model_validate(tx, from_attributes=True)


@router.post("/{code}/deliver", summary="Teslim + doğrulama (tutarsızsa emanet askıya alınır)")
def deliver(code: str, payload: DeliverIn, db: Session = Depends(get_db),
            actor: str = Depends(require_actor)):
    tx = _get(db, code)
    _require(tx, TxState.SHIPPED)                 # teslim, sevkiyat sonrası (adım atlanamaz)
    _enforce_role(actor, {"buyer"})              # teslim doğrulama alıcının işi
    b = db.get(Batch, tx.batch_id)
    if not b:
        raise HTTPException(404, "Parti bulunamadı")
    declared = {"pamuk": b.pamuk, "polyester": b.polyester, "elastan": b.elastan,
                "kumas": b.kumas, "gramaj": b.gramaj, "kalite": b.kalite,
                "miktar_kg": b.miktar_kg}
    observed = payload.model_dump(exclude_none=True)
    photo = observed.pop("photo_ref", None)
    mm = TS.compare_declared_observed(declared, observed, tx.agreed_qty_kg)
    mismatch = bool(mm)

    with atomic(db):
        db.add(DeliveryVerification(
            transaction_id=tx.id, declared=declared, observed=observed,
            mismatch=mismatch, mismatch_fields=mm or None, photo_ref=photo,
            decision="suspended" if mismatch else "verified"))
        # Önce fiziksel teslim kaydı (zaman tünelinde "Teslim edildi"), sonra doğrulama
        TS.transition(db, tx, TxState.DELIVERED, "DELIVERED", {"photo": bool(photo)},
                      actor="buyer", commit=False)
        if mismatch:
            TS.transition(db, tx, TxState.SUSPENDED, "SUSPENDED",
                          {"reason": "teslim beyanla uyuşmuyor", "mismatch": mm},
                          actor="buyer", commit=False)
        else:
            TS.transition(db, tx, TxState.VERIFIED, "VERIFIED", {}, actor="buyer", commit=False)
    db.refresh(tx)
    return {"transaction": TransactionOut.model_validate(tx, from_attributes=True),
            "mismatch": mismatch, "mismatch_fields": mm,
            "message": ("Tutarsızlık: emanet otomatik askıya alındı."
                        if mismatch else "Teslim doğrulandı; emanet çözülmeye hazır.")}


@router.post("/{code}/complete", response_model=TransactionOut,
             summary="Emaneti çöz, işlemi kapat (itibar +)")
def complete(code: str, db: Session = Depends(get_db), actor: str = Depends(require_actor)):
    tx = _get(db, code)
    _require(tx, TxState.VERIFIED)
    # Emaneti (satıcıya) alıcı serbest bırakır; satıcı KENDİ emanetini serbest bırakamaz.
    # Tarafsız aktör (denetçi/bakanlık) da onaylayabilir. Beneficiary (seller) hariç.
    _enforce_actor_role(actor, {"recycler", "auditor", "ministry"})
    b = db.get(Batch, tx.batch_id)
    if not b:
        raise HTTPException(404, "Parti bulunamadı")
    with atomic(db):
        TS.update_reputation(db, b, success=True)
        b.status = "sold"
        TS.transition(db, tx, TxState.COMPLETED, "COMPLETED",
                      {"price": tx.agreed_price, "qty_kg": tx.agreed_qty_kg}, commit=False)
    db.refresh(tx)
    return TransactionOut.model_validate(tx, from_attributes=True)


@router.post("/{code}/dispute", response_model=TransactionOut, summary="Uyuşmazlık aç")
def dispute(code: str, payload: DisputeIn, db: Session = Depends(get_db),
            actor: str = Depends(require_actor)):
    tx = _get(db, code)
    _require(tx, TxState.SUSPENDED, TxState.VERIFIED)
    # Alıcı her iki durumdan da uyuşmazlık açar (teslimi o doğrular). Satıcı ise YALNIZ
    # otomatik askıya alınmış (SUSPENDED) emanette tarafsız çözüme başvurabilir — aksi
    # halde alıcı pasif kalırsa emanet süresiz kilitlenir, satıcı malı sevk etmiş olur.
    # Bu, "güvenilir ticari ray"ın iki taraflı adalet güvencesidir (denetim bulgusu).
    trole = _ROLE_TRADE.get(actor)
    if actor != "anon":
        if trole == "buyer":
            pass
        elif trole == "seller" and tx.status == TxState.SUSPENDED:
            pass
        else:
            raise HTTPException(403, f"'{actor}' rolü bu durumda uyuşmazlık açamaz")
    by = "seller" if trole == "seller" else "buyer"
    with atomic(db):
        TS.transition(db, tx, TxState.DISPUTED, "SUSPENDED",
                      {"dispute": payload.reason, "by": by}, actor=by, commit=False)
    db.refresh(tx)
    return TransactionOut.model_validate(tx, from_attributes=True)


@router.post("/{code}/resolve", response_model=TransactionOut,
             summary="Uyuşmazlığı çöz (release=teslim geçerli / refund=iade)")
def resolve(code: str, payload: ResolveIn, db: Session = Depends(get_db),
            actor: str = Depends(require_actor)):
    tx = _get(db, code)
    _require(tx, TxState.DISPUTED)
    # Uyuşmazlığı YALNIZ tarafsız bir aktör çözer (denetçi/bakanlık). Ne satıcı ne
    # alıcı kendi lehine karar veremez — "güvenilir ticari ray"ın temel güvencesi
    # (denetim bulgusu 1.2: taraf kendi emanetini serbest bırakıp iade ettiremez).
    _enforce_actor_role(actor, {"auditor", "ministry"})
    b = db.get(Batch, tx.batch_id)
    if not b:
        raise HTTPException(404, "Parti bulunamadı")
    with atomic(db):
        if payload.outcome == "release":
            TS.update_reputation(db, b, success=True)
            b.status = "sold"
            TS.transition(db, tx, TxState.COMPLETED, "COMPLETED",
                          {"resolution": "release", "note": payload.note}, commit=False)
        else:
            TS.update_reputation(db, b, success=False)
            b.status = "listed"
            TS.transition(db, tx, TxState.CANCELLED, "CANCELLED",
                          {"resolution": "refund", "note": payload.note}, commit=False)
    db.refresh(tx)
    return TransactionOut.model_validate(tx, from_attributes=True)
