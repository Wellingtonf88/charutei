"""Montagem do Conversational Assistant real (fakes + KG semeado + corpus) para evals/testes."""

from __future__ import annotations

import json
from pathlib import Path

from charutei_assistant import Assistant, Document, DocumentStore
from charutei_cache import ExactCache, InMemoryKV, SemanticCache
from charutei_knowledge import (
    InMemoryKnowledgeGraph,
    InMemoryVectorRepository,
    seed_knowledge_graph,
)
from charutei_orchestrator import FakeEmbeddingProvider, FakeLLMProvider, FakeTracer

_DOCS = Path(__file__).resolve().parent / "datasets" / "cigar_docs.json"


async def build_assistant() -> Assistant:
    kg = InMemoryKnowledgeGraph()
    await seed_knowledge_graph(kg)

    embed = FakeEmbeddingProvider()
    doc_store = DocumentStore(embed, InMemoryVectorRepository())
    docs = json.loads(_DOCS.read_text(encoding="utf-8"))["docs"]
    await doc_store.index_docs([Document(**d) for d in docs])

    kv = InMemoryKV()
    semantic = SemanticCache(InMemoryVectorRepository(), kv, lambda t: _embed_one(embed, t))

    return Assistant(
        kg=kg,
        llm=FakeLLMProvider(),
        embed=embed,
        doc_store=doc_store,
        tracer=FakeTracer(),
        exact_cache=ExactCache(kv),
        semantic_cache=semantic,
    )


async def _embed_one(embed: FakeEmbeddingProvider, text: str) -> list[float]:
    vectors = await embed.embed([text])
    return vectors[0]
