from pathlib import Path

import pytest
from fastapi import HTTPException

from app.config import Settings
from app.images import resolve_image_path, validate_remote_url


def settings(tmp_path: Path, **overrides) -> Settings:
    values = {
        "database_url": "postgresql+psycopg2://tacho:tacho@localhost/tacho",
        "redis_url": "redis://localhost:6379/0",
        "images_dir": str(tmp_path),
    }
    values.update(overrides)
    return Settings(**values)


def test_production_rejects_default_auth_secret(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="AUTH_SECRET"):
        settings(tmp_path, environment="production", auth_secret="dev-secret-change-me-in-production")


def test_image_path_cannot_escape_media_root(tmp_path: Path) -> None:
    with pytest.raises(HTTPException):
        resolve_image_path("../secret", settings(tmp_path))


@pytest.mark.parametrize("url", ["http://127.0.0.1/a", "http://[::1]/a"])
def test_remote_import_rejects_loopback(url: str) -> None:
    with pytest.raises(ValueError, match="private or local"):
        validate_remote_url(url)
