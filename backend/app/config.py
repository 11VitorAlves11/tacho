from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str
    cors_origins: list[str] = ["http://localhost:5173"]
    # Caminho relativo ao WORKDIR do container (/app). Em dev resolve para
    # backend/images/ via bind mount; em docker-compose.yml há também um
    # volume Docker nomeado (tacho_images) montado no mesmo caminho, mais
    # específico que o bind mount — garante que as fotos sobrevivem a um
    # deploy sem o bind mount de desenvolvimento.
    images_dir: str = "images"
    max_image_bytes: int = 8 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
