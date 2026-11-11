from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User

CreateRecipe = Callable[..., dict[str, Any]]
LoginAs = Callable[[str, str], TestClient]

MEMBER = {"email": "member@example.com", "password": "member-password-123"}


def members(client: TestClient) -> list[str]:
    response = client.get("/workspace/members")
    assert response.status_code == 200, response.text
    return [member["email"] for member in response.json()]


def test_list_starts_with_the_setup_account(client: TestClient) -> None:
    response = client.get("/workspace/members")

    assert response.status_code == 200
    [owner] = response.json()
    assert (owner["email"], owner["name"]) == ("owner@example.com", "Owner")


def test_added_member_shares_the_workspace(client: TestClient, create_recipe: CreateRecipe, login_as: LoginAs) -> None:
    create_recipe(client, title="Receita partilhada")

    response = client.post("/workspace/members", json=MEMBER)

    assert response.status_code == 201
    assert response.json()["email"] == MEMBER["email"]
    assert members(client) == ["owner@example.com", MEMBER["email"]]
    member_client = login_as(MEMBER["email"], MEMBER["password"])
    assert [r["title"] for r in member_client.get("/recipes").json()] == ["Receita partilhada"]


def test_adding_existing_email_is_conflict(client: TestClient) -> None:
    client.post("/workspace/members", json=MEMBER)

    assert client.post("/workspace/members", json=MEMBER).status_code == 409


def test_cannot_remove_self(client: TestClient) -> None:
    owner_id = client.get("/users/me").json()["id"]

    response = client.delete(f"/workspace/members/{owner_id}")

    assert response.status_code == 400
    assert members(client) == ["owner@example.com"]


def test_removing_member_deletes_the_account(client: TestClient, db: Session) -> None:
    member_id = client.post("/workspace/members", json=MEMBER).json()["id"]

    assert client.delete(f"/workspace/members/{member_id}").status_code == 204

    assert members(client) == ["owner@example.com"]
    assert db.scalars(select(User).where(User.email == MEMBER["email"])).first() is None


def test_members_of_another_workspace_are_invisible_and_cannot_be_removed(
    client: TestClient, other_client: TestClient
) -> None:
    other_id = other_client.get("/users/me").json()["id"]

    assert members(client) == ["owner@example.com"]
    assert members(other_client) == ["other@example.com"]
    assert client.delete(f"/workspace/members/{other_id}").status_code == 404
    assert other_client.get("/users/me").status_code == 200
