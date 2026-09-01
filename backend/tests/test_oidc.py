from urllib.parse import parse_qs, urlparse

import pytest

from app.config import Settings
from app.oidc import OIDCError, create_authorization, decode_state


def oidc_settings() -> Settings:
    return Settings(
        database_url="postgresql+psycopg2://tacho:tacho@localhost/tacho",
        redis_url="redis://localhost:6379/0",
        auth_secret="test-secret-long-enough-for-signed-state",
        oidc_issuer="https://identity.example.com",
        oidc_client_id="tacho",
        oidc_redirect_uri="https://tacho.example.com/auth/oidc/callback",
    )


def test_oidc_authorization_uses_pkce_state_and_nonce(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.oidc.discover",
        lambda issuer: {
            "authorization_endpoint": f"{issuer}/authorize",
            "token_endpoint": f"{issuer}/token",
            "jwks_uri": f"{issuer}/jwks",
        },
    )
    settings = oidc_settings()
    url, state_token = create_authorization(settings, "/planeamento")
    query = parse_qs(urlparse(url).query)

    assert query["response_type"] == ["code"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["nonce"]
    state = decode_state(settings, state_token, query["state"][0])
    assert state["next"] == "/planeamento"
    assert state["verifier"]


def test_oidc_state_rejects_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.oidc.discover",
        lambda issuer: {
            "authorization_endpoint": f"{issuer}/authorize",
            "token_endpoint": f"{issuer}/token",
            "jwks_uri": f"{issuer}/jwks",
        },
    )
    settings = oidc_settings()
    _, state_token = create_authorization(settings)

    with pytest.raises(OIDCError, match="não corresponde"):
        decode_state(settings, state_token, "outro-estado")


def test_production_oidc_requires_https() -> None:
    with pytest.raises(ValueError, match="OIDC_ISSUER"):
        Settings(
            database_url="postgresql+psycopg2://tacho:tacho@localhost/tacho",
            redis_url="redis://localhost:6379/0",
            environment="production",
            auth_secret="a" * 32,
            oidc_issuer="http://identity.example.com",
        )
