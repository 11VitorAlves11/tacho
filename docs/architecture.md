# Architecture

The browser talks to one FastAPI origin. In production that process also serves
the compiled React application. PostgreSQL stores durable domain data; recipe
images live on a separate persistent volume. Redis transports Celery import
tasks and is not the source of truth.

All household data belongs to a workspace. Authentication uses an HTTP-only
cookie. Private images are authorized through the API; temporary public shares
receive a token-scoped image endpoint.

The production image is shared by three Compose services:

- `migrate`: applies Alembic migrations and exits;
- `web`: starts FastAPI/Uvicorn after migrations succeed;
- `worker`: starts Celery from exactly the same source revision.

This keeps web, worker and migrations synchronized while avoiding multiple
release artifacts.

