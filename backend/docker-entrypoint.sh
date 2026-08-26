#!/bin/sh
set -e

if [ -n "${TACHO_SECRETS_DIR:-}" ]; then
    POSTGRES_PASSWORD="$(cat "$TACHO_SECRETS_DIR/postgres_password")"
    AUTH_SECRET="$(cat "$TACHO_SECRETS_DIR/auth_secret")"
    export POSTGRES_PASSWORD AUTH_SECRET
    export DATABASE_URL="postgresql+psycopg2://${POSTGRES_USER:-tacho}:${POSTGRES_PASSWORD}@${POSTGRES_HOST:-db}:5432/${POSTGRES_DB:-tacho}"
fi

if [ "$#" -eq 0 ]; then
    set -- uvicorn app.main:app --host 0.0.0.0 --port 8000
fi

exec "$@"
