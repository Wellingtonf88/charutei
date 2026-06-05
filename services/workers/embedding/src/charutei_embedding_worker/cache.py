"""Cache de embedding por hash de conteúdo — nunca re-embeda conteúdo inalterado.

Chave = sha256 do conteúdo. Em escala, o job offline usa Batch API (-50%); aqui o ganho é
evitar a chamada ao provider quando o conteúdo já foi embedado.
"""

from __future__ import annotations

import hashlib
import json

from charutei_cache.interfaces import KVBackend


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class ContentEmbeddingCache:
    def __init__(self, kv: KVBackend) -> None:
        self._kv = kv

    async def get(self, content: str) -> list[float] | None:
        raw = await self._kv.get(f"emb:{content_hash(content)}")
        if raw is None:
            return None
        loaded: list[float] = json.loads(raw)
        return loaded

    async def put(self, content: str, embedding: list[float]) -> None:
        await self._kv.set(f"emb:{content_hash(content)}", json.dumps(embedding))
