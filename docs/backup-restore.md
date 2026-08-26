# Backup and restore

A complete backup contains PostgreSQL, uploaded images and the generated
secrets. `scripts/backup.sh` creates a timestamped directory under `backups/`.

```bash
./scripts/backup.sh
```

Copy backups away from the Docker host and protect them: the database contains
account information and the secrets archive can unlock it.

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

