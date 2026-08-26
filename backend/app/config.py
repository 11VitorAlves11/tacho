from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str
    environment: str = "development"
    # Assina os cookies de sessão (JWT do fastapi-users) — tem de ser fixo
    # e secreto em produção (.env), nunca o valor por omissão; um valor
    # aleatório a cada arranque invalidava a sessão de todos ao reiniciar.
    auth_secret: str = "dev-secret-change-me-in-production"
    # Cookie "Secure" só é entregue pelo browser em HTTPS — falso por
    # omissão para o dev local (http://localhost) funcionar; produção
    # HTTPS deployments should set this to true in their environment.
    auth_cookie_secure: bool = False
    cors_origins: list[str] = ["http://localhost:5173"]
    # Caminho relativo ao WORKDIR do container (/app). Em dev resolve para
    # backend/images/ via bind mount; em docker-compose.yml há também um
    # volume Docker nomeado (tacho_images) montado no mesmo caminho, mais
    # específico que o bind mount — garante que as fotos sobrevivem a um
    # deploy sem o bind mount de desenvolvimento.
    images_dir: str = "images"
    max_image_bytes: int = 8 * 1024 * 1024
    # Só para o export schema.org (GET /recipes/{id}/export) construir URLs
    # absolutas corretas. Sem isto, cairia em request.base_url — que atrás
    # de um proxy reverso sem --proxy-headers configurado (ver Dockerfile)
    # dava esquema/host errados (ex. http:// interno em vez de https://
    # público). Em dev fica None e usa-se request.base_url, que já está
    # certo (sem proxy no meio).
    public_base_url: str | None = None
    # Host do link/QR de partilha pública (`POST /recipes/{id}/share`) —
    # deliberadamente separado de `public_base_url`: aquele é o host
    # private application URL used for schema.org images, while this is the
    # optional public host used for temporary recipe sharing.
    # Trocar um pelo outro seria errado nos dois sentidos. Sem valor, cai
    # em `public_base_url` (ex. dev local, onde ambos os casos usam o
    # mesmo host único).
    share_base_url: str | None = None
    # Login silencioso quando o pedido já chega autenticado pelo forward-auth
    # external forward-auth proxy — avoids asking for a second login to a
    # user already authenticated upstream.
    # Desligado por omissão: só liga em produção depois de configurar o NPM
    # para injetar o header de email + o segredo partilhado nesta rota.
    trust_forward_auth: bool = False
    forward_auth_email_header: str = "X-Forwarded-Email"
    # Só o NPM (não o Authentik) consegue injetar este valor — é o que
    # impede um pedido direto ao backend (contorna o NPM/Authentik, ex.
    # outro container na LAN) de forjar o header de email e entrar como
    # qualquer pessoa. Sem valor, `trust_forward_auth` fica inerte mesmo
    # que `True` (ver validação em `forward_login`).
    forward_auth_secret: str | None = None
    # Importação inteligente (app/gemini.py): fallback de extração quando o
    # recipe-scrapers falha, e importação por foto (Vision). Opcional — sem
    # chave, `gemini.is_available()` devolve False e a app funciona na
    # mesma (TODO.md: "funcionalidade opcional"). NUNCA testado contra a
    # API real nesta sessão de desenvolvimento (sem chave disponível) — ver
    # aviso em TODO.md antes de confiar cegamente na extração em produção.
    gemini_api_key: str | None = None

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        """Refuse known development credentials in a production deployment."""
        if self.environment.lower() == "production":
            if self.auth_secret == "dev-secret-change-me-in-production" or len(self.auth_secret) < 32:
                raise ValueError("AUTH_SECRET must be set to a random value of at least 32 characters")
            if self.trust_forward_auth and (not self.forward_auth_secret or len(self.forward_auth_secret) < 32):
                raise ValueError("FORWARD_AUTH_SECRET must contain at least 32 characters when forward auth is enabled")
        return self

    @property
    def async_database_url(self) -> str:
        """Só a autenticação (fastapi-users) usa isto — a lib exige
        `AsyncSession`, sem variante síncrona (verificado no código-fonte de
        `fastapi_users_db_sqlalchemy` 7.0.0). O resto da app (`crud.py`,
        todos os routers) continua 100% síncrono sobre `database_url`; esta
        é a mesma BD, só um driver diferente (`asyncpg` em vez de
        `psycopg2`) para essa fatia isolada."""
        return self.database_url.replace("+psycopg2", "+asyncpg")


@lru_cache
def get_settings() -> Settings:
    return Settings()
