from redis.exceptions import ConnectionError as RedisConnectionError


class FakeRedis:
    """Subconjunto em memória dos comandos usados por `RateLimiter`."""

    def __init__(self, broken: bool = False) -> None:
        self.values: dict[str, int] = {}
        self.ttls: dict[str, int] = {}
        self.broken = broken

    def _check(self) -> None:
        if self.broken:
            raise RedisConnectionError("Connection refused")

    async def get(self, name: str) -> bytes | None:
        self._check()
        return str(self.values[name]).encode() if name in self.values else None

    async def ttl(self, name: str) -> int:
        self._check()
        return self.ttls.get(name, -1) if name in self.values else -2

    async def incr(self, name: str) -> int:
        self._check()
        self.values[name] = self.values.get(name, 0) + 1
        return self.values[name]

    async def expire(self, name: str, time: int, nx: bool = False) -> bool:
        self._check()
        if nx and name in self.ttls:
            return False
        self.ttls[name] = time
        return True

    async def delete(self, *names: str) -> int:
        self._check()
        removed = [name for name in names if self.values.pop(name, None) is not None]
        for name in names:
            self.ttls.pop(name, None)
        return len(removed)
