# Development

## Docker development environment

```bash
cp .env.example .env
docker compose -f docker-compose.dev.yml up --build
```

This runs Vite with hot reload, FastAPI with reload, PostgreSQL, Redis and a
Celery worker.

## Backend

Python 3.12 and uv are required.

```bash
cd backend
uv sync --frozen --all-groups
uv run alembic upgrade head
uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy app
uv run pytest
```

Create migrations with `uv run alembic revision --autogenerate -m "description"`.
Review generated operations and test both a new database and an upgrade from the
previous release.

## Frontend

```bash
cd frontend
npm ci
npm run lint
npm test
npm run build
```

Do not edit lockfiles by hand. Runtime behavior changes need focused tests, not
coverage-only assertions.

