import uuid
from types import SimpleNamespace

import pytest
from fake_redis import FakeRedis
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import get_user_manager
from app.database import get_db
from app.rate_limit import TOO_MANY_ATTEMPTS_DETAIL, RateLimiter, get_rate_limiter
from app.routers import auth as auth_router
from app.routers import login as login_router

WINDOW = 900
PASSWORD = "correct-password"


class FakeUserManager:
    def __init__(self) -> None:
        self.user = SimpleNamespace(id=uuid.uuid4(), is_active=True)

    async def authenticate(self, credentials):
        return self.user if credentials.password == PASSWORD else None

    async def on_after_login(self, user, request, response) -> None:
        return None


class FakeSession:
    def scalar(self, _statement) -> int:
        return 1


@pytest.fixture
def store() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def client(store: FakeRedis) -> TestClient:
    app = FastAPI()
    app.include_router(login_router.router, prefix="/auth/cookie")
    app.include_router(auth_router.router)
    manager = FakeUserManager()
    app.dependency_overrides[get_user_manager] = lambda: manager
    app.dependency_overrides[get_rate_limiter] = lambda: RateLimiter(store, WINDOW)
    app.dependency_overrides[get_db] = lambda: FakeSession()
    return TestClient(app)


def login(client: TestClient, email: str = "ana@example.com", password: str = "wrong"):
    return client.post("/auth/cookie/login", data={"username": email, "password": password})


def test_login_succeeds_and_sets_session_cookie(client: TestClient) -> None:
    response = login(client, password=PASSWORD)
    assert response.status_code == 204
    assert "tacho_session" in response.headers["set-cookie"]


def test_failed_logins_are_allowed_until_the_email_limit(client: TestClient) -> None:
    for _ in range(5):
        assert login(client).status_code == 400
    blocked = login(client, password=PASSWORD)
    assert blocked.status_code == 429
    assert blocked.json() == {"detail": TOO_MANY_ATTEMPTS_DETAIL}
    assert blocked.headers["Retry-After"] == str(WINDOW)


def test_ip_limit_applies_across_emails(client: TestClient) -> None:
    for index in range(10):
        assert login(client, email=f"user{index}@example.com").status_code == 400
    assert login(client, email="other@example.com", password=PASSWORD).status_code == 429


def test_email_matching_ignores_case(client: TestClient) -> None:
    for _ in range(5):
        login(client, email="Ana@Example.com")
    assert login(client, email="ana@example.com").status_code == 429


def test_successful_login_resets_the_email_counter(client: TestClient, store: FakeRedis) -> None:
    for _ in range(4):
        login(client)
    assert login(client, password=PASSWORD).status_code == 204
    assert not any(":login:email:" in key for key in store.values)
    for _ in range(4):
        assert login(client).status_code == 400


def test_login_fails_open_when_redis_is_down(client: TestClient, store: FakeRedis) -> None:
    store.broken = True
    for _ in range(12):
        assert login(client).status_code == 400
    assert login(client, password=PASSWORD).status_code == 204


def test_zero_limit_disables_the_check(store: FakeRedis, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "login_max_failures_per_email", 0)
    monkeypatch.setattr(get_settings(), "login_max_failures_per_ip", 0)
    app = FastAPI()
    app.include_router(login_router.router, prefix="/auth/cookie")
    app.dependency_overrides[get_user_manager] = FakeUserManager
    app.dependency_overrides[get_rate_limiter] = lambda: RateLimiter(store, WINDOW)
    client = TestClient(app)
    for _ in range(12):
        assert login(client).status_code == 400
    assert store.values == {}


def test_logout_route_is_still_mounted(client: TestClient) -> None:
    assert client.post("/auth/cookie/logout").status_code == 401


def test_rejected_setup_attempts_are_limited_per_ip(client: TestClient) -> None:
    payload = {"name": "Ana", "email": "ana@example.com", "password": "password123"}
    for _ in range(10):
        assert client.post("/setup", json=payload).status_code == 403
    blocked = client.post("/setup", json=payload)
    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == str(WINDOW)
