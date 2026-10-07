#!/bin/sh
set -e
alembic upgrade head
if [ "$#" -gt 0 ]; then
    exec "$@"
fi
exec uvicorn chiron.api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
