"""Correspondência despensa ↔ ingrediente (`crud._in_pantry`).

A mesma regra decide o que é excluído em `POST /shopping-list/generate`, em
`POST /recipes/{id}/shopping-list/missing` e o que aparece em
`missing_ingredients` / filtro `makeable` de `GET /recipes` — por isso cada
caso é verificado nos três caminhos.
"""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

CreateRecipe = Callable[..., dict[str, Any]]

WEEK_START = "2026-03-02"  # segunda-feira


def clear_shopping_list(client: TestClient) -> None:
    for item in client.get("/shopping-list").json():
        assert client.delete(f"/shopping-list/{item['id']}").status_code == 204


def names_to_buy_per_path(client: TestClient, recipe_id: str) -> dict[str, list[str]]:
    summary = next(r for r in client.get("/recipes").json() if r["id"] == recipe_id)
    makeable_ids = [r["id"] for r in client.get("/recipes", params={"makeable": "true"}).json()]

    missing = client.post(f"/recipes/{recipe_id}/shopping-list/missing")
    assert missing.status_code == 200, missing.text
    clear_shopping_list(client)

    planned = client.put(f"/meal-plan/{WEEK_START}/jantar", json={"recipe_id": recipe_id})
    assert planned.status_code == 200, planned.text
    generated = client.post("/shopping-list/generate", json={"week_start": WEEK_START})
    assert generated.status_code == 200, generated.text

    assert summary["missing_ingredient_count"] == len(summary["missing_ingredients"])
    assert summary["is_makeable"] is (not summary["missing_ingredients"])
    assert (recipe_id in makeable_ids) is summary["is_makeable"]
    return {
        "missing_ingredients": sorted(summary["missing_ingredients"]),
        "shopping-list/missing": sorted(item["name"] for item in missing.json()),
        "shopping-list/generate": sorted(item["name"] for item in generated.json()),
    }


@pytest.mark.parametrize(
    ("pantry", "ingredients", "expected_to_buy"),
    [
        pytest.param(
            ["sal"],
            ["Sal", "Sal grosso", "Salmão", "Salsa fresca", "Salsichas"],
            ["Salmão", "Salsa fresca", "Salsichas"],
            id="whole-words-only",
        ),
        pytest.param(["ovo"], ["Ovo", "Ovos", "Feijão-frade novo"], ["Feijão-frade novo"], id="ovo-not-novo"),
        pytest.param(
            ["Ovos", "cebola", "pão", "Limões"],
            ["ovo", "Cebolas", "Pães", "Limão", "Leite"],
            ["Leite"],
            id="simple-plurals",
        ),
        pytest.param(["azeite"], ["Azeite virgem extra"], [], id="pantry-word-inside-longer-name"),
        pytest.param(["azeite virgem"], ["Azeite", "Azeite virgem extra"], ["Azeite"], id="all-pantry-words-required"),
        pytest.param(["ACUCAR mascavado"], ["Açúcar mascavado"], [], id="case-and-accents"),
        pytest.param([" ", "-", "123"], ["Farinha"], ["Farinha"], id="pantry-names-without-letters-ignored"),
    ],
)
def test_pantry_matching_is_consistent_across_paths(
    client: TestClient,
    create_recipe: CreateRecipe,
    pantry: list[str],
    ingredients: list[str],
    expected_to_buy: list[str],
) -> None:
    for name in pantry:
        assert client.post("/pantry", json={"name": name}).status_code == 201
    recipe = create_recipe(client, ingredients=[{"name": name} for name in ingredients])

    result = names_to_buy_per_path(client, recipe["id"])

    assert result == {path: sorted(expected_to_buy) for path in result}


def test_known_limitation_single_word_pantry_item_covers_longer_names(
    client: TestClient, create_recipe: CreateRecipe
) -> None:
    client.post("/pantry", json={"name": "Alho"})
    recipe = create_recipe(client, ingredients=[{"name": "Alho francês"}])

    assert names_to_buy_per_path(client, recipe["id"])["missing_ingredients"] == []


def test_add_recipe_dedupes_by_normalized_name(client: TestClient, create_recipe: CreateRecipe) -> None:
    client.post("/shopping-list", json={"name": "acucar"})
    recipe = create_recipe(
        client,
        ingredients=[{"name": "Açúcar"}, {"name": "FARINHA"}, {"name": "farinha"}, {"name": "Leite"}],
    )

    response = client.post(f"/recipes/{recipe['id']}/shopping-list")

    assert response.status_code == 200, response.text
    assert [item["name"] for item in response.json()] == ["FARINHA", "Leite"]


def test_add_recipe_does_not_exclude_pantry_items(client: TestClient, create_recipe: CreateRecipe) -> None:
    client.post("/pantry", json={"name": "Leite"})
    recipe = create_recipe(client, ingredients=[{"name": "Leite"}])

    response = client.post(f"/recipes/{recipe['id']}/shopping-list")

    assert [item["name"] for item in response.json()] == ["Leite"]
