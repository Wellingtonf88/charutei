"""Cache semântico (degrau 1b): hit por consulta semanticamente equivalente.

Embeda a consulta normalizada, busca o vizinho mais próximo e aceita o hit só acima de um
**threshold conservador** (evita falso positivo → resposta errada). Namespaceado por
capability + versão do KG (invalidação automática quando o conhecimento muda).
"""

from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable

from charutei_contracts import CascadeResult, Tier

from charutei_cache.exact import normalize_query
from charutei_cache.interfaces import KVBackend, VectorIndex

EmbedFn = Callable[[str], Awaitable[list[float]]]


class SemanticCache:
    def __init__(
        self,
        index: VectorIndex,
        kv: KVBackend,
        embed: EmbedFn,
        *,
        threshold: float = 0.95,
        ttl_seconds: int | None = 3600,
    ) -> None:
        self._index = index
        self._kv = kv
        self._embed = embed
        self._threshold = threshold
        self._ttl = ttl_seconds

    @staticmethod
    def _kind(capability: str, kg_version: int) -> str:
        return f"sem:{capability}:v{kg_version}"

    @staticmethod
    def _val_key(item_id: str) -> str:
        return f"semval:{item_id}"

    async def get(self, capability: str, kg_version: int, text: str) -> CascadeResult | None:
        embedding = await self._embed(normalize_query(text))
        hits = await self._index.ann_search(self._kind(capability, kg_version), embedding, k=1)
        if not hits:
            return None
        item_id, score = hits[0]
        if score < self._threshold:
            return None
        raw = await self._kv.get(self._val_key(item_id))
        if raw is None:
            return None
        result = CascadeResult.model_validate_json(raw)
        return result.model_copy(update={"tier_resolved": Tier.CACHE, "cost_usd": 0.0})

    async def set(self, capability: str, kg_version: int, text: str, result: CascadeResult) -> None:
        norm = normalize_query(text)
        item_id = hashlib.sha256(f"{capability}:{kg_version}:{norm}".encode()).hexdigest()
        embedding = await self._embed(norm)
        await self._index.upsert(self._kind(capability, kg_version), item_id, embedding)
        await self._kv.set(self._val_key(item_id), result.model_dump_json(), self._ttl)
