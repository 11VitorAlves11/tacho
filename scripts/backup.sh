#!/bin/sh
set -eu

backup_root=${BACKUP_ROOT:-./backups}
timestamp=$(date -u +%Y-%m-%dT%H%M%SZ)
destination=$backup_root/$timestamp

mkdir -p "$destination"
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-tacho}" -d "${POSTGRES_DB:-tacho}" \
  | gzip > "$destination/database.sql.gz"
docker compose exec -T web tar -C /app/images -czf - . > "$destination/images.tar.gz"
docker compose run --rm --no-deps -T \
  -v "$destination:/backup" secrets-init \
  tar -C /secrets -czf /backup/secrets.tar.gz .

test -s "$destination/database.sql.gz"
test -s "$destination/images.tar.gz"
test -s "$destination/secrets.tar.gz"
printf 'Backup created at %s\n' "$destination"

