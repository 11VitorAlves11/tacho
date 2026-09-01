# Tacho

Tacho is a self-hosted recipe and kitchen manager for collecting recipes,
cooking step by step, planning meals and maintaining a shared shopping list.

> Tacho 2.1 is available for self-hosted installations. Keep verified backups
> and pin an exact image version on installations containing important data.

## Features

- Recipe CRUD, categories, tags, cookbooks, favourites and ratings.
- Import from a URL, with optional Gemini extraction from text or photos.
- Recipe photographs and galleries.
- Full-screen cooking mode with timers, portion scaling and offline cache.
- Pantry, weekly meal plan and generated shopping list.
- Temporary public recipe links and print-friendly views.
- Multiple members in one household, cookie authentication and optional
  forward-auth integration.
- Installable PWA, dark mode and responsive interface.

## Quick start

Requirements: Docker Engine with Docker Compose v2.

```bash
git clone https://github.com/11VitorAlves11/tacho.git
cd tacho
cp .env.example .env
docker compose up -d
```

Open <http://localhost:8000> and create the first account. The Compose stack
generates persistent database and session secrets during its first start.

For an internet-facing installation, configure HTTPS and set
`AUTH_COOKIE_SECURE=true`. See [installation](docs/installation.md) and
[configuration](docs/configuration.md) before exposing Tacho to a network you
do not trust.

## Data and upgrades

Recipes and accounts are stored in the `tacho_pgdata` volume. Uploaded images
are stored in `tacho_images`; generated secrets are stored in `tacho_secrets`.
All three belong to the installation and must be preserved.

```bash
./scripts/backup.sh
docker compose pull
docker compose up -d --wait
```

Read [upgrading](docs/upgrading.md) before changing versions and
[backup and restore](docs/backup-restore.md) before relying on an installation.

## Architecture

The repository is a deliberately small monorepo:

- `backend/`: FastAPI, SQLAlchemy, Alembic and Celery.
- `frontend/`: React, TypeScript, Vite and Tailwind CSS.
- PostgreSQL: durable application data.
- Redis: Celery broker and transient task results.
- one Tacho image: web process, worker and migrations use different commands
  from the same release artifact.

More detail is available in [architecture](docs/architecture.md).

## Development

```bash
cp .env.example .env
docker compose -f docker-compose.dev.yml up --build
```

The frontend runs at <http://localhost:5173> and the API documentation at
<http://localhost:8000/docs>. See [development](docs/development.md) for local
tooling, tests and migration commands.

## Documentation

- [Installation](docs/installation.md)
- [Configuration](docs/configuration.md)
- [Upgrading and rollback](docs/upgrading.md)
- [Backup and restore](docs/backup-restore.md)
- [Development](docs/development.md)
- [Architecture](docs/architecture.md)
- [Release process](docs/releasing.md)
- [Migration from `tacho_app`](docs/migration-from-tacho-app.md)

## Contributing and support

Contributions are welcome; read [CONTRIBUTING.md](CONTRIBUTING.md). Only the
latest stable release is supported. Security reports follow
[SECURITY.md](SECURITY.md); general support is best-effort through GitHub
Issues.

## License

Tacho is licensed under the [GNU Affero General Public License v3.0](LICENSE).
