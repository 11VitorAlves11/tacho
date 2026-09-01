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
| `OIDC_ISSUER` | OpenID Provider issuer/discovery base URL | disabled |
| `OIDC_CLIENT_ID` / `OIDC_CLIENT_SECRET` | OAuth client credentials | empty |
| `OIDC_REDIRECT_URI` | Exact callback registered at the provider | empty |
| `OIDC_SCOPES` | Requested scopes | `openid email profile` |
| `OIDC_DISPLAY_NAME` | Provider name displayed in the login UI | `OpenID Connect` |
| `OIDC_ALLOW_PROVISIONING` | Create new workspace members after verified OIDC login | `false` |
| `OIDC_DISABLE_LOCAL_LOGIN` | Remove password login endpoint and form | `false` |

## Secrets

The generic Compose generates the database password and `AUTH_SECRET` inside
`tacho_secrets`. They are not stored in `.env` or printed during normal startup.

Forward-auth is different: its secret must be shared with an external trusted proxy.
Generate it with `openssl rand -hex 32`, store it in `.env` with restrictive
permissions, and ensure the proxy removes client-provided identity/secret
headers before injecting trusted values.

## OpenID Connect

OIDC uses the provider discovery document, Authorization Code Flow with PKCE,
and validates state, nonce, issuer, audience and the ID-token signature. Register
`OIDC_REDIRECT_URI` as an exact callback, normally
`https://tacho.example.com/auth/oidc/callback`.

Email coincidence never links accounts automatically. With provisioning off,
sign in locally and choose **Associar OpenID Connect** in the account menu. With
provisioning on, a new account is created only when the provider supplies an
email that is not already used locally. Keep local login enabled until at least
one working OIDC identity has been linked; disabling it prematurely can lock all
administrators out.

## Volumes and bind mounts

Named volumes are the portable default. Operators who require bind mounts
should keep their paths in a private Compose override. A sanitized example is
provided as `docker-compose.override.example.yml`; do not commit the effective
override or host-specific paths to this repository.
