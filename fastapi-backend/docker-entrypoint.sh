#!/bin/bash
set -e

echo "Starting ProctoAI Backend..."

# Wait for database to be ready
echo "Waiting for PostgreSQL to be ready..."
while ! nc -z postgres 5432; do
  sleep 1
done
echo "PostgreSQL is ready!"

# Run migrations
echo "Running database migrations..."
python -m alembic upgrade head

# Ensure MinIO bucket exists
echo "Ensuring MinIO bucket exists..."
python -c "from app.core.storage import ensure_bucket; ensure_bucket()" || echo "MinIO not available, skipping bucket creation"

echo "Starting Uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
