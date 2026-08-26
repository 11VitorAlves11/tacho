# Configuration

Copy `.env.example` to `.env`. Empty optional values disable their feature.

| Variable | Purpose | Default |
|---|---|---|
| `TACHO_VERSION` | Image tag to run | `latest` |
| `TACHO_PORT` | Published web port | `8000` |
| `POSTGRES_USER` / `POSTGRES_DB` | Database identity | `tacho` |
| `AUTH_COOKIE_SECURE` | Send session cookie only over HTTPS | `false` |
| `CORS_ORIGINS` | JSON list of browser origins | localhost |
| `PUBLIC_BASE_URL` | Canonical private application URL | request URL |
| `SHARE_BASE_URL` | Canonical public share URL | public base URL |
| `GEMINI_API_KEY` | Optional AI extraction | disabled |
| `TRUST_FORWARD_AUTH` | Enable trusted proxy login | `false` |
| `FORWARD_AUTH_SECRET` | Shared proxy/backend secret | empty |
| `FORWARD_AUTH_EMAIL_HEADER` | Header containing the verified identity email | `X-Forwarded-Email` |

## Secrets

The generic Compose generates the database password and `AUTH_SECRET` inside
`tacho_secrets`. They are not stored in `.env` or printed during normal startup.

Forward-auth is different: its secret must be shared with an external trusted proxy.
Generate it with `openssl rand -hex 32`, store it in `.env` with restrictive
permissions, and ensure the proxy removes client-provided identity/secret
headers before injecting trusted values.

## Volumes and bind mounts

Named volumes are the portable default. Operators who require bind mounts
should keep their paths in a private Compose override. A sanitized example is
provided as `docker-compose.override.example.yml`; do not commit the effective
override or host-specific paths to this repository.
