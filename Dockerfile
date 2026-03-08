# ── Stage 1: Build frontend ──────────────────────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python backend ───────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

COPY backend/ backend/
COPY alembic/ alembic/
COPY alembic.ini .

COPY --from=frontend-builder /app/frontend/dist/ frontend/dist/

CMD alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
