# Tacho backend

FastAPI API and Celery worker for Tacho, with PostgreSQL through SQLAlchemy and
schema migrations through Alembic.

From this directory:

```bash
uv sync --frozen --all-groups
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
uv run pytest
uv run ruff check app tests
uv run mypy app
```

The application requires `DATABASE_URL` and `REDIS_URL`. Use the development
Compose from the repository root for a ready PostgreSQL and Redis environment.
See [`docs/development.md`](../docs/development.md).
