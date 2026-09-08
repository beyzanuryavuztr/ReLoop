"""
Seed yükleyici — motor ekosistemini (Parti/Talep) DB'ye yazar.

dataset:
  'canonical' → ../seed.py (referans: 80 fabrika / 250 parti / 60 talep, seed=42)
  'semireal'  → seed_semireal.py (gerçek coğrafya, 120/400/90, seed=2026, ikinci koşu)

Her parti için:
  • DMP tutarsızlık uyarıları hesaplanır ve saklanır,
  • genesis olay (DMP_CREATED) hash zincirine yazılır.
Aktörler (fabrika + geri dönüşümcü) ada göre tekilleştirilir.
"""
from __future__ import annotations

from sqlalchemy import delete

from ._enginepath import ensure_engine_on_path

ensure_engine_on_path()  # ../seed.py için de gerekli

from . import engine_service as ES
from . import seed_semireal
from .chain import append_event
from .models import (AuditLog, Batch, Bid, Demand, DeliveryVerification,
                     Factory, Notification, PassportEvent, Role,
                     Transaction, User)

VALID_DATASETS = {"canonical", "semireal"}

# Demo kullanıcıları (rol + API anahtarı). Anahtarlar README'de; prod'da değiştir.
DEMO_USERS = [
    ("seller_demo", Role.SELLER, "demo-seller-key"),
    ("recycler_demo", Role.RECYCLER, "demo-recycler-key"),
    ("auditor_demo", Role.AUDITOR, "demo-auditor-key"),
    ("ministry_demo", Role.MINISTRY, "demo-ministry-key"),
]


def seed_users(db):
    """Rol tabanlı demo kullanıcılarını oluşturur (idempotent; reseed'de korunur).
    Prod'da RELOOP_SEED_DEMO_USERS=false ile kapatılır (bilinen anahtarlar sızmaz)."""
    from .config import settings
    if not settings.seed_demo_users:
        return
    for uname, role, key in DEMO_USERS:
        if not db.query(User).filter(User.username == uname).first():
            db.add(User(username=uname, role=role, api_key=key))


def _clear(db):
    # Notification da temizlenir; aksi halde reseed sonrası ESKİ dataset'in
    # alıcı/talep kodlarına referans veren bayat bildirimler kalır.
    for model in (PassportEvent, DeliveryVerification, Bid, Transaction,
                  Notification, Batch, Demand, Factory, AuditLog):
        db.execute(delete(model))
    db.commit()


def load(db, dataset: str = "canonical") -> dict:
    import seed as canonical_seed  # ../seed.py

    # Geçersiz dataset SESSİZCE canonical'a düşmemeli (istemci hatasını maskeler +
    # tüm DB'yi habersiz siler). Bilinmeyen değer → hata.
    if dataset not in VALID_DATASETS:
        raise ValueError(f"Geçersiz dataset '{dataset}'; beklenen: {sorted(VALID_DATASETS)}")

    if dataset == "semireal":
        partiler, talepler, itibarlar = seed_semireal.uret()
    else:
        partiler, talepler, itibarlar = canonical_seed.uret()

    _clear(db)

    # --- Üretici fabrikalar (parti sahibi) ---
    fab_by_name: dict[str, Factory] = {}
    for p in partiler:
        if p.fabrika not in fab_by_name:
            f = Factory(name=p.fabrika, role=Role.SELLER, city=p.sehir,
                        lat=p.lat, lon=p.lon, reputation=itibarlar.get(p.fabrika, p.itibar))
            db.add(f)
            fab_by_name[p.fabrika] = f
    db.flush()

    # --- Partiler (DMP) + tutarsızlık + genesis olay ---
    for p in partiler:
        f = fab_by_name[p.fabrika]
        b = Batch(
            code=p.id, factory_id=f.id, city=p.sehir, lat=p.lat, lon=p.lon,
            pamuk=p.pamuk, polyester=p.polyester, elastan=p.elastan, kumas=p.kumas,
            gramaj=p.gramaj, en_m=p.en_m, miktar_kg=p.miktar_kg, kalite=p.kalite,
            min_fiyat=p.min_fiyat, depo_gun=p.depo_gun, dogrulanmis=p.dogrulanmis,
            reputation=p.itibar, waste_code="04 02 22", status="listed",
        )
        db.add(b)
        db.flush()
        uyari = ES.inconsistencies_for(b)
        b.inconsistencies = uyari or None
        append_event(db, b, "DMP_CREATED", {
            "code": b.code, "kumas": b.kumas, "miktar_kg": b.miktar_kg,
            "kalite": b.kalite, "pamuk": b.pamuk, "polyester": b.polyester,
            "elastan": b.elastan, "gramaj": b.gramaj, "sehir": b.city,
            "dogrulanmis": b.dogrulanmis, "waste_code": b.waste_code,
            "inconsistencies": uyari,
        }, commit=False)

    # --- Alıcı talepleri + geri dönüşümcü aktörler ---
    for t in talepler:
        if t.alici not in fab_by_name:
            f = Factory(name=t.alici, role=Role.RECYCLER, city=t.sehir,
                        lat=t.lat, lon=t.lon, reputation=0.9)
            db.add(f)
            fab_by_name[t.alici] = f
        db.add(Demand(
            code=t.id, buyer=t.alici, city=t.sehir, lat=t.lat, lon=t.lon,
            min_pamuk=t.min_pamuk, max_elastan=t.max_elastan, ihtiyac_kg=t.ihtiyac_kg,
            max_fiyat=t.max_fiyat, min_kalite=t.min_kalite,
            dogrulanmis_ister=t.dogrulanmis_ister,
        ))

    seed_users(db)   # rol tabanlı API anahtarları (auth)
    db.add(AuditLog(actor="system", action="seed", entity="dataset", entity_id=dataset,
                    detail=f"{len(partiler)} parti, {len(talepler)} talep yüklendi"))
    db.commit()

    return {
        "dataset": dataset,
        "factories": db.query(Factory).count(),
        "batches": db.query(Batch).count(),
        "demands": db.query(Demand).count(),
    }
