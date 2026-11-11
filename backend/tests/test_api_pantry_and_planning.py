from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

CreateRecipe = Callable[..., dict[str, Any]]

SOURCE_WEEK = "2026-03-02"  # segunda-feira
TARGET_WEEK = "2026-03-09"


def week_plan(client: TestClient, start: str, end: str) -> list[tuple[str, str, str]]:
    response = client.get("/meal-plan", params={"start": start, "end": end})
    assert response.status_code == 200, response.text
    return sorted((entry["day"], entry["meal_type"], entry["recipe"]["title"]) for entry in response.json())


def test_pantry_item_crud(client: TestClient) -> None:
    created = client.post("/pantry", json={"name": "Arroz", "quantity": 2, "unit": "kg", "expires_on": "2026-12-31"})
    assert created.status_code == 201
    item = created.json()
    assert item["has_it"] is True
    assert (item["quantity"], item["unit"], item["expires_on"]) == (2, "kg", "2026-12-31")
    client.post("/pantry", json={"name": "Azeite"})
    assert [i["name"] for i in client.get("/pantry").json()] == ["Arroz", "Azeite"]

    updated = client.patch(f"/pantry/{item['id']}", json={"has_it": False, "quantity": 0.5})
    assert updated.status_code == 200
    assert (updated.json()["has_it"], updated.json()["quantity"], updated.json()["unit"]) == (False, 0.5, "kg")

    assert client.delete(f"/pantry/{item['id']}").status_code == 204
    assert [i["name"] for i in client.get("/pantry").json()] == ["Azeite"]
    assert client.delete(f"/pantry/{item['id']}").status_code == 404


def test_pantry_rejects_negative_quantity(client: TestClient) -> None:
    assert client.post("/pantry", json={"name": "Arroz", "quantity": -1}).status_code == 422


def test_makeable_filter_returns_recipes_fully_covered_by_pantry(
    client: TestClient, create_recipe: CreateRecipe
) -> None:
    create_recipe(
        client,
        title="Omelete",
        ingredients=[{"name": "Recheio", "is_header": True}, {"name": "Ovos"}, {"name": "Sal"}],
    )
    create_recipe(client, title="Bolo", ingredients=[{"name": "Ovos"}, {"name": "Farinha"}])
    client.post("/pantry", json={"name": "Ovos"})
    client.post("/pantry", json={"name": "Sal"})

    makeable = client.get("/recipes", params={"makeable": "true"})

    assert makeable.status_code == 200
    assert [r["title"] for r in makeable.json()] == ["Omelete"]
    by_title = {r["title"]: r for r in client.get("/recipes").json()}
    assert by_title["Omelete"]["is_makeable"] is True
    assert by_title["Bolo"]["is_makeable"] is False
    assert by_title["Bolo"]["missing_ingredients"] == ["Farinha"]


def test_makeable_ignores_pantry_items_marked_as_missing(client: TestClient, create_recipe: CreateRecipe) -> None:
    create_recipe(client, title="Ovo cozido", ingredients=[{"name": "Ovos"}])
    item = client.post("/pantry", json={"name": "Ovos"}).json()
    client.patch(f"/pantry/{item['id']}", json={"has_it": False})

    assert client.get("/recipes", params={"makeable": "true"}).json() == []


def test_meal_plan_upsert_replaces_the_slot(client: TestClient, create_recipe: CreateRecipe) -> None:
    sopa = create_recipe(client, title="Sopa")
    peixe = create_recipe(client, title="Peixe")

    first = client.put(f"/meal-plan/{SOURCE_WEEK}/jantar", json={"recipe_id": sopa["id"]})
    second = client.put(f"/meal-plan/{SOURCE_WEEK}/jantar", json={"recipe_id": peixe["id"]})

    assert first.status_code == second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert week_plan(client, SOURCE_WEEK, SOURCE_WEEK) == [(SOURCE_WEEK, "jantar", "Peixe")]


def test_meal_plan_rejects_unknown_meal_type_and_recipe(client: TestClient, create_recipe: CreateRecipe) -> None:
    recipe = create_recipe(client)

    assert client.put(f"/meal-plan/{SOURCE_WEEK}/ceia", json={"recipe_id": recipe["id"]}).status_code == 422
    missing = client.put(f"/meal-plan/{SOURCE_WEEK}/jantar", json={"recipe_id": "00000000-0000-0000-0000-00000000abcd"})
    assert missing.status_code == 404


def test_meal_plan_delete(client: TestClient, create_recipe: CreateRecipe) -> None:
    recipe = create_recipe(client)
    client.put(f"/meal-plan/{SOURCE_WEEK}/almoco", json={"recipe_id": recipe["id"]})

    assert client.delete(f"/meal-plan/{SOURCE_WEEK}/almoco").status_code == 204
    assert week_plan(client, SOURCE_WEEK, SOURCE_WEEK) == []
    assert client.delete(f"/meal-plan/{SOURCE_WEEK}/almoco").status_code == 404


def test_copy_week_keeps_day_offsets(client: TestClient, create_recipe: CreateRecipe) -> None:
    sopa = create_recipe(client, title="Sopa")
    peixe = create_recipe(client, title="Peixe")
    client.put("/meal-plan/2026-03-02/almoco", json={"recipe_id": sopa["id"]})
    client.put("/meal-plan/2026-03-08/jantar", json={"recipe_id": peixe["id"]})

    response = client.post(
        "/meal-plan/copy-week", json={"source_week_start": SOURCE_WEEK, "target_week_start": TARGET_WEEK}
    )

    assert response.status_code == 200
    expected = [("2026-03-09", "almoco", "Sopa"), ("2026-03-15", "jantar", "Peixe")]
    assert sorted((e["day"], e["meal_type"], e["recipe"]["title"]) for e in response.json()) == expected
    assert week_plan(client, TARGET_WEEK, "2026-03-15") == expected
    assert len(week_plan(client, SOURCE_WEEK, "2026-03-08")) == 2


def test_copy_week_respects_overwrite_flag(client: TestClient, create_recipe: CreateRecipe) -> None:
    sopa = create_recipe(client, title="Sopa")
    peixe = create_recipe(client, title="Peixe")
    client.put("/meal-plan/2026-03-02/almoco", json={"recipe_id": sopa["id"]})
    client.put("/meal-plan/2026-03-09/almoco", json={"recipe_id": peixe["id"]})
    payload = {"source_week_start": SOURCE_WEEK, "target_week_start": TARGET_WEEK}

    client.post("/meal-plan/copy-week", json=payload)
    assert week_plan(client, TARGET_WEEK, TARGET_WEEK) == [("2026-03-09", "almoco", "Peixe")]

    client.post("/meal-plan/copy-week", json={**payload, "overwrite": True})
    assert week_plan(client, TARGET_WEEK, TARGET_WEEK) == [("2026-03-09", "almoco", "Sopa")]
