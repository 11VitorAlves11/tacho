import asyncio
import io
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image
from starlette.datastructures import Headers

from app.config import Settings
from app.images import (
    INVALID_IMAGE_DETAIL,
    InvalidImageError,
    copy_recipe_image,
    delete_recipe_image,
    ensure_variant,
    resolve_image_path,
    save_recipe_image,
    save_recipe_image_from_url,
    variant_path,
)
from app.remote_fetch import FetchedResponse

RECIPE_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
ORIENTATION = 0x0112
GPS_IFD = 0x8825


def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url="postgresql+psycopg2://tacho:tacho@localhost/tacho",
        redis_url="redis://localhost:6379/0",
        images_dir=str(tmp_path),
    )


def image_bytes(size: tuple[int, int], fmt: str = "JPEG", exif: Image.Exif | None = None) -> bytes:
    image = Image.new("RGB", size, (200, 80, 40))
    # Um quadrante distinto para conseguir verificar a rotação.
    image.paste((0, 0, 255), (0, 0, size[0] // 2, size[1] // 2))
    buffer = io.BytesIO()
    image.save(buffer, fmt, **({"exif": exif} if exif is not None else {}))
    return buffer.getvalue()


def upload(data: bytes, content_type: str) -> UploadFile:
    return UploadFile(io.BytesIO(data), filename="foto", headers=Headers({"content-type": content_type}))


def save(tmp_path: Path, data: bytes, content_type: str = "image/jpeg") -> str:
    return asyncio.run(save_recipe_image(upload(data, content_type), settings(tmp_path), RECIPE_ID))


def test_upload_keeps_original_and_creates_webp_variants(tmp_path: Path) -> None:
    data = image_bytes((3000, 2000))
    path = save(tmp_path, data)

    assert path.startswith(f"receitas/{RECIPE_ID}/") and path.endswith(".jpg")
    assert (tmp_path / path).read_bytes() == data
    with Image.open(tmp_path / variant_path(path, "thumb")) as thumb:
        assert (thumb.format, thumb.size) == ("WEBP", (480, 320))
    with Image.open(tmp_path / variant_path(path, "medium")) as medium:
        assert (medium.format, medium.size) == ("WEBP", (1200, 800))


def test_small_images_are_not_upscaled(tmp_path: Path) -> None:
    path = save(tmp_path, image_bytes((300, 200), "PNG"), "image/png")

    with Image.open(tmp_path / variant_path(path, "medium")) as medium:
        assert medium.size == (300, 200)


def test_variants_apply_exif_orientation_and_drop_exif(tmp_path: Path) -> None:
    exif = Image.Exif()
    exif[ORIENTATION] = 6  # rodar 90° no sentido dos ponteiros do relógio
    exif[GPS_IFD] = {2: (38.0, 42.0, 0.0)}
    path = save(tmp_path, image_bytes((1600, 800), exif=exif))

    with Image.open(tmp_path / path) as original:
        assert original.getexif().get_ifd(GPS_IFD)
    with Image.open(tmp_path / variant_path(path, "thumb")) as thumb:
        assert thumb.size == (480, 960)
        assert not thumb.getexif()
        assert "exif" not in thumb.info
        # O quadrante azul (canto superior esquerdo) passa para o superior direito.
        red, _, blue = thumb.convert("RGB").getpixel((470, 10))
        assert blue > 200 and red < 50


@pytest.mark.parametrize(
    ("data", "content_type"),
    [
        (b"not an image at all", "image/jpeg"),
        (image_bytes((50, 50), "PNG"), "image/jpeg"),
        (image_bytes((50, 50))[:200], "image/jpeg"),
    ],
    ids=["garbage", "png-declared-as-jpeg", "truncated"],
)
def test_upload_rejects_bytes_that_do_not_match_declared_type(tmp_path: Path, data: bytes, content_type: str) -> None:
    with pytest.raises(HTTPException) as excinfo:
        save(tmp_path, data, content_type)

    assert excinfo.value.status_code == 422
    assert excinfo.value.detail == INVALID_IMAGE_DETAIL
    assert not any(path.is_file() for path in tmp_path.rglob("*"))


@pytest.mark.filterwarnings("ignore::PIL.Image.DecompressionBombWarning")
@pytest.mark.parametrize("max_pixels", [100, 6000], ids=["pillow-error", "pillow-only-warns"])
def test_upload_rejects_decompression_bomb(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, max_pixels: int) -> None:
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", max_pixels)
    with pytest.raises(HTTPException) as excinfo:
        save(tmp_path, image_bytes((100, 100), "PNG"), "image/png")

    assert excinfo.value.status_code == 422


def test_delete_removes_original_and_variants(tmp_path: Path) -> None:
    path = save(tmp_path, image_bytes((1000, 1000)))

    delete_recipe_image(path, settings(tmp_path))

    assert list((tmp_path / "receitas" / str(RECIPE_ID)).iterdir()) == []


def test_copy_creates_variants_for_the_copy(tmp_path: Path) -> None:
    path = save(tmp_path, image_bytes((1000, 500)))
    new_id = uuid.uuid4()

    copied = copy_recipe_image(path, settings(tmp_path), new_id)

    assert copied is not None and copied != path
    assert (tmp_path / variant_path(copied, "thumb")).is_file()
    assert (tmp_path / variant_path(copied, "medium")).is_file()


def test_ensure_variant_regenerates_missing_variant(tmp_path: Path) -> None:
    # Imagem antiga, plana, gravada antes de existirem variantes.
    (tmp_path / "antiga.png").write_bytes(image_bytes((2000, 1000), "PNG"))

    target = ensure_variant("antiga.png", "thumb", settings(tmp_path))

    assert target == tmp_path / "antiga.thumb.webp"
    with Image.open(target) as thumb:
        assert thumb.size == (480, 240)
    assert ensure_variant("antiga.png", "thumb", settings(tmp_path)) == target
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []


def test_ensure_variant_reports_missing_and_invalid_originals(tmp_path: Path) -> None:
    (tmp_path / "estragada.jpg").write_bytes(b"nope")

    with pytest.raises(FileNotFoundError):
        ensure_variant("nao-existe.jpg", "thumb", settings(tmp_path))
    with pytest.raises(InvalidImageError):
        ensure_variant("estragada.jpg", "thumb", settings(tmp_path))


@pytest.mark.parametrize("image_path", ["../segredo.jpg", "receitas/../../segredo.png", "/etc/passwd"])
def test_variant_names_cannot_escape_media_root(tmp_path: Path, image_path: str) -> None:
    with pytest.raises(HTTPException):
        resolve_image_path(variant_path(image_path, "thumb"), settings(tmp_path / "media"))
    with pytest.raises(HTTPException):
        ensure_variant(image_path, "medium", settings(tmp_path / "media"))


def test_variant_path_keeps_directory_and_replaces_extension() -> None:
    assert variant_path("receitas/r/abc.jpg", "thumb") == "receitas/r/abc.thumb.webp"
    assert variant_path("abc.png", "medium") == "abc.medium.webp"


def fake_response(data: bytes, content_type: str) -> FetchedResponse:
    return FetchedResponse(url="https://example.com/foto", content_type=content_type, content=data, encoding=None)


def test_save_from_url_stores_image_and_variants(tmp_path: Path) -> None:
    data = image_bytes((1600, 1200), "WEBP")
    with patch("app.images.fetch_public_url", return_value=fake_response(data, "image/webp")) as fetch:
        path = save_recipe_image_from_url("https://example.com/foto.webp", settings(tmp_path), RECIPE_ID)

    fetch.assert_called_once()
    assert path is not None and path.endswith(".webp")
    assert (tmp_path / path).read_bytes() == data
    with Image.open(tmp_path / variant_path(path, "medium")) as medium:
        assert medium.size == (1200, 900)


def test_save_from_url_ignores_bytes_that_are_not_the_announced_image(tmp_path: Path) -> None:
    with patch("app.images.fetch_public_url", return_value=fake_response(b"<html>oops</html>" * 20, "image/jpeg")):
        path = save_recipe_image_from_url("https://example.com/foto.jpg", settings(tmp_path), RECIPE_ID)

    assert path is None
    assert not any(p.is_file() for p in tmp_path.rglob("*"))
