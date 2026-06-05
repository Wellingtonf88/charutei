"""Testes do cache exato e semântico, incluindo invalidação por versão do KG."""

import math

from charutei_cache import ExactCache, InMemoryKV, SemanticCache
from charutei_contracts import CascadeResult, Tier


def _result(answer: str) -> CascadeResult:
    return CascadeResult(answer=answer, tier_resolved=Tier.MEDIUM, cost_usd=0.004)


# ---- embedding fake local (bag-of-words normalizado) p/ o cache semântico ----
async def _embed(text: str) -> list[float]:
    dim = 32
    vec = [0.0] * dim
    for tok in text.lower().split():
        vec[hash(tok) % dim] += 1.0
    norm = math.sqrt(sum(x * x for x in vec))
    return [x / norm for x in vec] if norm else vec


class _Index:
    """VectorIndex mínimo em memória para o teste."""

    def __init__(self) -> None:
        self.data: dict[str, list[tuple[str, list[float]]]] = {}

    async def upsert(self, kind, item_id, embedding, metadata=None):  # type: ignore[no-untyped-def]
        self.data.setdefault(kind, []).append((item_id, embedding))

    async def ann_search(self, kind, embedding, k=5, filters=None):  # type: ignore[no-untyped-def]
        out = []
        for item_id, vec in self.data.get(kind, []):
            dot = sum(a * b for a, b in zip(embedding, vec, strict=True))
            out.append((item_id, dot))
        out.sort(key=lambda p: p[1], reverse=True)
        return out[:k]


async def test_exact_cache_hit_marks_tier_cache() -> None:
    cache = ExactCache(InMemoryKV())
    await cache.set("assistant", 1, "Com o que harmoniza?", _result("rum"))

    hit = await cache.get("assistant", 1, "  com o QUE   harmoniza? ")  # normalização
    assert hit is not None
    assert hit.answer == "rum"
    assert hit.tier_resolved == Tier.CACHE
    assert hit.cost_usd == 0.0


async def test_exact_cache_invalidated_by_kg_version() -> None:
    cache = ExactCache(InMemoryKV())
    await cache.set("assistant", 1, "pergunta", _result("v1"))
    assert await cache.get("assistant", 2, "pergunta") is None  # versão nova → miss


async def test_semantic_cache_hits_on_paraphrase() -> None:
    cache = SemanticCache(_Index(), InMemoryKV(), _embed, threshold=0.8)
    await cache.set("assistant", 1, "com o que harmoniza o cohiba", _result("rum"))

    hit = await cache.get("assistant", 1, "harmoniza com o que o cohiba")  # mesmas palavras
    assert hit is not None
    assert hit.tier_resolved == Tier.CACHE


async def test_semantic_cache_misses_below_threshold() -> None:
    cache = SemanticCache(_Index(), InMemoryKV(), _embed, threshold=0.99)
    await cache.set("assistant", 1, "harmonização do cohiba robustos", _result("rum"))

    hit = await cache.get("assistant", 1, "como armazenar charutos no humidor")
    assert hit is None


async def test_semantic_cache_invalidated_by_kg_version() -> None:
    cache = SemanticCache(_Index(), InMemoryKV(), _embed, threshold=0.5)
    await cache.set("assistant", 1, "harmoniza cohiba", _result("rum"))
    assert await cache.get("assistant", 2, "harmoniza cohiba") is None
