from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import DEFAULT_WORKSPACE_ID
from app.models import User, WorkspaceMember

SETUP_PAYLOAD = {"name": "Owner", "email": "owner@example.com", "password": "owner-password-123"}


def test_setup_status_reports_needs_setup_on_empty_database(anon_client: TestClient) -> None:
    response = anon_client.get("/setup/status")

    assert response.status_code == 200
    assert response.json() == {"needs_setup": True}


def test_first_setup_creates_account_in_seeded_workspace(anon_client: TestClient, db: Session) -> None:
    response = anon_client.post("/setup", json=SETUP_PAYLOAD)

    assert response.status_code == 201
    assert response.json() == {"needs_setup": False}
    assert anon_client.get("/setup/status").json() == {"needs_setup": False}
    user = db.scalars(select(User)).one()
    assert user.email == "owner@example.com"
    assert user.name == "Owner"
    membership = db.scalars(select(WorkspaceMember)).one()
    assert membership.user_id == user.id
    assert membership.workspace_id == DEFAULT_WORKSPACE_ID


def test_second_setup_is_forbidden(anon_client: TestClient) -> None:
    assert anon_client.post("/setup", json=SETUP_PAYLOAD).status_code == 201

    response = anon_client.post(
        "/setup", json={"name": "Intruder", "email": "intruder@example.com", "password": "intruder-password"}
    )

    assert response.status_code == 403


def test_setup_account_can_log_in_and_read_profile(anon_client: TestClient) -> None:
    anon_client.post("/setup", json=SETUP_PAYLOAD)

    login = anon_client.post(
        "/auth/cookie/login", data={"username": SETUP_PAYLOAD["email"], "password": SETUP_PAYLOAD["password"]}
    )

    assert login.status_code == 204
    assert "tacho_session" in anon_client.cookies
    me = anon_client.get("/users/me")
    assert me.status_code == 200
    assert me.json()["email"] == SETUP_PAYLOAD["email"]
    assert me.json()["name"] == "Owner"


def test_login_with_wrong_password_is_rejected(anon_client: TestClient) -> None:
    anon_client.post("/setup", json=SETUP_PAYLOAD)

    response = anon_client.post(
        "/auth/cookie/login", data={"username": SETUP_PAYLOAD["email"], "password": "wrong-password"}
    )

    assert response.status_code == 400
    assert "tacho_session" not in anon_client.cookies


def test_protected_endpoints_require_a_session(anon_client: TestClient) -> None:
    assert anon_client.get("/recipes").status_code == 401
    assert anon_client.get("/workspace/members").status_code == 401
