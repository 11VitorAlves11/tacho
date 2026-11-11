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

Login attempts are rate-limited per client IP ([details](configuration.md#login-rate-limiting)).
Uvicorn only trusts `X-Forwarded-For`/`X-Forwarded-Proto` from addresses listed
in `FORWARDED_ALLOW_IPS` (default `127.0.0.1`). When the proxy reaches Tacho
from another host or container, set it to the proxy's address as seen by the
`web` container, for example:

```dotenv
FORWARDED_ALLOW_IPS=172.18.0.10
```

Without it, every visitor appears to come from the proxy and shares a single
per-IP attempt budget. Do not use `*` unless port 8000 is reachable only
through the proxy, since any client could then forge its address.

## Verify

```bash
docker compose ps
curl --fail http://localhost:8000/health
docker compose exec web alembic current
```

Before storing important recipes, create and restore a test backup by following
[backup and restore](backup-restore.md).

## Recovering access

Tacho sends no email, so there is no "forgot password" link. Anyone with shell
access to the host can reset a local account from the `web` container:

```bash
# List accounts: email, name, active, member of the household workspace
docker compose exec web python -m scripts.reset_password --list

# Set a new password (prompted twice, never echoed)
docker compose exec web python -m scripts.reset_password --email ana@example.com

# Non-interactive: read the password from the first line of stdin
printf '%s\n' "$NEW_PASSWORD" | docker compose exec -T web python -m scripts.reset_password --email ana@example.com --password-stdin

# Re-activate a deactivated account without changing its password
docker compose exec web python -m scripts.reset_password --email ana@example.com --activate
```

Passwords must have at least 8 characters, as in the initial setup. The command
exits with `0` on success, `1` when no account has that email, `2` for invalid
arguments or passwords and `130` when cancelled.

Resetting a password does not end sessions that are already signed in:
session cookies are self-contained tokens that stay valid until they expire
(30 days) or until the generated `auth_secret` in `tacho_secrets` is replaced,
which signs everybody out.

If an address is temporarily blocked after too many failed sign-ins, wait for
the window to expire (15 minutes by default) or clear the counters:

```bash
docker compose exec redis sh -c "redis-cli --scan --pattern 'tacho:ratelimit:*' | xargs -r redis-cli del"
```
