"""`POST /recipes/import-file` — reimportar o JSON de `GET /recipes/export`."""

import copy
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

CreateRecipe = Callable[..., dict[str, Any]]


def export_document(*recipes: dict[str, Any]) -> dict[str, Any]:
    return {"format": "tacho.recipe-export", "version": 1, "recipes": list(recipes)}


def exported_recipe(title: str = "Caldo verde", **fields: Any) -> dict[str, Any]:
    recipe: dict[str, Any] = {
        "id": "00000000-0000-0000-0000-000000000001",
        "title": title,
        "servings": 4,
        "prep_minutes": 10,
        "cook_minutes": 30,
        "source_url": None,
        "rating": 4,
        "image_path": None,
        "ingredients": [
            {"name": "Sopa", "quantity": None, "unit": None, "is_header": True},
            {"name": "Couve", "quantity": 1, "unit": "molho", "is_header": False},
            {"name": "Batata", "quantity": 500, "unit": "g", "is_header": False},
        ],
        "steps": [{"instruction": "Cozer as batatas.", "duration_minutes": 20}, {"instruction": "Juntar a couve."}],
        "categories": [
            {"id": "00000000-0000-0000-0000-000000000002", "name": "Sopas", "color": "#2F855A", "icon": "main"}
        ],
        "tags": [{"id": "00000000-0000-0000-0000-000000000003", "name": "tradicional"}],
        "comments": [],
        "images": [],
    }
    recipe.update(fields)
    return recipe


def import_file(client: TestClient, document: Any, mode: str | None = None) -> Any:
    params = {"mode": mode} if mode else None
    return client.post("/recipes/import-file", json=document, params=params)


def recipe_titles(client: TestClient) -> list[str]:
    return [recipe["title"] for recipe in client.get("/recipes").json()]


def test_round_trip_export_then_import_skips_everything(client: TestClient, create_recipe: CreateRecipe) -> None:
    category = client.post("/categories", json={"name": "Sopas"}).json()
    tag = client.post("/tags", json={"name": "rápido"}).json()
    create_recipe(
        client,
        title="Caldo verde",
        ingredients=[{"name": "Couve"}, {"name": "Batata"}],
        category_ids=[category["id"]],
        tag_ids=[tag["id"]],
    )
    create_recipe(client, title="Arroz de pato", source_url="https://example.com/arroz")
    create_recipe(client, title="Sem ingredientes")
    exported = client.get("/recipes/export").json()

    response = import_file(client, exported)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["imported"] == 0
    assert body["skipped"] == 3
    assert {item["reason"] for item in body["items"]} == {"duplicate"}
    assert body["created_categories"] == []
    assert body["created_tags"] == []
    assert len(client.get("/recipes").json()) == 3


def test_import_into_empty_workspace_creates_full_recipes(client: TestClient) -> None:
    response = import_file(client, export_document(exported_recipe(notes="Melhor no dia seguinte.")))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["imported"] == 1
    assert body["skipped"] == 0
    assert body["created_categories"] == ["Sopas"]
    assert body["created_tags"] == ["tradicional"]
    [item] = body["items"]
    assert item["status"] == "imported"
    recipe = client.get(f"/recipes/{item['recipe_id']}").json()
    assert recipe["title"] == "Caldo verde"
    assert recipe["id"] != "00000000-0000-0000-0000-000000000001"
    assert (recipe["servings"], recipe["prep_minutes"], recipe["cook_minutes"], recipe["rating"]) == (4, 10, 30, 4)
    assert recipe["notes"] == "Melhor no dia seguinte."
    assert [(i["name"], i["quantity"], i["unit"], i["is_header"]) for i in recipe["ingredients"]] == [
        ("Sopa", None, None, True),
        ("Couve", 1, "molho", False),
        ("Batata", 500, "g", False),
    ]
    assert [(s["instruction"], s["duration_minutes"]) for s in recipe["steps"]] == [
        ("Cozer as batatas.", 20),
        ("Juntar a couve.", None),
    ]
    assert [(c["name"], c["color"], c["icon"]) for c in recipe["categories"]] == [("Sopas", "#2F855A", "main")]
    assert [t["name"] for t in recipe["tags"]] == ["tradicional"]


def test_import_reuses_categories_and_tags_by_normalised_name(client: TestClient) -> None:
    category = client.post("/categories", json={"name": "Sopas"}).json()
    tag = client.post("/tags", json={"name": "Tradicional"}).json()
    entry = exported_recipe(categories=[{"name": " sopas "}], tags=[{"name": "tradicional"}, {"name": "Rápido"}])

    body = import_file(client, export_document(entry)).json()

    assert body["created_categories"] == []
    assert body["created_tags"] == ["Rápido"]
    recipe = client.get(f"/recipes/{body['items'][0]['recipe_id']}").json()
    assert [c["id"] for c in recipe["categories"]] == [category["id"]]
    assert tag["id"] in [t["id"] for t in recipe["tags"]]
    assert len(client.get("/categories").json()) == 1


def test_duplicate_needs_same_title_and_same_url_or_ingredients(
    client: TestClient, create_recipe: CreateRecipe
) -> None:
    create_recipe(client, title="Caldo Verde", ingredients=[{"name": "couve"}, {"name": "batata"}])
    create_recipe(client, title="Bolo", source_url="https://example.com/bolo", ingredients=[{"name": "Farinha"}])

    body = import_file(
        client,
        export_document(
            exported_recipe(title="  caldo   verde "),
            exported_recipe(title="Bolo", source_url="https://example.com/bolo/", ingredients=[{"name": "Ovos"}]),
            exported_recipe(title="Caldo verde", ingredients=[{"name": "Couve"}, {"name": "Chouriço"}]),
            exported_recipe(title="Caldo verde à minha moda"),
        ),
    ).json()

    assert [(item["title"], item["status"]) for item in body["items"]] == [
        ("caldo   verde", "skipped"),
        ("Bolo", "skipped"),
        ("Caldo verde", "imported"),
        ("Caldo verde à minha moda", "imported"),
    ]


def test_mode_duplicate_imports_copies_of_existing_recipes(client: TestClient, create_recipe: CreateRecipe) -> None:
    create_recipe(client, title="Arroz de pato", ingredients=[{"name": "Pato"}])
    exported = client.get("/recipes/export").json()

    body = import_file(client, exported, mode="duplicate").json()

    assert (body["imported"], body["skipped"]) == (1, 0)
    assert recipe_titles(client) == ["Arroz de pato", "Arroz de pato"]


def test_unknown_mode_is_rejected(client: TestClient) -> None:
    assert import_file(client, export_document(), mode="overwrite").status_code == 422


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ({"format": "other", "version": 1, "recipes": []}, "não é uma exportação de receitas do Tacho"),
        ({"version": 1, "recipes": []}, "não é uma exportação de receitas do Tacho"),
        ([], "não é uma exportação de receitas do Tacho"),
        ({"format": "tacho.recipe-export", "version": 2, "recipes": []}, "Versão"),
        ({"format": "tacho.recipe-export", "version": "1", "recipes": []}, "Versão"),
        ({"format": "tacho.recipe-export", "version": 1}, "lista de receitas"),
    ],
)
def test_wrong_format_or_version_is_rejected_in_portuguese(client: TestClient, document: Any, message: str) -> None:
    response = import_file(client, document)

    assert response.status_code == 422
    assert message in response.json()["detail"]
    assert recipe_titles(client) == []


def test_more_than_500_recipes_is_rejected(client: TestClient) -> None:
    document = export_document(*[{"title": f"Receita {i}"} for i in range(501)])

    response = import_file(client, document)

    assert response.status_code == 422
    assert "máx. 500" in response.json()["detail"]
    assert recipe_titles(client) == []


def test_identical_recipes_in_the_same_file_are_imported_once(client: TestClient) -> None:
    entry = exported_recipe()

    body = import_file(client, export_document(entry, copy.deepcopy(entry))).json()

    assert (body["imported"], body["skipped"]) == (1, 1)
    assert body["items"][1]["reason"] == "duplicate_in_file"
    assert body["created_categories"] == ["Sopas"]
    assert recipe_titles(client) == ["Caldo verde"]


def test_identical_recipes_in_the_same_file_are_imported_once_even_in_duplicate_mode(client: TestClient) -> None:
    entry = exported_recipe()

    body = import_file(client, export_document(entry, copy.deepcopy(entry)), mode="duplicate").json()

    assert (body["imported"], body["skipped"]) == (1, 1)


def test_duplicates_are_detected_only_within_the_importing_workspace(
    client: TestClient, other_client: TestClient, create_recipe: CreateRecipe
) -> None:
    create_recipe(client, title="Caldo verde", ingredients=[{"name": "Couve"}, {"name": "Batata"}])
    client.post("/categories", json={"name": "Sopas"})
    exported = client.get("/recipes/export").json()

    body = import_file(other_client, exported).json()

    assert (body["imported"], body["skipped"]) == (1, 0)
    assert body["created_categories"] == []
    assert recipe_titles(other_client) == ["Caldo verde"]
    assert recipe_titles(client) == ["Caldo verde"]
    assert import_file(other_client, exported).json()["skipped"] == 1


def test_categories_are_matched_only_within_the_importing_workspace(
    client: TestClient, other_client: TestClient
) -> None:
    client.post("/categories", json={"name": "Sopas"})

    body = import_file(other_client, export_document(exported_recipe())).json()

    assert body["created_categories"] == ["Sopas"]
    assert [c["name"] for c in other_client.get("/categories").json()] == ["Sopas"]
    assert len(client.get("/categories").json()) == 1


def test_malformed_entries_are_reported_and_the_rest_imported(client: TestClient) -> None:
    body = import_file(
        client,
        export_document(
            exported_recipe(title="Boa"),
            {"title": "   "},
            exported_recipe(title="Avaliação fora", rating=9),
            exported_recipe(title="Quantidade enorme", ingredients=[{"name": "Sal", "quantity": 1e12}]),
            "não é um objeto",
            exported_recipe(title="Categoria sem nome", categories=[{"name": ""}]),
        ),
    ).json()

    assert (body["imported"], body["skipped"]) == (1, 5)
    invalid = body["items"][1:]
    assert {item["reason"] for item in invalid} == {"invalid"}
    assert [item["title"] for item in invalid] == [
        "#2",
        "Avaliação fora",
        "Quantidade enorme",
        "#5",
        "Categoria sem nome",
    ]
    assert "rating" in invalid[1]["detail"]
    assert "ingredients.0.quantity" in invalid[2]["detail"]
    assert recipe_titles(client) == ["Boa"]


def test_images_are_not_imported_but_counted(client: TestClient, images_dir: Path) -> None:
    entry = exported_recipe(
        image_path="receitas/00000000-0000-0000-0000-000000000001/capa.webp",
        images=[{"id": "x", "filename": "receitas/x/galeria.webp", "position": 0, "is_cover": False}],
    )

    body = import_file(client, export_document(entry, exported_recipe(title="Sem foto"))).json()

    assert body["images_not_imported"] == 1
    recipe = client.get(f"/recipes/{body['items'][0]['recipe_id']}").json()
    assert recipe["image_path"] is None
    assert recipe["images"] == []
    assert list(images_dir.iterdir()) == []


def test_unexpected_database_error_rolls_back_the_whole_file(client: TestClient) -> None:
    # O psycopg2 recusa NUL em texto — um erro que a validação por receita
    # não apanha, por isso tem de anular também a receita anterior.
    document = export_document(exported_recipe(title="Primeira"), exported_recipe(title="Segunda", notes="a\x00b"))

    with pytest.raises(ValueError, match="NUL"):
        import_file(client, document)

    assert recipe_titles(client) == []
    assert client.get("/categories").json() == []


def test_import_requires_authentication(anon_client: TestClient) -> None:
    assert import_file(anon_client, export_document(exported_recipe())).status_code == 401
