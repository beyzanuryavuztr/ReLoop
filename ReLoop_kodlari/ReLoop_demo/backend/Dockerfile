# Build context = ReLoop_demo/ (üst klasör), böylece motor çekirdeği (reloop.py,
# seed.py) da imaja girer. Bkz. docker-compose.yml -> build.context: ..
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RELOOP_ENGINE_DIR=/srv
WORKDIR /srv

RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg62-turbo libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

# Prod = Postgres → yalın liste + psycopg sürücüsü (requirements-postgres.txt).
COPY backend/requirements.txt backend/requirements-postgres.txt ./
RUN pip install --no-cache-dir -r requirements-postgres.txt

# Motor çekirdeği (tek doğruluk kaynağı) — RELOOP_ENGINE_DIR=/srv ile bulunur.
COPY reloop.py seed.py /srv/
COPY backend/app /srv/app
COPY backend/alembic /srv/alembic
COPY backend/alembic.ini /srv/alembic.ini
# Görüntü Zekâsı: TF.js + MobileNet (yerel; CDN yok).
# NOT: Dockerfile satır-içi yorumu argüman sayar → yorum AYRI satırda olmalı.
COPY backend/vendor /srv/vendor

EXPOSE 8000
# Prod: migrasyonları uygula, sonra sunucu.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
