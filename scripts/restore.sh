#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  printf 'Usage: %s BACKUP_DIRECTORY\n' "$0" >&2
  exit 2
fi

source_dir=$1
for file in database.sql.gz images.tar.gz secrets.tar.gz; do
  test -s "$source_dir/$file" || {
    printf 'Missing backup file: %s/%s\n' "$source_dir" "$file" >&2
    exit 1
  }
done

printf 'This replaces the current Tacho database, images and secrets. Type RESTORE to continue: '
read -r confirmation
test "$confirmation" = RESTORE || exit 1

docker compose down
docker compose run --rm --no-deps -T \
  -v "$source_dir:/backup:ro" secrets-init \
  sh -ec 'rm -f /secrets/* && tar -C /secrets -xzf /backup/secrets.tar.gz'
docker compose up -d db redis
docker compose exec -T db sh -ec 'until pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"; do sleep 1; done'
docker compose exec -T db dropdb -U "${POSTGRES_USER:-tacho}" --if-exists "${POSTGRES_DB:-tacho}"
docker compose exec -T db createdb -U "${POSTGRES_USER:-tacho}" "${POSTGRES_DB:-tacho}"
gzip -dc "$source_dir/database.sql.gz" \
  | docker compose exec -T db psql -U "${POSTGRES_USER:-tacho}" -d "${POSTGRES_DB:-tacho}"
docker compose run --rm --no-deps -T \
  -v "$source_dir:/backup:ro" web \
  sh -ec 'rm -rf /app/images/* && tar -C /app/images -xzf /backup/images.tar.gz'
docker compose up -d --wait

