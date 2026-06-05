"""Testes do Conversational Assistant: KG (fato) vs RAG, citações, cache e cascata."""

from charutei_assistant import Assistant, Document, DocumentStore
from charutei_cache import ExactCache, InMemoryKV, SemanticCache
from charutei_contracts import Tier
from charutei_knowledge import (
    InMemoryKnowledgeGraph,
    InMemoryVectorRepository,
    seed_knowledge_graph,
)
from charutei_orchestrator import FakeEmbeddingProvider, FakeLLMProvider, FakeTracer

_DOCS = [
    Document(
        id="doc-humidor",
        title="Armazenamento em humidor",
        text="Guarde charutos em um humidor com umidade de 70% e temperatura de 18°C. "
        "Use um higrômetro para monitorar a umidade.",
    ),
    Document(
        id="doc-corte",
        title="Como cortar",
        text="Corte o charuto acima da linha do cap usando uma guilhotina ou um punch.",
    ),
]


async def _build() -> Assistant:
    kg = InMemoryKnowledgeGraph()
    await seed_knowledge_graph(kg)
    embed = FakeEmbeddingProvider()
    store = DocumentStore(embed, InMemoryVectorRepository())
    await store.index_docs(_DOCS)
    kv = InMemoryKV()

    async def embed_one(t: str) -> list[float]:
        return (await embed.embed([t]))[0]

    return Assistant(
        kg=kg,
        llm=FakeLLMProvider(),
        embed=embed,
        doc_store=store,
        tracer=FakeTracer(),
        exact_cache=ExactCache(kv),
        semantic_cache=SemanticCache(InMemoryVectorRepository(), kv, embed_one),
    )


async def test_harmonization_resolved_by_kg_with_citations() -> None:
    assistant = await _build()
    result = await assistant.ask("Com o que harmoniza o Cohiba Robustos?")
    assert result.tier_resolved == Tier.DETERMINISTIC
    assert result.cost_usd == 0.0
    assert result.citations
    assert any("rum" in (c.source_id or "").lower() for c in result.citations)


async def test_fact_lookup_resolved_by_kg() -> None:
    assistant = await _build()
    result = await assistant.ask("Qual o país do Davidoff Grand Cru No. 3?")
    assert result.tier_resolved == Tier.DETERMINISTIC
    assert result.citations
    assert result.answer and "country" in result.answer


async def test_general_question_uses_rag_with_citations() -> None:
    assistant = await _build()
    result = await assistant.ask("Como devo armazenar meus charutos no humidor?")
    assert result.tier_resolved == Tier.MEDIUM  # RAG via Sonnet
    assert result.cost_usd > 0.0
    assert result.citations
    assert any(c.source_id == "doc-humidor" for c in result.citations)


async def test_repeat_question_hits_cache() -> None:
    assistant = await _build()
    q = "Como devo armazenar meus charutos no humidor?"
    first = await assistant.ask(q)
    second = await assistant.ask(q)
    assert first.tier_resolved == Tier.MEDIUM
    assert second.tier_resolved == Tier.CACHE
    assert second.cost_usd == 0.0
