import uuid
from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app import crud
from app.auth import current_active_user
from app.database import get_db
from app.deps import get_workspace_id
from app.main import app


def compiled(sort: crud.RecipeSort) -> list[str]:
    return [str(clause.compile(dialect=postgresql.dialect())) for clause in crud._recipe_order_by(sort)]


@pytest.mark.parametrize(
    ("sort", "expected"),
    [
        ("title", ["recipes.title ASC"]),
        ("newest", ["recipes.created_at DESC", "recipes.title ASC"]),
        ("updated", ["recipes.updated_at DESC", "recipes.title ASC"]),
        ("rating", ["recipes.rating DESC NULLS LAST", "recipes.title ASC"]),
        ("least_recently_made", ["recipes.last_made_at ASC NULLS FIRST", "recipes.title ASC"]),
    ],
)
def test_recipe_order_by_compiles_to_expected_sql(sort: crud.RecipeSort, expected: list[str]) -> None:
    assert compiled(sort) == expected


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, dict]]:
    captured: dict = {}

    def fake_list_recipes(db, workspace_id, user_id, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(crud, "list_recipes", fake_list_recipes)
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[get_workspace_id] = lambda: uuid.uuid4()
    app.dependency_overrides[current_active_user] = lambda: SimpleNamespace(id=uuid.uuid4())
    try:
        yield TestClient(app), captured
    finally:
        app.dependency_overrides.clear()


def test_list_recipes_defaults_to_title_sort(client: tuple[TestClient, dict]) -> None:
    test_client, captured = client
    response = test_client.get("/recipes")
    assert response.status_code == 200
    assert captured["sort"] == "title"


def test_list_recipes_forwards_sort(client: tuple[TestClient, dict]) -> None:
    test_client, captured = client
    response = test_client.get("/recipes", params={"sort": "least_recently_made"})
    assert response.status_code == 200
    assert captured["sort"] == "least_recently_made"


def test_list_recipes_rejects_unknown_sort(client: tuple[TestClient, dict]) -> None:
    test_client, captured = client
    response = test_client.get("/recipes", params={"sort": "bogus"})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "sort"]
    assert captured == {}
