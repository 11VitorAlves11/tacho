"""Pedidos HTTP a URLs fornecidos pelos utilizadores (importação de receitas
e das respetivas fotos), com proteção contra SSRF.

Política (ver SECURITY.md):
- só HTTP(S) para endereços públicos — o hostname é resolvido e qualquer
  endereço privado, loopback, link-local, reservado, multicast ou não
  especificado é rejeitado (incluindo IPv4 embutido em IPv6, ex.
  `::ffff:127.0.0.1`);
- redirects seguidos à mão, no máximo `MAX_REDIRECTS`, com cada salto
  validado de novo;
- a ligação TCP é feita ao IP que acabou de ser validado (o hostname não é
  resolvido uma segunda vez pelo `urllib3`), o que fecha a janela de DNS
  rebinding entre validação e ligação; o `Host` e o SNI/verificação TLS
  continuam a usar o hostname original;
- timeouts de ligação/leitura, prazo total por pedido, tamanho máximo do
  corpo e lista de content-types aceites.
"""

import ipaddress
import socket
import time
from collections.abc import Collection
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter
from requests.utils import get_encoding_from_headers
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from urllib3.exceptions import NewConnectionError
from urllib3.util.connection import create_connection

MAX_REDIRECTS = 5
TIMEOUT = (5, 15)  # (ligação, leitura entre bytes) em segundos
TOTAL_DEADLINE_SECONDS = 30.0
USER_AGENT = "Mozilla/5.0 (compatible; Tacho recipe importer)"
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


class RemoteFetchError(Exception):
    """Pedido recusado ou resposta inaceitável (ver política acima)."""


def _embedded_ipv4(ip: IPAddress) -> ipaddress.IPv4Address | None:
    if isinstance(ip, ipaddress.IPv6Address):
        return ip.ipv4_mapped or ip.sixtofour
    return None


def is_public_address(ip: IPAddress) -> bool:
    embedded = _embedded_ipv4(ip)
    if embedded is not None and not is_public_address(embedded):
        return False
    return ip.is_global and not (
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified
    )


def resolve_public_addresses(hostname: str, port: int) -> list[str]:
    """Resolve `hostname` e devolve os endereços, só se forem todos públicos —
    basta um privado para recusar (um atacante controla o DNS do domínio)."""
    try:
        infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("URL hostname could not be resolved") from exc
    addresses = list(dict.fromkeys(str(info[4][0]) for info in infos))
    if not addresses:
        raise ValueError("URL hostname could not be resolved")
    for address in addresses:
        # `%scope` de endereços IPv6 link-local não é aceite por ip_address.
        if not is_public_address(ipaddress.ip_address(address.split("%", 1)[0])):
            raise ValueError("URLs resolving to private or local networks are not accepted")
    return addresses


def validate_remote_url(url: str) -> None:
    """Reject URLs that resolve to local or otherwise non-public addresses."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("only public HTTP(S) URLs are accepted")
    default_port = 443 if parsed.scheme == "https" else 80
    resolve_public_addresses(parsed.hostname, parsed.port or default_port)


class _PinnedConnectionMixin:
    """Resolve, valida e liga ao IP validado no mesmo passo — o `urllib3`
    normalmente passa o hostname a `create_connection`, que voltaria a
    resolvê-lo (e um DNS malicioso podia responder com outro IP)."""

    _dns_host: str
    port: int
    timeout: Any
    source_address: tuple[str, int] | None
    socket_options: Any

    def _new_conn(self) -> socket.socket:
        addresses = resolve_public_addresses(self._dns_host, self.port)
        last_error: OSError | None = None
        for address in addresses:
            try:
                return create_connection(
                    (address, self.port),
                    self.timeout,
                    source_address=self.source_address,
                    socket_options=self.socket_options,
                )
            except OSError as exc:
                last_error = exc
        raise NewConnectionError(self, f"Failed to establish a new connection: {last_error}")


class _PinnedHTTPConnection(_PinnedConnectionMixin, HTTPConnection):
    pass


class _PinnedHTTPSConnection(_PinnedConnectionMixin, HTTPSConnection):
    pass


class _PinnedHTTPConnectionPool(HTTPConnectionPool):
    ConnectionCls = _PinnedHTTPConnection


class _PinnedHTTPSConnectionPool(HTTPSConnectionPool):
    ConnectionCls = _PinnedHTTPSConnection


class _PinnedAdapter(HTTPAdapter):
    def init_poolmanager(self, *args: Any, **kwargs: Any) -> None:
        super().init_poolmanager(*args, **kwargs)
        self.poolmanager.pool_classes_by_scheme = {
            "http": _PinnedHTTPConnectionPool,
            "https": _PinnedHTTPSConnectionPool,
        }


def _pinned_session() -> requests.Session:
    session = requests.Session()
    # Sem proxies/.netrc do ambiente: um proxy faria a ligação em nosso nome
    # e a validação acima deixaria de se aplicar ao destino real.
    session.trust_env = False
    adapter = _PinnedAdapter(max_retries=0)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


@dataclass(frozen=True)
class FetchedResponse:
    url: str
    content_type: str
    content: bytes
    encoding: str | None

    def text(self) -> str:
        try:
            return self.content.decode(self.encoding or "utf-8", errors="replace")
        except LookupError:
            return self.content.decode("utf-8", errors="replace")


def _read_capped(response: requests.Response, max_bytes: int, deadline: float) -> bytes:
    declared = response.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > max_bytes:
        raise RemoteFetchError("response body too large")
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(chunk_size=65536):
        total += len(chunk)
        if total > max_bytes:
            raise RemoteFetchError("response body too large")
        if time.monotonic() > deadline:
            raise RemoteFetchError("response took too long")
        chunks.append(chunk)
    return b"".join(chunks)


def _encoding(response: requests.Response) -> str | None:
    # Sem charset explícito o `requests` assume ISO-8859-1 para text/*, o que
    # estragava acentos em páginas UTF-8; nesse caso fica a cargo do chamador.
    if "charset" not in response.headers.get("content-type", "").lower():
        return None
    return get_encoding_from_headers(response.headers)


def fetch_public_url(
    url: str,
    *,
    allowed_content_types: Collection[str],
    max_bytes: int,
    session: requests.Session | None = None,
) -> FetchedResponse:
    """Descarrega `url` segundo a política do módulo. Levanta `ValueError`
    para destinos não públicos, `RemoteFetchError` para respostas recusadas
    e `requests.RequestException` para erros de rede/HTTP."""
    own_session = session is None
    http = session or _pinned_session()
    deadline = time.monotonic() + TOTAL_DEADLINE_SECONDS
    current = url
    try:
        for _ in range(MAX_REDIRECTS + 1):
            validate_remote_url(current)
            with http.get(
                current,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT,
                stream=True,
                allow_redirects=False,
            ) as response:
                location = response.headers.get("location")
                if response.status_code in _REDIRECT_STATUSES and location:
                    current = urljoin(current, location)
                    continue
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                if content_type not in allowed_content_types:
                    raise RemoteFetchError(f"unexpected content type: {content_type or 'none'}")
                content = _read_capped(response, max_bytes, deadline)
                return FetchedResponse(
                    url=current, content_type=content_type, content=content, encoding=_encoding(response)
                )
        raise RemoteFetchError("too many redirects")
    finally:
        if own_session:
            http.close()
