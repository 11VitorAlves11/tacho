import io
import socket
import uuid
from pathlib import Path
from typing import Any

import pytest
import requests
from requests.structures import CaseInsensitiveDict

from app import remote_fetch, tasks
from app.config import Settings
from app.images import save_recipe_image_from_url
from app.remote_fetch import RemoteFetchError, fetch_public_url

HTML = {"text/html"}
PUBLIC_IP = "93.184.215.14"
HOSTS = {
    "recipes.example": PUBLIC_IP,
    "cdn.example": PUBLIC_IP,
    "internal.example": "10.0.0.5",
    "localhost": "127.0.0.1",
}


@pytest.fixture(autouse=True)
def fake_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    def getaddrinfo(host: str, port: int, *args: Any, **kwargs: Any) -> list[Any]:
        address = HOSTS.get(host, host)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))]

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)


def make_response(status: int = 200, body: bytes = b"", headers: dict[str, str] | None = None) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response.headers = CaseInsensitiveDict(headers or {})
    response.raw = io.BytesIO(body)
    response.reason = "test"
    return response


class FakeSession:
    """Responde por URL; regista os pedidos para os testes verificarem que
    nenhum pedido chegou a destinos recusados."""

    def __init__(self, responses: dict[str, requests.Response]) -> None:
        self.responses = responses
        self.requested: list[str] = []

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        assert kwargs["allow_redirects"] is False
        assert kwargs["stream"] is True
        assert kwargs["timeout"]
        self.requested.append(url)
        response = self.responses[url]
        response.url = url
        return response

    def close(self) -> None:
        pass


def fetch(session: FakeSession, url: str, **kwargs: Any) -> remote_fetch.FetchedResponse:
    kwargs.setdefault("allowed_content_types", HTML)
    kwargs.setdefault("max_bytes", 1024)
    return fetch_public_url(url, session=session, **kwargs)  # type: ignore[arg-type]


def test_happy_path_returns_html() -> None:
    session = FakeSession(
        {
            "https://recipes.example/r": make_response(
                body="<p>Açúcar</p>".encode(), headers={"content-type": "text/html; charset=utf-8"}
            )
        }
    )
    page = fetch(session, "https://recipes.example/r")
    assert page.url == "https://recipes.example/r"
    assert page.content_type == "text/html"
    assert page.text() == "<p>Açúcar</p>"


def test_html_without_charset_is_decoded_as_utf8() -> None:
    session = FakeSession(
        {"https://recipes.example/r": make_response(body="Açúcar".encode(), headers={"content-type": "text/html"})}
    )
    assert fetch(session, "https://recipes.example/r").text() == "Açúcar"


def test_follows_public_relative_redirect() -> None:
    session = FakeSession(
        {
            "https://recipes.example/old": make_response(301, headers={"location": "/new"}),
            "https://recipes.example/new": make_response(body=b"<html></html>", headers={"content-type": "text/html"}),
        }
    )
    page = fetch(session, "https://recipes.example/old")
    assert page.url == "https://recipes.example/new"
    assert session.requested == ["https://recipes.example/old", "https://recipes.example/new"]


@pytest.mark.parametrize(
    "location",
    [
        "http://169.254.169.254/latest/meta-data/",
        "http://127.0.0.1:8000/",
        "http://localhost/",
        "http://internal.example/admin",
        "http://[::ffff:127.0.0.1]/",
        "file:///etc/passwd",
    ],
)
def test_redirect_to_non_public_address_is_rejected(location: str) -> None:
    session = FakeSession({"https://recipes.example/r": make_response(302, headers={"location": location})})
    with pytest.raises(ValueError):
        fetch(session, "https://recipes.example/r")
    assert session.requested == ["https://recipes.example/r"]


def test_too_many_redirects_are_rejected() -> None:
    responses = {
        f"https://recipes.example/{i}": make_response(302, headers={"location": f"/{i + 1}"})
        for i in range(remote_fetch.MAX_REDIRECTS + 1)
    }
    session = FakeSession(responses)
    with pytest.raises(RemoteFetchError, match="too many redirects"):
        fetch(session, "https://recipes.example/0")
    assert len(session.requested) == remote_fetch.MAX_REDIRECTS + 1


def test_non_html_content_is_rejected() -> None:
    session = FakeSession(
        {"https://recipes.example/r": make_response(body=b"{}", headers={"content-type": "application/json"})}
    )
    with pytest.raises(RemoteFetchError, match="content type"):
        fetch(session, "https://recipes.example/r")


def test_oversized_body_is_rejected_while_streaming() -> None:
    session = FakeSession(
        {"https://recipes.example/r": make_response(body=b"x" * 2048, headers={"content-type": "text/html"})}
    )
    with pytest.raises(RemoteFetchError, match="too large"):
        fetch(session, "https://recipes.example/r")


def test_oversized_declared_length_is_rejected() -> None:
    session = FakeSession(
        {
            "https://recipes.example/r": make_response(
                body=b"x", headers={"content-type": "text/html", "content-length": "999999"}
            )
        }
    )
    with pytest.raises(RemoteFetchError, match="too large"):
        fetch(session, "https://recipes.example/r")


def test_http_error_status_is_raised() -> None:
    session = FakeSession({"https://recipes.example/r": make_response(500, headers={"content-type": "text/html"})})
    with pytest.raises(requests.HTTPError):
        fetch(session, "https://recipes.example/r")


def test_pinned_connection_connects_to_validated_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    connected: list[tuple[str, int]] = []

    def fake_create_connection(address: tuple[str, int], *args: Any, **kwargs: Any) -> str:
        connected.append(address)
        return "socket"

    monkeypatch.setattr(remote_fetch, "create_connection", fake_create_connection)
    conn = remote_fetch._PinnedHTTPSConnection("recipes.example", 443)
    assert conn._new_conn() == "socket"
    # Liga ao IP já validado (sem nova resolução DNS); o hostname fica
    # para o Host/SNI.
    assert connected == [(PUBLIC_IP, 443)]
    assert conn.host == "recipes.example"


def test_pinned_connection_refuses_private_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_create_connection(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("must not connect")

    monkeypatch.setattr(remote_fetch, "create_connection", fail_create_connection)
    conn = remote_fetch._PinnedHTTPConnection("internal.example", 80)
    with pytest.raises(ValueError, match="private or local"):
        conn._new_conn()


def test_pinned_session_uses_pinned_pools_and_ignores_env_proxies() -> None:
    session = remote_fetch._pinned_session()
    try:
        assert session.trust_env is False
        adapter = session.get_adapter("https://recipes.example/")
        pool = adapter.poolmanager.connection_from_url("https://recipes.example/")
        assert isinstance(pool, remote_fetch._PinnedHTTPSConnectionPool)
        pool = adapter.poolmanager.connection_from_url("http://recipes.example/")
        assert isinstance(pool, remote_fetch._PinnedHTTPConnectionPool)
    finally:
        session.close()


def test_pinned_session_blocks_private_target_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mesmo que a validação prévia fosse contornada (ex. DNS rebinding), a
    própria ligação recusa um destino privado."""
    monkeypatch.setattr(remote_fetch, "validate_remote_url", lambda url: None)

    def fail_create_connection(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("must not connect")

    monkeypatch.setattr(remote_fetch, "create_connection", fail_create_connection)
    with pytest.raises(ValueError, match="private or local"):
        fetch_public_url("http://internal.example/", allowed_content_types=HTML, max_bytes=1024)


def test_scrape_parses_fetched_html_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    html = (
        "<html><head><script type='application/ld+json'>"
        '{"@context": "https://schema.org", "@type": "Recipe", "name": "Bacalhau à Brás",'
        ' "recipeIngredient": ["500 g de bacalhau"], "recipeInstructions": "Misturar tudo."}'
        "</script></head><body></body></html>"
    )
    fetched: list[str] = []

    def fake_fetch(url: str, **kwargs: Any) -> remote_fetch.FetchedResponse:
        fetched.append(url)
        assert kwargs["allowed_content_types"] == tasks.HTML_CONTENT_TYPES
        assert kwargs["max_bytes"] == tasks.MAX_HTML_BYTES
        return remote_fetch.FetchedResponse(
            url="https://recipes.example/bacalhau", content_type="text/html", content=html.encode(), encoding=None
        )

    def no_network(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("recipe-scrapers must not fetch on its own")

    monkeypatch.setattr(tasks, "fetch_public_url", fake_fetch)
    monkeypatch.setattr(requests, "get", no_network)
    scraper = tasks._scrape("https://recipes.example/short")

    assert fetched == ["https://recipes.example/short"]
    assert scraper.title() == "Bacalhau à Brás"
    assert scraper.ingredients() == ["500 g de bacalhau"]
    # O fallback Gemini usa o HTML guardado no scraper.
    assert scraper.page_data == html


def test_recipe_image_download_rejects_redirect_to_private_address(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    session = FakeSession(
        {"https://cdn.example/photo.jpg": make_response(302, headers={"location": "http://10.0.0.1/photo.jpg"})}
    )
    monkeypatch.setattr(remote_fetch, "_pinned_session", lambda: session)
    settings = Settings(
        database_url="postgresql+psycopg2://tacho:tacho@localhost/tacho",
        redis_url="redis://localhost:6379/0",
        images_dir=str(tmp_path),
    )
    assert save_recipe_image_from_url("https://cdn.example/photo.jpg", settings, uuid.uuid4()) is None
    assert session.requested == ["https://cdn.example/photo.jpg"]


def test_import_task_has_time_limits() -> None:
    assert tasks.import_recipe_from_url.soft_time_limit == 60
    assert tasks.import_recipe_from_url.time_limit == 90
