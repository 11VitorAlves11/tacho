# Upgrading and rollback

## Before every upgrade

1. Read the target release notes.
2. Confirm available disk space.
3. Create a backup and verify that it contains both database and images.
4. Record the current image version: `docker compose images`.

## Upgrade

Pinning versions makes rollback explicit:

```dotenv
TACHO_VERSION=2.0.0
```

Then run:

```bash
./scripts/backup.sh
docker compose pull
docker compose up -d --wait
docker compose exec web alembic current
```

The `migrate` service applies each Alembic migration once before web and worker
start. Never start a newer application against a database whose migration job
failed.

## Rollback

If no database migration ran, set `TACHO_VERSION` back to the previous version
and run `docker compose up -d --wait`.

If a migration ran, do not assume the old application supports the new schema
and do not use `alembic downgrade` on valuable data. Stop the stack, restore the
pre-upgrade backup, set the previous version and start again.

