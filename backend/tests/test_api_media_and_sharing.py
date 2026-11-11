from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app import images
from app.models import Recipe

CreateRecipe = Callable[..., dict[str, Any]]
PngUpload = Callable[[], dict[str, Any]]


@pytest.fixture
def recipe_with_cover(client: TestClient, create_recipe: CreateRecipe, png_upload: PngUpload) -> dict[str, Any]:
    recipe = create_recipe(client, title="Pastéis de nata", ingredients=[{"name": "Massa folhada"}])
    response = client.post(f"/recipes/{recipe['id']}/image", files=png_upload())
    assert response.status_code == 200, response.text
    return response.json()


def share_token(client: TestClient, recipe_id: str) -> str:
    response = client.post(f"/recipes/{recipe_id}/share")
    assert response.status_code == 200, response.text
    return response.json()["share_url"].rsplit("/", 1)[1]


def test_uploaded_cover_is_stored_under_the_recipe_folder(
    recipe_with_cover: dict[str, Any], images_dir: Path, png_upload: PngUpload
) -> None:
    image_path = recipe_with_cover["image_path"]

    assert image_path.startswith(f"receitas/{recipe_with_cover['id']}/")
    assert (images_dir / image_path).read_bytes() == png_upload()["file"][1]


def test_media_requires_authentication(anon_client: TestClient, recipe_with_cover: dict[str, Any]) -> None:
    assert anon_client.get(f"/media/{recipe_with_cover['image_path']}").status_code == 401


def test_media_is_served_to_own_workspace(
    client: TestClient, recipe_with_cover: dict[str, Any], png_upload: PngUpload
) -> None:
    response = client.get(f"/media/{recipe_with_cover['image_path']}")

    assert response.status_code == 200
    assert response.content == png_upload()["file"][1]


def test_gallery_media_is_served_to_own_workspace(
    client: TestClient, create_recipe: CreateRecipe, png_upload: PngUpload
) -> None:
    recipe = create_recipe(client)
    gallery = client.post(f"/recipes/{recipe['id']}/images", files=png_upload()).json()

    response = client.get(f"/media/{gallery['images'][0]['filename']}")

    assert response.status_code == 200
    assert gallery["images"][0]["is_cover"] is True


def test_media_of_another_workspace_is_404(other_client: TestClient, recipe_with_cover: dict[str, Any]) -> None:
    assert other_client.get(f"/media/{recipe_with_cover['image_path']}").status_code == 404


def test_media_file_not_referenced_by_any_recipe_is_404(client: TestClient, images_dir: Path) -> None:
    (images_dir / "orphan.png").write_bytes(b"not referenced")

    assert client.get("/media/orphan.png").status_code == 404


def test_media_rejects_encoded_path_traversal(client: TestClient, tmp_path: Path) -> None:
    (tmp_path / "secret.txt").write_text("top secret")

    response = client.get("/media/..%2Fsecret.txt")

    assert response.status_code == 404
    assert "top secret" not in response.text


def test_media_rejects_traversal_even_when_stored_in_database(
    client: TestClient, create_recipe: CreateRecipe, db: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Defesa em profundidade: mesmo que um `image_path` malicioso chegue à
    base, `resolve_image_path` nunca serve ficheiros fora de `images_dir`."""
    (tmp_path / "secret.txt").write_text("top secret")
    recipe = create_recipe(client)
    db.execute(update(Recipe).where(Recipe.id == recipe["id"]).values(image_path="../secret.txt"))
    db.commit()
    resolved: list[str] = []
    original = images.resolve_image_path

    def spy(image_path: str, settings: Any) -> Path:
        resolved.append(image_path)
        return original(image_path, settings)

    monkeypatch.setattr(images, "resolve_image_path", spy)

    response = client.get("/media/..%2Fsecret.txt")

    assert resolved == ["../secret.txt"]  # passou a verificação na base e chegou ao disco
    assert response.status_code == 404
    assert "top secret" not in response.text


def test_share_returns_public_url_with_token_valid_for_five_hours(
    client: TestClient, recipe_with_cover: dict[str, Any]
) -> None:
    response = client.post(f"/recipes/{recipe_with_cover['id']}/share")

    assert response.status_code == 200
    body = response.json()
    base, token = body["share_url"].rsplit("/", 1)
    assert base == "http://testserver/partilha"
    assert len(token) >= 32
    expires_at = datetime.fromisoformat(body["share_expires_at"])
    assert timedelta(hours=4, minutes=59) < expires_at - datetime.now(UTC) <= timedelta(hours=5)


def test_public_recipe_is_readable_without_authentication(
    client: TestClient, anon_client: TestClient, recipe_with_cover: dict[str, Any]
) -> None:
    token = share_token(client, recipe_with_cover["id"])

    response = anon_client.get(f"/public/recipes/{token}")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Pastéis de nata"
    assert [i["name"] for i in body["ingredients"]] == ["Massa folhada"]
    # Vista pública deliberadamente estreita: nada de ids nem dados do agregado.
    assert not {"id", "workspace_id", "is_favorite", "rating", "comments", "images"} & body.keys()


def test_public_recipe_image_is_served_without_authentication(
    client: TestClient, anon_client: TestClient, recipe_with_cover: dict[str, Any], png_upload: PngUpload
) -> None:
    token = share_token(client, recipe_with_cover["id"])

    response = anon_client.get(f"/public/recipes/{token}/image")

    assert response.status_code == 200
    assert response.content == png_upload()["file"][1]


def test_public_recipe_image_is_404_when_recipe_has_no_cover(
    client: TestClient, anon_client: TestClient, create_recipe: CreateRecipe
) -> None:
    token = share_token(client, create_recipe(client)["id"])

    assert anon_client.get(f"/public/recipes/{token}/image").status_code == 404


def test_unknown_share_token_is_404(anon_client: TestClient, db: Session) -> None:
    assert anon_client.get("/public/recipes/does-not-exist").status_code == 404
    assert anon_client.get("/public/recipes/does-not-exist/image").status_code == 404


def test_expired_share_token_is_404(
    client: TestClient, anon_client: TestClient, recipe_with_cover: dict[str, Any], db: Session
) -> None:
    token = share_token(client, recipe_with_cover["id"])
    db.execute(
        update(Recipe)
        .where(Recipe.id == recipe_with_cover["id"])
        .values(share_expires_at=datetime.now(UTC) - timedelta(minutes=1))
    )
    db.commit()

    assert anon_client.get(f"/public/recipes/{token}").status_code == 404
    assert anon_client.get(f"/public/recipes/{token}/image").status_code == 404


def test_sharing_again_rotates_the_token(
    client: TestClient, anon_client: TestClient, recipe_with_cover: dict[str, Any]
) -> None:
    old_token = share_token(client, recipe_with_cover["id"])
    new_token = share_token(client, recipe_with_cover["id"])

    assert new_token != old_token
    assert anon_client.get(f"/public/recipes/{old_token}").status_code == 404
    assert anon_client.get(f"/public/recipes/{new_token}").status_code == 200
