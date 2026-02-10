FROM python:3.11-slim

WORKDIR /app

COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

COPY backend/ backend/
COPY alembic/ alembic/
COPY alembic.ini .

CMD alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
