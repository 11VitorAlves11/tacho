from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import Recipe

CreateRecipe = Callable[..., dict[str, Any]]


def _set_image(db: Session, recipe: dict[str, Any], image_path: str) -> None:
    db.execute(update(Recipe).where(Recipe.id == recipe["id"]).values(image_path=image_path))
    db.commit()


def test_new_cookbook_has_no_cover_images(client: TestClient) -> None:
    response = client.post("/cookbooks", json={"name": "Vazia"})

    assert response.status_code == 201
    assert response.json()["cover_image_paths"] == []
    assert client.get("/cookbooks").json()[0]["cover_image_paths"] == []


def test_list_cookbooks_returns_up_to_four_cover_images_by_title(
    client: TestClient, create_recipe: CreateRecipe, db: Session
) -> None:
    cookbook = client.post("/cookbooks", json={"name": "Jantares"}).json()
    paths: dict[str, str] = {}
    for title in ["Esparguete", "Bacalhau", "Arroz", "Caril", "Dourada"]:
        recipe = create_recipe(client, title=title)
        paths[title] = f"receitas/{recipe['id']}/capa.webp"
        _set_image(db, recipe, paths[title])
        assert client.post(f"/cookbooks/{cookbook['id']}/recipes/{recipe['id']}").status_code == 200

    [summary] = client.get("/cookbooks").json()

    assert summary["recipe_count"] == 5
    assert summary["cover_image_paths"] == [paths[title] for title in ["Arroz", "Bacalhau", "Caril", "Dourada"]]


def test_cover_images_skip_recipes_without_photo(client: TestClient, create_recipe: CreateRecipe, db: Session) -> None:
    cookbook = client.post("/cookbooks", json={"name": "Sopas"}).json()
    with_photo = create_recipe(client, title="Sopa de abóbora")
    without_photo = create_recipe(client, title="Caldo verde")
    _set_image(db, with_photo, "receitas/x/capa.webp")
    for recipe in (with_photo, without_photo):
        assert client.post(f"/cookbooks/{cookbook['id']}/recipes/{recipe['id']}").status_code == 200

    [summary] = client.get("/cookbooks").json()

    assert summary["recipe_count"] == 2
    assert summary["cover_image_paths"] == ["receitas/x/capa.webp"]
