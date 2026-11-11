import io
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.config import Settings
from app.database import get_db
from app.deps import get_workspace_id
from app.routers import media, public

IMAGE_PATH = "receitas/r1/foto.png"


def png(size: tuple[int, int]) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, (10, 120, 60)).save(buffer, "PNG")
    return buffer.getvalue()


@pytest.fixture
def images_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    settings = Settings(
        database_url="postgresql+psycopg2://tacho:tacho@localhost/tacho",
        redis_url="redis://localhost:6379/0",
        images_dir=str(tmp_path),
    )
    monkeypatch.setattr(media, "get_settings", lambda: settings)
    monkeypatch.setattr(public, "get_settings", lambda: settings)
    (tmp_path / "receitas" / "r1").mkdir(parents=True)
    (tmp_path / IMAGE_PATH).write_bytes(png((2000, 1000)))
    return tmp_path


def client(db: MagicMock) -> TestClient:
    app = FastAPI()
    app.include_router(media.router)
    app.include_router(public.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_workspace_id] = lambda: uuid.uuid4()
    return TestClient(app)


def authorised_db() -> MagicMock:
    db = MagicMock()
    db.scalar.return_value = uuid.uuid4()
    return db


def test_media_serves_original_with_immutable_private_cache(images_dir: Path) -> None:
    db = authorised_db()
    response = client(db).get(f"/media/{IMAGE_PATH}")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, max-age=31536000, immutable"
    assert response.headers["etag"] and response.headers["last-modified"]
    assert response.content == (images_dir / IMAGE_PATH).read_bytes()
    # Capa e galeria verificadas numa única ida à BD.
    assert db.scalar.call_count == 1


def test_media_serves_requested_variant_generating_it_on_demand(images_dir: Path) -> None:
    response = client(authorised_db()).get(f"/media/{IMAGE_PATH}", params={"size": "thumb"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/webp"
    assert response.headers["cache-control"] == "private, max-age=31536000, immutable"
    assert Image.open(io.BytesIO(response.content)).size == (480, 240)
    assert (images_dir / "receitas/r1/foto.thumb.webp").is_file()


def test_media_falls_back_to_original_when_variant_cannot_be_generated(images_dir: Path) -> None:
    (images_dir / IMAGE_PATH).write_bytes(b"not really a png")

    response = client(authorised_db()).get(f"/media/{IMAGE_PATH}", params={"size": "medium"})

    assert response.status_code == 200
    assert response.content == b"not really a png"


def test_media_rejects_unknown_size(images_dir: Path) -> None:
    response = client(authorised_db()).get(f"/media/{IMAGE_PATH}", params={"size": "huge"})

    assert response.status_code == 422


def test_media_hides_images_of_other_workspaces_and_their_variants(images_dir: Path) -> None:
    db = MagicMock()
    db.scalar.return_value = None

    for params in ({}, {"size": "thumb"}):
        assert client(db).get(f"/media/{IMAGE_PATH}", params=params).status_code == 404
    assert not (images_dir / "receitas/r1/foto.thumb.webp").exists()


def test_public_image_serves_variant_with_short_public_cache(images_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    recipe = SimpleNamespace(image_path=IMAGE_PATH)
    monkeypatch.setattr(public.crud, "get_recipe_by_share_token", lambda db, token: recipe)

    response = client(MagicMock()).get("/public/recipes/token/image", params={"size": "medium"})

    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=3600"
    assert Image.open(io.BytesIO(response.content)).size == (1200, 600)
