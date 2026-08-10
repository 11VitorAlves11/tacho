from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str
    # Assina os cookies de sessão (JWT do fastapi-users) — tem de ser fixo
    # e secreto em produção (.env), nunca o valor por omissão; um valor
    # aleatório a cada arranque invalidava a sessão de todos ao reiniciar.
    auth_secret: str = "dev-secret-change-me-in-production"
    # Cookie "Secure" só é entregue pelo browser em HTTPS — falso por
    # omissão para o dev local (http://localhost) funcionar; produção
    # (https://receitas.alveslab.dev) tem de o definir true no .env.
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
