"""Limitador de tentativas falhadas (login e configuração inicial) em Redis.

Janela fixa por chave: `INCR` + `EXPIRE NX`, por isso a primeira falha
marca o início da janela e o contador desaparece sozinho no fim. Falha em
aberto: se o Redis não responder, regista um aviso e deixa o pedido seguir
— um reinício do Redis nunca pode impedir alguém de entrar.
"""

import hashlib
import logging
from dataclasses import dataclass
from typing import Protocol

from fastapi import HTTPException, Request
from redis import RedisError
from redis.asyncio import Redis

from app.config import get_settings

logger = logging.getLogger(__name__)

KEY_PREFIX = "tacho:ratelimit"
TOO_MANY_ATTEMPTS_DETAIL = "Demasiadas tentativas. Tenta novamente dentro de alguns minutos."


class RateLimitStore(Protocol):
    async def get(self, name: str) -> bytes | str | None: ...

    async def ttl(self, name: str) -> int: ...

    async def incr(self, name: str) -> int: ...

    async def expire(self, name: str, time: int, nx: bool = False) -> bool: ...

    async def delete(self, *names: str) -> int: ...


@dataclass(frozen=True)
class Limit:
    key: str
    max_failures: int


class RateLimiter:
    def __init__(self, store: RateLimitStore, window_seconds: int) -> None:
        self.store = store
        self.window_seconds = window_seconds

    async def retry_after(self, limits: list[Limit]) -> int | None:
        """Segundos até poder tentar outra vez, ou None se nenhum limite foi atingido."""
        try:
            for limit in limits:
                if limit.max_failures <= 0:
                    continue
                count = await self.store.get(limit.key)
                if count is not None and int(count) >= limit.max_failures:
                    ttl = await self.store.ttl(limit.key)
                    return ttl if ttl > 0 else self.window_seconds
        except (RedisError, OSError) as exc:
            logger.warning("Rate limiter unavailable, allowing request: %s", exc)
        return None

    async def record_failure(self, limits: list[Limit]) -> None:
        try:
            for limit in limits:
                if limit.max_failures <= 0:
                    continue
                await self.store.incr(limit.key)
                await self.store.expire(limit.key, self.window_seconds, nx=True)
        except (RedisError, OSError) as exc:
            logger.warning("Rate limiter unavailable, failure not recorded: %s", exc)

    async def reset(self, limits: list[Limit]) -> None:
        try:
            await self.store.delete(*(limit.key for limit in limits))
        except (RedisError, OSError) as exc:
            logger.warning("Rate limiter unavailable, counters not reset: %s", exc)

    async def enforce(self, limits: list[Limit]) -> None:
        retry_after = await self.retry_after(limits)
        if retry_after is not None:
            raise HTTPException(
                status_code=429,
                detail=TOO_MANY_ATTEMPTS_DETAIL,
                headers={"Retry-After": str(retry_after)},
            )


_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        settings = get_settings()
        # Timeouts curtos: com o Redis em baixo, o login segue (fail-open)
        # sem ficar pendurado à espera da ligação.
        client = Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
        _limiter = RateLimiter(client, settings.login_rate_limit_window_seconds)
    return _limiter


def client_ip(request: Request) -> str:
    """IP já resolvido pelo uvicorn — atrás de um proxy reverso só reflete o
    cliente real se o IP do proxy estiver em `FORWARDED_ALLOW_IPS`."""
    return request.client.host if request.client else "unknown"


def login_limits(ip: str, email: str) -> tuple[Limit, Limit]:
    """(limite por IP, limite por par IP+email). O email entra em hash para
    não guardar endereços em claro no Redis."""
    settings = get_settings()
    email_hash = hashlib.sha256(email.strip().lower().encode()).hexdigest()
    return (
        Limit(f"{KEY_PREFIX}:login:ip:{ip}", settings.login_max_failures_per_ip),
        Limit(f"{KEY_PREFIX}:login:email:{ip}:{email_hash}", settings.login_max_failures_per_email),
    )


def setup_limits(ip: str) -> list[Limit]:
    return [Limit(f"{KEY_PREFIX}:setup:ip:{ip}", get_settings().login_max_failures_per_ip)]
