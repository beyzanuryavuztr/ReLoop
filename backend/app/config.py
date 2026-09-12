"""
Yapılandırma — DB-agnostik.

Varsayılan: SQLite (sıfır kurulum, yerel geliştirme + sandbox).
Prod: DATABASE_URL ile PostgreSQL (docker-compose).
  ör. postgresql+psycopg://reloop:reloop@db:5432/reloop
"""
from __future__ import annotations
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE = Path(__file__).resolve().parent.parent  # .../backend


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RELOOP_", env_file=".env", extra="ignore")

    # SQLite varsayılan; Postgres için RELOOP_DATABASE_URL ver.
    database_url: str = f"sqlite:///{(_BASE / 'reloop.db').as_posix()}"

    app_name: str = "ReLoop API"
    # Arayüzün (tek dosya HTML / yerel dosya) API'ye erişebilmesi için gevşek CORS.
    cors_origins: list[str] = ["*"]

    # Deterministik ekosistem: referans veri seti bu tohumla üretilir (tekrarlanabilir).
    seed_value: int = 42

    # Yönetici anahtarı: yıkıcı /admin/* uçları (ör. /admin/seed) için X-Admin-Key
    # zorunludur. VARSAYILAN BOŞ → auth.py FAIL-CLOSED davranır: /admin/* açılmaz,
    # 503 döner (bilinen bir anahtar prod'a sızmaz — denetim bulgusu 2.2). Kullanmak
    # için RELOOP_ADMIN_KEY ortam değişkenini açıkça ayarla.
    admin_key: str = ""

    # Rol tabanlı demo kullanıcıları (seed'de) oluşturulsun mu? Demo/pilot için AÇIK
    # (arayüzün canlı POST'ları demo anahtarıyla çalışsın). Gerçek prod dağıtımında
    # RELOOP_SEED_DEMO_USERS=false ver → README'deki bilinen anahtarlar üretilmez
    # (denetim bulgusu 2.3). Gerçek kullanıcılar dağıtım sırasında ayrıca oluşturulur.
    seed_demo_users: bool = True

    # Durum-değiştiren uçlar (ticari zincir, DMP oluşturma, forecast) geçerli bir
    # X-API-Key ister; rol doğrulanmış kullanıcıdan türetilir (self-declared değil).
    # Güvenli varsayılan: AÇIK. Arayüz canlı POST'larında demo anahtarı gönderir;
    # ticari zincir arayüzde çevrimdışı simüle edilir (backend'i çağırmaz).
    require_auth: bool = True


settings = Settings()
