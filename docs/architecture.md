# Architecture

The browser talks to one FastAPI origin. In production that process also serves
the compiled React application. PostgreSQL stores durable domain data; recipe
images live on a separate persistent volume. Redis transports Celery import
tasks and is not the source of truth.

All household data belongs to a workspace. Authentication uses an HTTP-only
cookie. Private images are authorized through the API; temporary public shares
receive a token-scoped image endpoint.

Uploaded photos are decoded with Pillow before being stored, so files whose
bytes do not match their declared type are rejected. The original is kept
unchanged in the `tacho_images` volume as `receitas/<recipe>/<uuid>.<ext>`;
next to it the backend writes two derived WebP variants without EXIF metadata,
`<uuid>.thumb.webp` (up to 480 px wide) and `<uuid>.medium.webp` (up to
1200 px wide). Clients request them with `?size=thumb|medium`. Variants are
always regenerable: a missing one is created on its first request. Because file
names are unique and never rewritten, `/media` responses are sent with
`Cache-Control: private, max-age=31536000, immutable`; public share images are
cached for one hour, well within the five-hour share lifetime.

The production image is shared by three Compose services:

- `migrate`: applies Alembic migrations and exits;
- `web`: starts FastAPI/Uvicorn after migrations succeed;
- `worker`: starts Celery from exactly the same source revision.

This keeps web, worker and migrations synchronized while avoiding multiple
release artifacts.

