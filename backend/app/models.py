"""
ORM şeması — ReLoop güvenilir ticari ray.

Temel varlıklar:
  Factory  : fabrika/alıcı aktör (satıcı=fire üreten, recycler=geri dönüşümcü)
  Batch    : fire partisi = Dijital Malzeme Pasaportu (DMP)
  Demand   : alıcı talebi
               (Eşleşmeler kalıcı tabloda tutulmaz; talep başına anlık hesaplanır.)
  Transaction + Bid : kör teklif → pazarlık → emanet → teslim ticari zinciri
  DeliveryVerification : teslimde beyan↔gözlem karşılaştırması (Dalga 2)
  PassportEvent : DMP olaylarının SHA-256 hash zinciri (değişmezlik, Dalga 2)
  AuditLog : denetim izi   ·   User : rol tabanlı erişim (satıcı/alıcı/denetçi/bakanlık)

Tüm zamanlar UTC saklanır. JSON alanları SQLite ve PostgreSQL'de taşınabilir.
"""
from __future__ import annotations
from datetime import datetime, timezone

from sqlalchemy import (Boolean, DateTime, Float, ForeignKey, Integer, JSON,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- Sabitler (durum makineleri + roller) ----------------------------------
class Role:
    SELLER = "seller"        # fire üreten tekstil fabrikası
    RECYCLER = "recycler"    # geri dönüşümcü / alıcı
    AUDITOR = "auditor"      # denetçi (denetim modu)
    MINISTRY = "ministry"    # bakanlık / OSB (kamu dashboard, açık veri)
    ALL = {SELLER, RECYCLER, AUDITOR, MINISTRY}


class TxState:
    OPEN = "OPEN"                 # talep-parti eşleşti, teklif bekliyor
    BID = "BID_PLACED"            # kör teklif verildi
    COUNTERED = "COUNTERED"       # karşı teklif
    ACCEPTED = "ACCEPTED"         # fiyat/miktar mutabakatı
    ESCROW = "ESCROW"             # emanet açıldı (bedel kilitli)
    SHIPPED = "SHIPPED"           # satıcı sevkiyatı yaptı
    DELIVERED = "DELIVERED"       # fiziksel teslim yapıldı, doğrulama bekliyor
    VERIFIED = "VERIFIED"         # teslim beyanla uyumlu
    COMPLETED = "COMPLETED"       # emanet çözüldü, işlem kapandı
    DISPUTED = "DISPUTED"         # uyuşmazlık açıldı
    SUSPENDED = "SUSPENDED"       # tutarsızlık → emanet askıya alındı
    CANCELLED = "CANCELLED"


class EventType:
    CREATED = "DMP_CREATED"
    UPDATED = "DMP_UPDATED"
    LISTED = "LISTED"
    MATCHED = "MATCHED"
    BID = "BID"
    ESCROW = "ESCROW_OPENED"
    DELIVERED = "DELIVERED"
    VERIFIED = "VERIFIED"
    SUSPENDED = "SUSPENDED"
    COMPLETED = "COMPLETED"


# --- Aktörler ---------------------------------------------------------------
class Factory(Base):
    __tablename__ = "factory"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    role: Mapped[str] = mapped_column(String(20), default=Role.SELLER)
    city: Mapped[str] = mapped_column(String(60))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    reputation: Mapped[float] = mapped_column(Float, default=0.85)  # geçmiş teslim başarı oranı 0–1
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    batches: Mapped[list["Batch"]] = relationship(back_populates="factory")


# --- DMP (fire partisi) -----------------------------------------------------
class Batch(Base):
    __tablename__ = "batch"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # P0001
    factory_id: Mapped[int] = mapped_column(ForeignKey("factory.id"))
    city: Mapped[str] = mapped_column(String(60))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)

    # Lif kompozisyonu (%)
    pamuk: Mapped[float] = mapped_column(Float)
    polyester: Mapped[float] = mapped_column(Float)
    elastan: Mapped[float] = mapped_column(Float)

    kumas: Mapped[str] = mapped_column(String(30))
    gramaj: Mapped[int] = mapped_column(Integer)      # g/m²
    en_m: Mapped[float] = mapped_column(Float)        # kumaş eni (m)
    miktar_kg: Mapped[float] = mapped_column(Float)
    kalite: Mapped[str] = mapped_column(String(2))    # A/B/C
    min_fiyat: Mapped[float] = mapped_column(Float)   # TL/kg (yalnız sisteme görünür, kör teklif)
    depo_gun: Mapped[int] = mapped_column(Integer, default=0)
    dogrulanmis: Mapped[bool] = mapped_column(Boolean, default=False)  # NIR/lab doğrulanmış mı
    reputation: Mapped[float] = mapped_column(Float, default=0.85)

    waste_code: Mapped[str] = mapped_column(String(12), default="04 02 22")  # tekstil fire (EWC/Atık Yön.)
    status: Mapped[str] = mapped_column(String(20), default="listed")
    inconsistencies: Mapped[dict | None] = mapped_column(JSON, default=None)  # tutarsızlık uyarıları
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    factory: Mapped["Factory"] = relationship(back_populates="batches")
    events: Mapped[list["PassportEvent"]] = relationship(
        back_populates="batch", order_by="PassportEvent.seq")


# --- Talep ------------------------------------------------------------------
class Demand(Base):
    __tablename__ = "demand"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # T001
    buyer: Mapped[str] = mapped_column(String(120))
    city: Mapped[str] = mapped_column(String(60))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    min_pamuk: Mapped[float] = mapped_column(Float)
    max_elastan: Mapped[float] = mapped_column(Float, default=0.0)
    ihtiyac_kg: Mapped[float] = mapped_column(Float)
    max_fiyat: Mapped[float] = mapped_column(Float)
    min_kalite: Mapped[str] = mapped_column(String(2), default="C")
    dogrulanmis_ister: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# Not: Eşleşmeler kalıcı tabloda tutulmaz — motor (reloop.py) tarafından istek anında
# hesaplanır (tek doğruluk kaynağı). Böylece bayat/çelişkili eşleşme kaydı oluşmaz.


# --- Ticari zincir: işlem + teklifler ---------------------------------------
class Transaction(Base):
    __tablename__ = "transaction"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(24), unique=True, index=True)  # TX-0001
    batch_id: Mapped[int] = mapped_column(ForeignKey("batch.id"))
    demand_id: Mapped[int] = mapped_column(ForeignKey("demand.id"))
    status: Mapped[str] = mapped_column(String(20), default=TxState.OPEN)
    agreed_price: Mapped[float | None] = mapped_column(Float, default=None)
    agreed_qty_kg: Mapped[float | None] = mapped_column(Float, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    bids: Mapped[list["Bid"]] = relationship(back_populates="transaction",
                                             order_by="Bid.created_at")


class Bid(Base):
    __tablename__ = "bid"
    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transaction.id"))
    by_role: Mapped[str] = mapped_column(String(20))   # buyer/seller
    kind: Mapped[str] = mapped_column(String(12))      # bid/counter/accept/reject
    amount: Mapped[float] = mapped_column(Float)       # TL/kg
    qty_kg: Mapped[float] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(String(200), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    transaction: Mapped["Transaction"] = relationship(back_populates="bids")


# --- Teslim doğrulama (Dalga 2) --------------------------------------------
class DeliveryVerification(Base):
    __tablename__ = "delivery_verification"
    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transaction.id"))
    declared: Mapped[dict] = mapped_column(JSON)       # DMP beyanı anlık görüntüsü
    observed: Mapped[dict] = mapped_column(JSON)       # teslimde gözlenen değerler
    mismatch: Mapped[bool] = mapped_column(Boolean, default=False)
    mismatch_fields: Mapped[dict | None] = mapped_column(JSON, default=None)
    photo_ref: Mapped[str | None] = mapped_column(String(255), default=None)
    decision: Mapped[str | None] = mapped_column(String(20), default=None)  # verified/suspended
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# --- Pasaport hash zinciri (Dalga 2) ---------------------------------------
class PassportEvent(Base):
    __tablename__ = "passport_event"
    __table_args__ = (UniqueConstraint("batch_id", "seq", name="uq_event_seq"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batch.id"))
    seq: Mapped[int] = mapped_column(Integer)          # 0'dan artan zincir sırası
    event_type: Mapped[str] = mapped_column(String(24))
    payload: Mapped[dict] = mapped_column(JSON)
    prev_hash: Mapped[str] = mapped_column(String(64), default="0" * 64)
    hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    batch: Mapped["Batch"] = relationship(back_populates="events")


# --- Denetim izi ------------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(60), default="system")
    action: Mapped[str] = mapped_column(String(60))
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(40))
    detail: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# --- Proaktif bildirim (Dalga 3) --------------------------------------------
class Notification(Base):
    __tablename__ = "notification"
    id: Mapped[int] = mapped_column(primary_key=True)
    recipient: Mapped[str] = mapped_column(String(120), index=True)  # alıcı adı/rol
    kind: Mapped[str] = mapped_column(String(24), default="prematch")
    demand_code: Mapped[str | None] = mapped_column(String(20), default=None)
    batch_ref: Mapped[str | None] = mapped_column(String(30), default=None)  # ör. FORECAST
    message: Mapped[str] = mapped_column(Text)
    score: Mapped[float | None] = mapped_column(Float, default=None)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# --- Kullanıcı / rol (RBAC) -------------------------------------------------
class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(20), default=Role.SELLER)
    api_key: Mapped[str] = mapped_column(String(64), index=True)
    factory_id: Mapped[int | None] = mapped_column(ForeignKey("factory.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
