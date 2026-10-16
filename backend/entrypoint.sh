#!/bin/sh
set -e

echo "[QueryPilot Backend] Running database migrations..."
alembic upgrade head || echo "[QueryPilot Backend] Alembic migration finished or already at head."

echo "[QueryPilot Backend] Launching FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
