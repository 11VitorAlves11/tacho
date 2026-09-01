import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from urllib.parse import urlencode

import jwt
import requests

from app.config import Settings

STATE_TTL_MINUTES = 10
ALLOWED_ID_TOKEN_ALGORITHMS = {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}


class OIDCError(ValueError):
    pass


@lru_cache(maxsize=8)
def discover(issuer: str) -> dict:
    url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise OIDCError("Não foi possível obter o discovery OIDC") from exc
    document = response.json()
    if document.get("issuer") != issuer.rstrip("/"):
        raise OIDCError("O issuer devolvido pelo discovery não corresponde à configuração")
    for field in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
        if not document.get(field):
            raise OIDCError(f"Discovery OIDC sem {field}")
    return document


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def create_authorization(settings: Settings, next_path: str = "/") -> tuple[str, str]:
    if not settings.oidc_enabled or not settings.oidc_issuer or not settings.oidc_client_id:
        raise OIDCError("OIDC não está configurado")
    document = discover(settings.oidc_issuer.rstrip("/"))
    verifier = _b64url(secrets.token_bytes(48))
    nonce = secrets.token_urlsafe(32)
    state_id = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    state_token = jwt.encode(
        {
            "state": state_id,
            "nonce": nonce,
            "verifier": verifier,
            "next": next_path if next_path.startswith("/") and not next_path.startswith("//") else "/",
            "iat": now,
            "exp": now + timedelta(minutes=STATE_TTL_MINUTES),
        },
        settings.auth_secret,
        algorithm="HS256",
    )
    params = {
        "response_type": "code",
        "client_id": settings.oidc_client_id,
        "redirect_uri": settings.oidc_redirect_uri,
        "scope": settings.oidc_scopes,
        "state": state_id,
        "nonce": nonce,
        "code_challenge": _b64url(hashlib.sha256(verifier.encode()).digest()),
        "code_challenge_method": "S256",
    }
    return f"{document['authorization_endpoint']}?{urlencode(params)}", state_token


def decode_state(settings: Settings, state_token: str, returned_state: str) -> dict:
    try:
        payload = jwt.decode(state_token, settings.auth_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise OIDCError("Estado OIDC inválido ou expirado") from exc
    if not secrets.compare_digest(str(payload.get("state", "")), returned_state):
        raise OIDCError("Estado OIDC não corresponde ao pedido inicial")
    return payload


def exchange_code(settings: Settings, code: str, verifier: str) -> dict:
    if not settings.oidc_issuer or not settings.oidc_client_id or not settings.oidc_redirect_uri:
        raise OIDCError("OIDC não está configurado")
    document = discover(settings.oidc_issuer.rstrip("/"))
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.oidc_redirect_uri,
        "client_id": settings.oidc_client_id,
        "code_verifier": verifier,
    }
    if settings.oidc_client_secret:
        data["client_secret"] = settings.oidc_client_secret
    try:
        response = requests.post(document["token_endpoint"], data=data, timeout=15)
    except requests.RequestException as exc:
        raise OIDCError("Não foi possível contactar o token endpoint OIDC") from exc
    if not response.ok:
        raise OIDCError("O fornecedor OIDC recusou a troca do código")
    tokens = response.json()
    if not tokens.get("id_token"):
        raise OIDCError("O fornecedor OIDC não devolveu id_token")
    return tokens


def validate_id_token(settings: Settings, id_token: str, nonce: str) -> dict:
    if not settings.oidc_issuer or not settings.oidc_client_id:
        raise OIDCError("OIDC não está configurado")
    document = discover(settings.oidc_issuer.rstrip("/"))
    try:
        header = jwt.get_unverified_header(id_token)
    except jwt.PyJWTError as exc:
        raise OIDCError("Cabeçalho do id_token inválido") from exc
    algorithm = header.get("alg")
    if algorithm not in ALLOWED_ID_TOKEN_ALGORITHMS:
        raise OIDCError("Algoritmo do id_token não permitido")
    try:
        response = requests.get(document["jwks_uri"], timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise OIDCError("Não foi possível obter as chaves OIDC") from exc
    keys = response.json().get("keys", [])
    jwk = next((key for key in keys if key.get("kid") == header.get("kid")), None)
    if jwk is None:
        raise OIDCError("Chave de assinatura do id_token não encontrada")
    try:
        claims = jwt.decode(
            id_token,
            key=jwt.PyJWK.from_dict(jwk).key,
            algorithms=[algorithm],
            audience=settings.oidc_client_id,
            issuer=settings.oidc_issuer.rstrip("/"),
        )
    except jwt.PyJWTError as exc:
        raise OIDCError("id_token inválido") from exc
    if not secrets.compare_digest(str(claims.get("nonce", "")), nonce):
        raise OIDCError("Nonce OIDC inválido")
    if not claims.get("sub"):
        raise OIDCError("id_token sem subject")
    return claims
