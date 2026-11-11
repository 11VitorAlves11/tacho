import socket
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.config import Settings
from app.images import resolve_image_path
from app.remote_fetch import validate_remote_url


def settings(tmp_path: Path, **overrides) -> Settings:
    values = {
        "database_url": "postgresql+psycopg2://tacho:tacho@localhost/tacho",
        "redis_url": "redis://localhost:6379/0",
        "images_dir": str(tmp_path),
    }
    values.update(overrides)
    return Settings(**values)


def test_production_rejects_default_auth_secret(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="AUTH_SECRET"):
        settings(tmp_path, environment="production", auth_secret="dev-secret-change-me-in-production")


def test_image_path_cannot_escape_media_root(tmp_path: Path) -> None:
    with pytest.raises(HTTPException):
        resolve_image_path("../secret", settings(tmp_path))


@pytest.mark.parametrize("url", ["http://127.0.0.1/a", "http://[::1]/a"])
def test_remote_import_rejects_loopback(url: str) -> None:
    with pytest.raises(ValueError, match="private or local"):
        validate_remote_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://[::ffff:127.0.0.1]/a",
        "http://[::ffff:169.254.169.254]/a",
        "http://[::ffff:10.0.0.1]/a",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.1.2.3/a",
        "http://192.168.1.1/a",
        "http://0.0.0.0/a",
        "http://224.0.0.1/a",
        "http://[fe80::1]/a",
        "http://[2002:7f00:1::]/a",
    ],
)
def test_remote_import_rejects_non_public_addresses(url: str) -> None:
    with pytest.raises(ValueError, match="private or local"):
        validate_remote_url(url)


@pytest.mark.parametrize("url", ["ftp://example.com/a", "file:///etc/passwd", "http:///a"])
def test_remote_import_rejects_non_http_urls(url: str) -> None:
    with pytest.raises(ValueError, match="HTTP"):
        validate_remote_url(url)


@pytest.mark.parametrize(
    ("url", "expected_port"),
    [("http://example.com/a", 80), ("https://example.com/a", 443), ("http://example.com:8080/a", 8080)],
)
def test_remote_import_resolves_with_scheme_default_port(
    monkeypatch: pytest.MonkeyPatch, url: str, expected_port: int
) -> None:
    calls: list[tuple[str, int]] = []

    def fake_getaddrinfo(host: str, port: int, *args, **kwargs):
        calls.append((host, port))
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.215.14", port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    validate_remote_url(url)
    assert calls == [("example.com", expected_port)]


def test_remote_import_rejects_hostname_with_any_private_address(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_getaddrinfo(host: str, port: int, *args, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.215.14", port)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(ValueError, match="private or local"):
        validate_remote_url("https://rebind.example/a")
