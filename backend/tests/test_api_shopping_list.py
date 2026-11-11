"""`POST /shopping-list/generate` — documenta o comportamento atual.

Aqui só se fixam os casos com nomes iguais; os casos-limite da exclusão
pela despensa (ex. "sal" vs "salmão", plurais) estão em
`test_api_pantry_matching.py`.
"""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

CreateRecipe = Callable[..., dict[str, Any]]

WEEK_START = "2026-03-02"  # segunda-feira


def plan(client: TestClient, day: str, meal_type: str, recipe_id: str) -> None:
    response = client.put(f"/meal-plan/{day}/{meal_type}", json={"recipe_id": recipe_id})
    assert response.status_code == 200, response.text


def generate(client: TestClient, week_start: str = WEEK_START) -> list[tuple[str, str | None]]:
    response = client.post("/shopping-list/generate", json={"week_start": week_start})
    assert response.status_code == 200, response.text
    return sorted((item["name"], item["quantity"]) for item in response.json())


@pytest.fixture
def planned_week(client: TestClient, create_recipe: CreateRecipe) -> None:
    bolo = create_recipe(
        client,
        title="Bolo",
        ingredients=[
            {"name": "Massa", "is_header": True},
            {"name": "Farinha", "quantity": 200, "unit": "g"},
            {"name": "Leite", "quantity": 1, "unit": "L"},
            {"name": "Ovos", "quantity": 3},
        ],
    )
    panquecas = create_recipe(
        client,
        title="Panquecas",
        ingredients=[
            {"name": "farinha", "quantity": 300, "unit": "g"},
            {"name": "Leite", "quantity": 2, "unit": "chávenas"},
            {"name": "Ovos", "quantity": 2},
            {"name": "Sal"},
        ],
    )
    plan(client, "2026-03-02", "almoco", bolo["id"])
    plan(client, "2026-03-08", "jantar", panquecas["id"])


def test_generate_aggregates_same_name_and_unit_across_planned_recipes(client: TestClient, planned_week: None) -> None:
    assert generate(client) == [
        ("Farinha", "500 g"),
        ("Leite", "1 L"),
        ("Leite", "2 chávenas"),
        ("Ovos", "5"),
        ("Sal", None),
    ]


def test_generate_skips_section_headers(client: TestClient, planned_week: None) -> None:
    assert "Massa" not in [name for name, _ in generate(client)]


def test_generate_ignores_entries_outside_the_week(client: TestClient, create_recipe: CreateRecipe) -> None:
    recipe = create_recipe(client, ingredients=[{"name": "Arroz", "quantity": 1, "unit": "kg"}])
    plan(client, "2026-03-01", "jantar", recipe["id"])  # domingo anterior
    plan(client, "2026-03-09", "jantar", recipe["id"])  # segunda seguinte

    assert generate(client) == []


def test_generate_skips_ingredients_already_unchecked_in_the_list(client: TestClient, planned_week: None) -> None:
    client.post("/shopping-list", json={"name": "ovos", "quantity": "1 dúzia"})

    items = generate(client)

    assert [item for item in items if item[0].lower() == "ovos"] == [("ovos", "1 dúzia")]


def test_generate_again_does_not_duplicate_unchecked_items(client: TestClient, planned_week: None) -> None:
    first = generate(client)

    assert generate(client) == first


def test_checked_items_do_not_block_regeneration(client: TestClient, planned_week: None) -> None:
    sal = client.post("/shopping-list", json={"name": "Sal"}).json()
    client.patch(f"/shopping-list/{sal['id']}", json={"is_checked": True})

    response = client.post("/shopping-list/generate", json={"week_start": WEEK_START})

    sal_items = [(item["name"], item["is_checked"]) for item in response.json() if item["name"] == "Sal"]
    assert sorted(sal_items) == [("Sal", False), ("Sal", True)]


def test_generate_excludes_ingredients_available_in_pantry(client: TestClient, planned_week: None) -> None:
    client.post("/pantry", json={"name": "Farinha"})
    client.post("/pantry", json={"name": "Ovos"})

    names = [name for name, _ in generate(client)]

    assert "Farinha" not in names
    assert "Ovos" not in names
    assert "Leite" in names


def test_pantry_items_marked_as_missing_do_not_exclude(client: TestClient, planned_week: None) -> None:
    item = client.post("/pantry", json={"name": "Farinha"}).json()
    client.patch(f"/pantry/{item['id']}", json={"has_it": False})

    assert ("Farinha", "500 g") in generate(client)


def test_shopping_list_item_crud(client: TestClient) -> None:
    created = client.post("/shopping-list", json={"name": "Pão", "quantity": "2"})
    assert created.status_code == 201
    item_id = created.json()["id"]
    assert created.json()["is_checked"] is False

    updated = client.patch(f"/shopping-list/{item_id}", json={"is_checked": True})
    assert updated.status_code == 200
    assert updated.json()["is_checked"] is True

    assert client.delete(f"/shopping-list/{item_id}").status_code == 204
    assert client.get("/shopping-list").json() == []
    assert client.delete(f"/shopping-list/{item_id}").status_code == 404
