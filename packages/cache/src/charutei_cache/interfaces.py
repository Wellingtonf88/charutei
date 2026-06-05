"""Interfaces de cache.

`KVBackend` é o armazenamento chave-valor (in-memory hoje, Redis na fundação real).
`VectorIndex` é a forma estrutural mínima que o cache semântico precisa — definida aqui
(não importada de knowledge) para evitar acoplamento; qualquer `VectorRepository` a satisfaz.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class KVBackend(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None: ...

    async def delete(self, key: str) -> None: ...


@runtime_checkable
class VectorIndex(Protocol):
    async def upsert(
        self,
        kind: str,
        item_id: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None: ...

    async def ann_search(
        self,
        kind: str,
        embedding: list[float],
        k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[str, float]]: ...
