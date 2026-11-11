"""Invariante central do Tacho: tudo é filtrado pela workspace do
utilizador autenticado. Um utilizador de outra workspace recebe sempre 404
para dados alheios — nunca 200 e nunca 403 (que revelaria que o recurso
existe) — e as suas listagens nunca incluem dados de outra workspace."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

CreateRecipe = Callable[..., dict[str, Any]]

PLAN_DAY = "2026-03-02"


@pytest.fixture
def owner_data(
    client: TestClient, create_recipe: CreateRecipe, png_upload: Callable[[], dict[str, Any]]
) -> dict[str, str]:
    """Um exemplar de cada recurso na workspace do dono (`client`)."""
    category = client.post("/categories", json={"name": "Peixe"}).json()
    tag = client.post("/tags", json={"name": "rápido"}).json()
    recipe = create_recipe(
        client,
        title="Receita privada",
        ingredients=[{"name": "Bacalhau", "quantity": 1, "unit": "kg"}],
        category_ids=[category["id"]],
        tag_ids=[tag["id"]],
    )
    cover = client.post(f"/recipes/{recipe['id']}/image", files=png_upload())
    assert cover.status_code == 200, cover.text
    gallery = client.post(f"/recipes/{recipe['id']}/images", files=png_upload())
    assert gallery.status_code == 201, gallery.text
    cookbook = client.post("/cookbooks", json={"name": "Coleção privada"}).json()
    assert client.post(f"/cookbooks/{cookbook['id']}/recipes/{recipe['id']}").status_code == 200
    pantry_item = client.post("/pantry", json={"name": "Azeite"}).json()
    shopping_item = client.post("/shopping-list", json={"name": "Leite", "quantity": "1 L"}).json()
    entry = client.put(f"/meal-plan/{PLAN_DAY}/jantar", json={"recipe_id": recipe["id"]})
    assert entry.status_code == 200, entry.text
    return {
        "recipe": recipe["id"],
        "cover_path": cover.json()["image_path"],
        "gallery_image": gallery.json()["images"][0]["id"],
        "gallery_path": gallery.json()["images"][0]["filename"],
        "cookbook": cookbook["id"],
        "pantry_item": pantry_item["id"],
        "shopping_item": shopping_item["id"],
        "category": category["id"],
        "tag": tag["id"],
    }


FOREIGN_REQUESTS = [
    ("GET", "/recipes/{recipe}", None),
    ("PUT", "/recipes/{recipe}", {"title": "Sequestrada"}),
    ("DELETE", "/recipes/{recipe}", None),
    ("GET", "/recipes/{recipe}/export", None),
    ("POST", "/recipes/{recipe}/favorite", None),
    ("PATCH", "/recipes/{recipe}/rating", {"rating": 1}),
    ("POST", "/recipes/{recipe}/share", None),
    ("POST", "/recipes/{recipe}/duplicate", None),
    ("POST", "/recipes/{recipe}/mark-made", None),
    ("POST", "/recipes/{recipe}/comments", {"text": "olá"}),
    ("POST", "/recipes/{recipe}/shopping-list", None),
    ("DELETE", "/recipes/{recipe}/images/{gallery_image}", None),
    ("POST", "/recipes/{recipe}/images/{gallery_image}/cover", None),
    ("GET", "/cookbooks/{cookbook}", None),
    ("DELETE", "/cookbooks/{cookbook}", None),
    ("POST", "/cookbooks/{cookbook}/recipes/{recipe}", None),
    ("DELETE", "/cookbooks/{cookbook}/recipes/{recipe}", None),
    ("PATCH", "/pantry/{pantry_item}", {"has_it": False}),
    ("DELETE", "/pantry/{pantry_item}", None),
    ("PATCH", "/shopping-list/{shopping_item}", {"is_checked": True}),
    ("DELETE", "/shopping-list/{shopping_item}", None),
    ("DELETE", f"/meal-plan/{PLAN_DAY}/jantar", None),
    ("PUT", f"/meal-plan/{PLAN_DAY}/jantar", {"recipe_id": "{recipe}"}),
    ("PATCH", "/categories/{category}", {"name": "Roubada"}),
    ("DELETE", "/categories/{category}", None),
    ("DELETE", "/tags/{tag}", None),
    ("GET", "/media/{cover_path}", None),
    ("GET", "/media/{gallery_path}", None),
]


def _fill(value: Any, ids: dict[str, str]) -> Any:
    if isinstance(value, str):
        return value.format(**ids)
    if isinstance(value, dict):
        return {key: _fill(item, ids) for key, item in value.items()}
    return value


@pytest.mark.parametrize(("method", "path", "body"), FOREIGN_REQUESTS, ids=[f"{m} {p}" for m, p, _ in FOREIGN_REQUESTS])
def test_other_workspace_gets_404_for_foreign_resources(
    other_client: TestClient, owner_data: dict[str, str], method: str, path: str, body: dict[str, Any] | None
) -> None:
    response = other_client.request(method, _fill(path, owner_data), json=_fill(body, owner_data))

    assert response.status_code == 404, response.text


def test_other_workspace_cannot_upload_images_to_foreign_recipe(
    other_client: TestClient,
    owner_data: dict[str, str],
    png_upload: Callable[[], dict[str, Any]],
    images_dir: Path,
) -> None:
    recipe_id = owner_data["recipe"]
    recipe_dir = images_dir / "receitas" / recipe_id
    files_before = sorted(recipe_dir.iterdir())

    assert other_client.post(f"/recipes/{recipe_id}/image", files=png_upload()).status_code == 404
    assert other_client.post(f"/recipes/{recipe_id}/images", files=png_upload()).status_code == 404
    assert sorted(recipe_dir.iterdir()) == files_before


def test_foreign_requests_leave_owner_data_untouched(
    client: TestClient, other_client: TestClient, owner_data: dict[str, str]
) -> None:
    for method, path, body in FOREIGN_REQUESTS:
        other_client.request(method, _fill(path, owner_data), json=_fill(body, owner_data))

    recipe = client.get(f"/recipes/{owner_data['recipe']}")
    assert recipe.status_code == 200
    assert recipe.json()["title"] == "Receita privada"
    assert recipe.json()["rating"] is None
    assert recipe.json()["comments"] == []
    assert len(recipe.json()["images"]) == 1
    assert [c["name"] for c in recipe.json()["categories"]] == ["Peixe"]
    assert [r["id"] for r in client.get(f"/cookbooks/{owner_data['cookbook']}").json()["recipes"]] == [
        owner_data["recipe"]
    ]
    assert [(i["name"], i["has_it"]) for i in client.get("/pantry").json()] == [("Azeite", True)]
    assert [(i["name"], i["is_checked"]) for i in client.get("/shopping-list").json()] == [("Leite", False)]
    plan = client.get("/meal-plan", params={"start": PLAN_DAY, "end": PLAN_DAY}).json()
    assert [entry["recipe"]["id"] for entry in plan] == [owner_data["recipe"]]
    assert len(client.get("/recipes").json()) == 1


@pytest.mark.parametrize(
    ("path", "params"),
    [
        ("/recipes", {}),
        ("/cookbooks", {}),
        ("/pantry", {}),
        ("/shopping-list", {}),
        ("/meal-plan", {"start": PLAN_DAY, "end": PLAN_DAY}),
        ("/categories", {}),
        ("/tags", {}),
    ],
)
def test_other_workspace_lists_are_empty(
    other_client: TestClient, owner_data: dict[str, str], path: str, params: dict[str, str]
) -> None:
    response = other_client.get(path, params=params)

    assert response.status_code == 200
    assert response.json() == []


def test_other_workspace_export_excludes_foreign_recipes(other_client: TestClient, owner_data: dict[str, str]) -> None:
    response = other_client.get("/recipes/export")

    assert response.status_code == 200
    assert response.json()["recipes"] == []


def test_other_workspace_filters_never_match_foreign_recipes(
    other_client: TestClient, owner_data: dict[str, str]
) -> None:
    for params in (
        {"q": "privada"},
        {"category_id": owner_data["category"]},
        {"tag_ids": owner_data["tag"]},
        {"ingredient": "bacalhau"},
    ):
        response = other_client.get("/recipes", params=params)
        assert response.status_code == 200
        assert response.json() == [], params


def test_foreign_category_and_tag_ids_are_ignored_on_create(
    other_client: TestClient, owner_data: dict[str, str], create_recipe: CreateRecipe
) -> None:
    recipe = create_recipe(
        other_client, title="Minha", category_ids=[owner_data["category"]], tag_ids=[owner_data["tag"]]
    )

    assert recipe["categories"] == []
    assert recipe["tags"] == []


def test_each_workspace_sees_only_its_own_recipes(
    client: TestClient, other_client: TestClient, owner_data: dict[str, str], create_recipe: CreateRecipe
) -> None:
    mine = create_recipe(other_client, title="Receita do outro")

    assert [r["title"] for r in other_client.get("/recipes").json()] == ["Receita do outro"]
    assert [r["title"] for r in client.get("/recipes").json()] == ["Receita privada"]
    assert client.get(f"/recipes/{mine['id']}").status_code == 404
