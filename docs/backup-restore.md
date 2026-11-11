# Backup and restore

A complete backup contains PostgreSQL, uploaded images and the generated
secrets. `scripts/backup.sh` creates a timestamped directory under `backups/`.

```bash
./scripts/backup.sh
```

Copy backups away from the Docker host and protect them: the database contains
account information and the secrets archive can unlock it.

The images volume also holds the derived `*.thumb.webp` and `*.medium.webp`
variants next to each original photo. They are safe to back up and restore as
they are, and also safe to leave out: missing variants are regenerated on
demand, or all at once with the script described in
[Upgrading](upgrading.md#pre-generating-image-variants).

## Restore

Restoring replaces the current database and images. Stop normal application
traffic first and choose an explicit backup directory:

```bash
docker compose stop web worker
./scripts/restore.sh backups/2026-08-25T120000Z
docker compose up -d --wait
```

Test restore procedures on a disposable installation. A backup that has never
been restored is not yet a verified backup.

