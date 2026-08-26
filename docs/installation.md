# Installation

## Requirements

- Docker Engine 24 or newer.
- Docker Compose v2.20 or newer.
- Approximately 1 GB of available memory for the default stack.
- Persistent disk space for PostgreSQL and recipe images.

## Install

```bash
git clone https://github.com/11VitorAlves11/tacho.git
cd tacho
cp .env.example .env
docker compose up -d --wait
```

Open `http://HOST:8000`, complete the first-account screen and keep that account
secure. Registration is not public after initial setup; an authenticated member
can add further household members.

The first start creates random PostgreSQL and authentication secrets in a
named volume. Do not delete `tacho_secrets` while keeping the database: doing so
would generate a different database password and invalidate sessions.

## Reverse proxy and HTTPS

Tacho does not require a particular reverse proxy or identity provider. Proxy
HTTP traffic to port 8000, preserve the original host/protocol headers, and
enable WebSocket support if your proxy disables it by default.

Set the following in `.env`:

```dotenv
PUBLIC_BASE_URL=https://recipes.example.com
SHARE_BASE_URL=https://recipes.example.com
AUTH_COOKIE_SECURE=true
CORS_ORIGINS=["https://recipes.example.com"]
```

Terminate TLS at the proxy. Do not publish the PostgreSQL or Redis ports.

## Verify

```bash
docker compose ps
curl --fail http://localhost:8000/health
docker compose exec web alembic current
```

Before storing important recipes, create and restore a test backup by following
[backup and restore](backup-restore.md).

