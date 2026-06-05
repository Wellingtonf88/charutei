"""Backends de KV: in-memory (testes/CI) e Redis (fundação real)."""

from __future__ import annotations

import time


class InMemoryKV:
    """KV em dicionário com TTL. Para testes e dev sem Redis."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float | None]] = {}

    async def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at is not None and time.monotonic() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        expires_at = time.monotonic() + ttl_seconds if ttl_seconds else None
        self._store[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)


class RedisKV:
    """KV sobre Redis (extra `redis`). Mesma interface que InMemoryKV.

    Recebe um cliente `redis.asyncio.Redis` já configurado (injeção de dependência),
    para que o wiring (DSN, pool) fique no serviço, não no cache.
    """

    def __init__(self, client: object) -> None:
        self._client = client

    async def get(self, key: str) -> str | None:
        value = await self._client.get(key)  # type: ignore[attr-defined]
        if value is None:
            return None
        return value.decode() if isinstance(value, bytes) else str(value)

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        await self._client.set(key, value, ex=ttl_seconds)  # type: ignore[attr-defined]

    async def delete(self, key: str) -> None:
        await self._client.delete(key)  # type: ignore[attr-defined]
