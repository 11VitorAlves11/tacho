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


def sources_of(items: list[dict[str, Any]]) -> list[tuple[str, str | None, list[str]]]:
    return sorted((item["name"], item["quantity"], [source["title"] for source in item["sources"]]) for item in items)


def test_generated_items_record_every_source_recipe(client: TestClient, planned_week: None) -> None:
    response = client.post("/shopping-list/generate", json={"week_start": WEEK_START})

    expected = [
        ("Farinha", "500 g", ["Bolo", "Panquecas"]),
        ("Leite", "1 L", ["Bolo"]),
        ("Leite", "2 chávenas", ["Panquecas"]),
        ("Ovos", "5", ["Bolo", "Panquecas"]),
        ("Sal", None, ["Panquecas"]),
    ]
    assert sources_of(response.json()) == expected
    assert sources_of(client.get("/shopping-list").json()) == expected


def test_generate_attaches_recipes_to_ingredients_already_listed(client: TestClient, planned_week: None) -> None:
    client.post("/shopping-list", json={"name": "ovos", "quantity": "1 dúzia"})

    response = client.post("/shopping-list/generate", json={"week_start": WEEK_START})

    assert ("ovos", "1 dúzia", ["Bolo", "Panquecas"]) in sources_of(response.json())


def test_added_recipe_is_attached_to_existing_unchecked_item(client: TestClient, create_recipe: CreateRecipe) -> None:
    sopa = create_recipe(client, title="Sopa", ingredients=[{"name": "Cenoura", "quantity": 2}])
    salada = create_recipe(client, title="Salada", ingredients=[{"name": "Cenoura", "quantity": 1}, {"name": "Alface"}])
    assert client.post(f"/recipes/{sopa['id']}/shopping-list").status_code == 200

    added = client.post(f"/recipes/{salada['id']}/shopping-list").json()

    assert sources_of(added) == [("Alface", None, ["Salada"])]
    assert sources_of(client.get("/shopping-list").json()) == [
        ("Alface", None, ["Salada"]),
        ("Cenoura", "2", ["Salada", "Sopa"]),
    ]


def test_checked_items_do_not_receive_new_sources(client: TestClient, create_recipe: CreateRecipe) -> None:
    item = client.post("/shopping-list", json={"name": "Cenoura"}).json()
    client.patch(f"/shopping-list/{item['id']}", json={"is_checked": True})
    recipe = create_recipe(client, title="Sopa", ingredients=[{"name": "Cenoura"}])

    client.post(f"/recipes/{recipe['id']}/shopping-list")

    assert sources_of(client.get("/shopping-list").json()) == [("Cenoura", None, []), ("Cenoura", None, ["Sopa"])]


def test_missing_ingredients_record_their_source(client: TestClient, create_recipe: CreateRecipe) -> None:
    client.post("/shopping-list", json={"name": "Alho"})
    recipe = create_recipe(client, title="Açorda", ingredients=[{"name": "Pão"}, {"name": "alho"}])

    added = client.post(f"/recipes/{recipe['id']}/shopping-list/missing").json()

    assert sources_of(added) == [("Pão", None, ["Açorda"])]
    assert ("Alho", None, ["Açorda"]) in sources_of(client.get("/shopping-list").json())


def test_manual_items_have_no_sources(client: TestClient) -> None:
    created = client.post("/shopping-list", json={"name": "Pão"})

    assert created.json()["sources"] == []
    assert client.get("/shopping-list").json()[0]["sources"] == []


def test_deleting_a_recipe_keeps_the_item_but_drops_the_source(client: TestClient, create_recipe: CreateRecipe) -> None:
    sopa = create_recipe(client, title="Sopa", ingredients=[{"name": "Cenoura"}, {"name": "Nabo"}])
    salada = create_recipe(client, title="Salada", ingredients=[{"name": "Cenoura"}])
    client.post(f"/recipes/{sopa['id']}/shopping-list")
    client.post(f"/recipes/{salada['id']}/shopping-list")

    assert client.delete(f"/recipes/{sopa['id']}").status_code == 204

    assert sources_of(client.get("/shopping-list").json()) == [("Cenoura", None, ["Salada"]), ("Nabo", None, [])]


def test_clear_checked_removes_only_bought_items_of_the_workspace(client: TestClient, other_client: TestClient) -> None:
    for name in ("Pão", "Leite", "Ovos"):
        item = client.post("/shopping-list", json={"name": name}).json()
        if name != "Ovos":
            client.patch(f"/shopping-list/{item['id']}", json={"is_checked": True})
    other_item = other_client.post("/shopping-list", json={"name": "Café"}).json()
    other_client.patch(f"/shopping-list/{other_item['id']}", json={"is_checked": True})

    response = client.delete("/shopping-list/checked")

    assert response.status_code == 200
    assert response.json() == {"deleted": 2}
    assert [item["name"] for item in client.get("/shopping-list").json()] == ["Ovos"]
    assert [item["name"] for item in other_client.get("/shopping-list").json()] == ["Café"]
    assert client.delete("/shopping-list/checked").json() == {"deleted": 0}


def test_clearing_checked_items_keeps_their_source_recipes(client: TestClient, create_recipe: CreateRecipe) -> None:
    recipe = create_recipe(client, title="Sopa", ingredients=[{"name": "Cenoura"}])
    item = client.post(f"/recipes/{recipe['id']}/shopping-list").json()[0]
    client.patch(f"/shopping-list/{item['id']}", json={"is_checked": True})

    assert client.delete("/shopping-list/checked").json() == {"deleted": 1}
    assert client.get(f"/recipes/{recipe['id']}").status_code == 200
