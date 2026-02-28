#!/bin/sh
# Runs inside the container before the main process.
# Executed as the non-root appuser; env vars are injected by docker-compose (env_file).
set -e

echo "[entrypoint] Applying database migrations..."
python manage.py migrate --noinput

echo "[entrypoint] Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "[entrypoint] Starting server..."
exec "$@"
