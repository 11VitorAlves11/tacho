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

### Backend tests

The suite mixes unit tests with API/database integration tests
(`backend/tests/test_api_*.py`). The integration tests drive the FastAPI app
through `TestClient` against a real PostgreSQL database: at session start
`tests/conftest.py` runs `alembic upgrade head` (which also validates the
migration chain on an empty database), and **every table is truncated before
each test**. Point `DATABASE_URL` at a disposable database only — as a guard,
the suite refuses to run unless the database name contains `test`.

Start a throwaway PostgreSQL on a free local port and run the suite:

```bash
docker run -d --rm --name tacho-test-db -e POSTGRES_USER=tacho -e POSTGRES_PASSWORD=tacho \
  -e POSTGRES_DB=tacho_test -p 127.0.0.1:55432:5432 postgres:16-alpine

cd backend
export DATABASE_URL=postgresql+psycopg2://tacho:tacho@127.0.0.1:55432/tacho_test
export REDIS_URL=redis://127.0.0.1:6379/0   # required by settings; no Redis server is needed
export AUTH_SECRET=test-secret-with-at-least-thirty-two-characters
uv run pytest

docker stop tacho-test-db
```

CI provides the same variables and a PostgreSQL service in
`.github/workflows/ci.yml`. Image uploads are written to a per-test temporary
directory, never to `backend/images/`. Tests that need a second, isolated
workspace use the `other_client` fixture, which creates that workspace and its
user directly in the database (there is no API for it).

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

