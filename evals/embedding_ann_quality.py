"""Eval `embedding_ann_quality` — qualidade ANN dos embeddings de texto de charuto.

Verifica que para cada charuto do seed curado, a busca ANN por embedding do label exato
retorna o próprio charuto como rank-1. Roda com providers fake (em memória, sem chave de
API) — CI-safe.

Gate: rank1_accuracy ≥ 0.90
"""

from __future__ import annotations

from charutei_knowledge import (
    InMemoryKnowledgeGraph,
    InMemoryVectorRepository,
    NodeType,
    seed_knowledge_graph,
)
from charutei_orchestrator.providers import FakeEmbeddingProvider

from evals.harness import EvalReport

GATE_ACCURACY = 0.90
CIGAR_KIND = "cigar_text"


async def run() -> EvalReport:
    kg = InMemoryKnowledgeGraph()
    await seed_knowledge_graph(kg)
    vec = InMemoryVectorRepository()
    embed_provider = FakeEmbeddingProvider()

    cigars = await kg.nodes_by_type(NodeType.CIGAR)
    if not cigars:
        return EvalReport(
            name="embedding_ann_quality",
            passed=False,
            summary="nenhum cigar no KG seed",
            details={"rank1_accuracy": 0.0},
        )

    labels = [c.label for c in cigars]
    embeddings = await embed_provider.embed(labels)
    for cigar, emb in zip(cigars, embeddings, strict=True):
        await vec.upsert(CIGAR_KIND, cigar.id, emb, {"cigar_id": cigar.id})

    hits = 0
    misses: list[str] = []
    for cigar, emb in zip(cigars, embeddings, strict=True):
        results = await vec.ann_search(CIGAR_KIND, emb, k=1)
        rank1_id = results[0][0] if results else None
        if rank1_id == cigar.id:
            hits += 1
        else:
            misses.append(f"{cigar.id} → {rank1_id}")

    total = len(cigars)
    accuracy = hits / total
    passed = accuracy >= GATE_ACCURACY
    summary = f"{total} charutos · rank1_accuracy={accuracy:.0%}"
    if misses:
        summary += f" | erros: {misses[:5]}"
    return EvalReport(
        name="embedding_ann_quality",
        passed=passed,
        summary=summary,
        details={
            "rank1_accuracy": accuracy,
            "total": float(total),
            "hits": float(hits),
            "misses": float(len(misses)),
        },
    )
