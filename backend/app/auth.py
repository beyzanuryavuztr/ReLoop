"""
Erişim kontrolü — GERÇEK API-anahtarı doğrulaması (self-declared başlık DEĞİL).

- Yönetici: X-Admin-Key ↔ RELOOP_ADMIN_KEY (sabit-zaman).
- Aktör: X-API-Key ↔ User tablosundaki api_key. Rol, doğrulanmış kullanıcıdan
  TÜRETİLİR (istemcinin iddiasından değil). RELOOP_REQUIRE_AUTH açıksa durum-değiştiren
  uçlar geçerli bir anahtar ister; kapalıysa (demo) anahtar opsiyoneldir ("anon").

Demo kullanıcıları seed'de oluşturulur (seed_loader.seed_users); anahtarlar README'de.
"""
from __future__ import annotations
import hmac

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User

VALID_ROLES = {"seller", "recycler", "auditor", "ministry"}


def require_admin(x_admin_key: str = Header(default="")) -> bool:
    # Fail-closed: anahtar yapılandırılmamışsa yıkıcı /admin/* uçlarını AÇMA (503).
    if not settings.admin_key:
        raise HTTPException(503, "Yönetici anahtarı yapılandırılmamış (RELOOP_ADMIN_KEY)")
    if not hmac.compare_digest(x_admin_key, settings.admin_key):
        raise HTTPException(401, "Yönetici anahtarı gerekli (X-Admin-Key başlığı)")
    return True


def require_actor(x_api_key: str = Header(default=""), db: Session = Depends(get_db)) -> str:
    """
    X-API-Key'i User tablosunda doğrular; rolü kullanıcıdan türetir.
    Dönen: doğrulanmış rol ('seller'/'recycler'/...) veya 'anon' (demo, anahtarsız).
    RELOOP_REQUIRE_AUTH açıkken geçerli anahtar zorunlu → aksi halde 401.
    """
    user = None
    if x_api_key:
        user = db.query(User).filter(User.api_key == x_api_key).first()
        if not user:
            raise HTTPException(401, "Geçersiz API anahtarı (X-API-Key)")
    if settings.require_auth and user is None:
        raise HTTPException(401, "Geçerli X-API-Key gerekli (durum-değiştiren uç)")
    return user.role if user else "anon"
