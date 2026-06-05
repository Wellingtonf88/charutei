"""Cache exato (degrau 1a): hit por consulta normalizada idêntica.

Namespacedo por capability e **versão do KG** — quando o conhecimento muda, a versão sobe e
as chaves antigas deixam de ser consultadas (invalidação sem varredura).
"""

from __future__ import annotations

import hashlib
import re

from charutei_contracts import CascadeResult, Tier

from charutei_cache.interfaces import KVBackend


def normalize_query(text: str) -> str:
    """Minúsculas, sem acentuação de espaços, espaços colapsados. Base das chaves de cache."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _key(capability: str, kg_version: int, text: str) -> str:
    digest = hashlib.sha256(normalize_query(text).encode("utf-8")).hexdigest()
    return f"exact:{capability}:v{kg_version}:{digest}"


class ExactCache:
    def __init__(self, kv: KVBackend, ttl_seconds: int | None = 3600) -> None:
        self._kv = kv
        self._ttl = ttl_seconds

    async def get(self, capability: str, kg_version: int, text: str) -> CascadeResult | None:
        raw = await self._kv.get(_key(capability, kg_version, text))
        if raw is None:
            return None
        result = CascadeResult.model_validate_json(raw)
        # Hit de cache é sempre degrau 1, custo ~0 — sobrescreve o tier original.
        return result.model_copy(update={"tier_resolved": Tier.CACHE, "cost_usd": 0.0})

    async def set(self, capability: str, kg_version: int, text: str, result: CascadeResult) -> None:
        await self._kv.set(_key(capability, kg_version, text), result.model_dump_json(), self._ttl)
