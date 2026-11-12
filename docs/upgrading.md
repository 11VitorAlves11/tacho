# Upgrading and rollback

## Before every upgrade

1. Read the target release notes.
2. Confirm available disk space.
3. Create a backup and verify that it contains both database and images.
4. Record the current image version: `docker compose images`.

## Upgrade

Pinning versions makes rollback explicit:

```dotenv
TACHO_VERSION=2.2.1
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

## Pre-generating image variants

Photos uploaded before image variants existed get their thumbnail and medium
WebP variants the first time they are displayed.
To create them all up front instead (optional, idempotent, prints a summary):

```bash
docker compose exec web ./docker-entrypoint.sh python -m scripts.generate_image_variants
```

The command goes through the entrypoint so the production secrets are loaded
into the environment. With the development stack, use
`docker compose -f docker-compose.dev.yml exec backend python -m scripts.generate_image_variants`.
Variants are derived files; deleting them is harmless.

## Release-specific notes

### 2.2.0

- Adds one migration (`876b063c0d21`, table `shopping_list_item_sources`) that
  links shopping list items to the recipes they came from. It only creates a
  new table; existing items keep working and simply show no source recipes.
  Rolling back follows the rule above: restore the pre-upgrade backup rather
  than downgrading.

## Rollback

If no database migration ran, set `TACHO_VERSION` back to the previous version
and run `docker compose up -d --wait`.

If a migration ran, do not assume the old application supports the new schema
and do not use `alembic downgrade` on valuable data. Stop the stack, restore the
pre-upgrade backup, set the previous version and start again.

## Migration notes

- **`a436639380b8` — pantry price entries.** Adds the `pantry_price_entries`
  table (one row per recorded purchase of a pantry item, cascading when the item
  or workspace is deleted). Additive only: existing data is untouched and no
  configuration change is needed. Rolling back drops the table and every
  recorded price, so restore the pre-upgrade backup instead of downgrading if the
  prices matter.
