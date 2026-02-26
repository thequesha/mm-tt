#!/bin/bash
set -e

echo "[entrypoint] Running Alembic migrations..."
MAX_RETRIES=30
RETRY_DELAY=2
ATTEMPT=1

until alembic upgrade head; do
  if [ "$ATTEMPT" -ge "$MAX_RETRIES" ]; then
    echo "[entrypoint] Alembic failed after $ATTEMPT attempts. Exiting."
    exit 1
  fi

  echo "[entrypoint] Migration attempt $ATTEMPT failed. Waiting ${RETRY_DELAY}s for DB..."
  ATTEMPT=$((ATTEMPT + 1))
  sleep "$RETRY_DELAY"
done

echo "[entrypoint] Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
