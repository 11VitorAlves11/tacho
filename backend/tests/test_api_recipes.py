from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.constants import DEFAULT_WORKSPACE_ID

CreateRecipe = Callable[..., dict[str, Any]]


def titles(response: Any) -> list[str]:
    assert response.status_code == 200, response.text
    return [recipe["title"] for recipe in response.json()]


def test_create_and_get_recipe_round_trips_content(client: TestClient) -> None:
    payload = {
        "title": "Bacalhau à Brás",
        "servings": 4,
        "prep_minutes": 15,
        "cook_minutes": 20,
        "ingredients": [
            {"name": "Bacalhau", "quantity": 400, "unit": "g"},
            {"name": "Batata palha", "quantity": 200, "unit": "g"},
        ],
        "steps": [{"instruction": "Desfiar o bacalhau."}, {"instruction": "Envolver tudo.", "duration_minutes": 5}],
    }

    created = client.post("/recipes", json=payload)

    assert created.status_code == 201
    body = created.json()
    assert body["workspace_id"] == str(DEFAULT_WORKSPACE_ID)
    assert body["is_favorite"] is False
    fetched = client.get(f"/recipes/{body['id']}")
    assert fetched.status_code == 200
    recipe = fetched.json()
    assert recipe["title"] == "Bacalhau à Brás"
    assert [(i["name"], i["quantity"], i["unit"], i["position"]) for i in recipe["ingredients"]] == [
        ("Bacalhau", 400, "g", 0),
        ("Batata palha", 200, "g", 1),
    ]
    assert [s["instruction"] for s in recipe["steps"]] == ["Desfiar o bacalhau.", "Envolver tudo."]


def test_update_recipe_replaces_fields_ingredients_and_steps(client: TestClient, create_recipe: CreateRecipe) -> None:
    recipe = create_recipe(client, ingredients=[{"name": "Arroz"}], steps=[{"instruction": "Cozer"}])

    response = client.put(
        f"/recipes/{recipe['id']}",
        json={"title": "Arroz de pato no forno", "servings": 6, "ingredients": [{"name": "Pato"}], "steps": []},
    )

    assert response.status_code == 200
    updated = client.get(f"/recipes/{recipe['id']}").json()
    assert updated["title"] == "Arroz de pato no forno"
    assert updated["servings"] == 6
    assert [i["name"] for i in updated["ingredients"]] == ["Pato"]
    assert updated["steps"] == []


def test_delete_recipe_removes_it(client: TestClient, create_recipe: CreateRecipe) -> None:
    recipe = create_recipe(client)

    assert client.delete(f"/recipes/{recipe['id']}").status_code == 204

    assert client.get(f"/recipes/{recipe['id']}").status_code == 404
    assert client.delete(f"/recipes/{recipe['id']}").status_code == 404
    assert client.get("/recipes").json() == []


def test_unknown_recipe_is_404(client: TestClient) -> None:
    assert client.get("/recipes/00000000-0000-0000-0000-00000000abcd").status_code == 404


def test_favorite_toggle_flips_state_and_feeds_favorite_filter(client: TestClient, create_recipe: CreateRecipe) -> None:
    favorite = create_recipe(client, title="Favorita")
    create_recipe(client, title="Outra")

    first = client.post(f"/recipes/{favorite['id']}/favorite")
    assert first.status_code == 200
    assert first.json()["is_favorite"] is True
    assert client.get(f"/recipes/{favorite['id']}").json()["is_favorite"] is True
    assert titles(client.get("/recipes", params={"favorite": "true"})) == ["Favorita"]

    second = client.post(f"/recipes/{favorite['id']}/favorite")
    assert second.json()["is_favorite"] is False
    assert titles(client.get("/recipes", params={"favorite": "true"})) == []


@pytest.mark.parametrize("rating", [1, 5])
def test_rating_accepts_values_from_one_to_five(client: TestClient, create_recipe: CreateRecipe, rating: int) -> None:
    recipe = create_recipe(client)

    response = client.patch(f"/recipes/{recipe['id']}/rating", json={"rating": rating})

    assert response.status_code == 200
    assert response.json()["rating"] == rating


@pytest.mark.parametrize("rating", [0, 6, -1])
def test_rating_outside_one_to_five_is_rejected(client: TestClient, create_recipe: CreateRecipe, rating: int) -> None:
    recipe = create_recipe(client)

    response = client.patch(f"/recipes/{recipe['id']}/rating", json={"rating": rating})

    assert response.status_code == 422
    assert client.get(f"/recipes/{recipe['id']}").json()["rating"] is None


def test_rating_can_be_cleared_with_null(client: TestClient, create_recipe: CreateRecipe) -> None:
    recipe = create_recipe(client)
    client.patch(f"/recipes/{recipe['id']}/rating", json={"rating": 4})

    response = client.patch(f"/recipes/{recipe['id']}/rating", json={"rating": None})

    assert response.status_code == 200
    assert response.json()["rating"] is None


def test_list_filters_by_full_text_query(client: TestClient, create_recipe: CreateRecipe) -> None:
    create_recipe(client, title="Bacalhau com natas")
    create_recipe(client, title="Arroz de pato")

    assert titles(client.get("/recipes", params={"q": "bacalhau"})) == ["Bacalhau com natas"]
    # Pesquisa por prefixo enquanto se escreve.
    assert titles(client.get("/recipes", params={"q": "bacal"})) == ["Bacalhau com natas"]
    assert titles(client.get("/recipes", params={"q": "inexistente"})) == []


def test_list_filters_by_category(client: TestClient, create_recipe: CreateRecipe) -> None:
    dessert = client.post("/categories", json={"name": "Sobremesas"}).json()
    create_recipe(client, title="Arroz doce", category_ids=[dessert["id"]])
    create_recipe(client, title="Arroz de pato")

    assert titles(client.get("/recipes", params={"category_id": dessert["id"]})) == ["Arroz doce"]


def test_list_tag_filter_requires_every_tag(client: TestClient, create_recipe: CreateRecipe) -> None:
    quick = client.post("/tags", json={"name": "rápido"}).json()
    vegan = client.post("/tags", json={"name": "vegan"}).json()
    create_recipe(client, title="Salada", tag_ids=[quick["id"], vegan["id"]])
    create_recipe(client, title="Tosta", tag_ids=[quick["id"]])

    assert titles(client.get("/recipes", params={"tag_ids": quick["id"]})) == ["Salada", "Tosta"]
    assert titles(client.get("/recipes", params={"tag_ids": f"{quick['id']},{vegan['id']}"})) == ["Salada"]


def test_list_rejects_malformed_tag_ids(client: TestClient) -> None:
    assert client.get("/recipes", params={"tag_ids": "not-a-uuid"}).status_code == 422


def test_workspace_export_is_versioned_and_contains_full_recipes(
    client: TestClient, create_recipe: CreateRecipe
) -> None:
    create_recipe(client, title="Caldo verde", ingredients=[{"name": "Couve", "quantity": 1, "unit": "molho"}])
    create_recipe(client, title="Arroz de pato")

    response = client.get("/recipes/export")

    assert response.status_code == 200
    body = response.json()
    assert body["format"] == "tacho.recipe-export"
    assert body["version"] == 1
    assert [recipe["title"] for recipe in body["recipes"]] == ["Arroz de pato", "Caldo verde"]
    caldo = body["recipes"][1]
    assert caldo["ingredients"][0]["name"] == "Couve"
    assert {"id", "steps", "categories", "tags", "comments", "images"} <= caldo.keys()
