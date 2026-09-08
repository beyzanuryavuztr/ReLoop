"""
SQLAlchemy motoru + oturum (DB-agnostik).

SQLite ise foreign_keys pragmasını açar ve tek-thread kısıtını gevşetir;
PostgreSQL ise standart havuz kullanılır. Uygulama kodu iki DB'de de aynıdır.
"""
from __future__ import annotations
from contextlib import contextmanager

from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=not _is_sqlite,
    future=True,
)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _fk_pragma(dbapi_con, _rec):  # noqa: ANN001
        cur = dbapi_con.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI bağımlılığı: istek başına oturum."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def atomic(db):
    """
    Mutasyon + commit'i tek transaction'da sarar ve eşzamanlılık çakışmalarını temiz
    409'a çevirir. Çakışma (aynı batch'e seq / aynı kod) YALNIZ son commit'te değil,
    daha erken `db.flush()` sırasında da patlayabilir: SQLite'ta "database is locked"
    (OperationalError), Postgres'te unique-violation (IntegrityError). İkisi de burada
    yakalanır → ham 500 yerine 409. Diğer hatalarda (ör. HTTPException doğrulaması)
    bekleyen mutasyonlar geri alınır ve hata olduğu gibi yükselir.
    """
    try:
        yield db
        db.commit()
    except (IntegrityError, OperationalError):
        db.rollback()
        raise HTTPException(409, "Eşzamanlı çakışma; lütfen tekrar deneyin")
    except Exception:
        db.rollback()
        raise
