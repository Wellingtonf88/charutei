"""Gera tráfego real dos agentes e envia traces ao Langfuse (verificação da observabilidade).

Requer Langfuse no ar e env LANGFUSE_PUBLIC_KEY/SECRET_KEY/HOST. Roda com providers FAKE
(zero custo de LLM) mas tracing REAL — exatamente o que valida os dashboards.

    LANGFUSE_HOST=http://localhost:3010 LANGFUSE_PUBLIC_KEY=pk-lf-charutei-dev \
      LANGFUSE_SECRET_KEY=sk-lf-charutei-dev \
      uv run --extra providers python scripts/langfuse_demo.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from charutei_assistant import Assistant, Document, DocumentStore
from charutei_band_recognition import BandRecognitionAgent, build_band_catalog, default_spec
from charutei_cache import ExactCache, InMemoryKV, SemanticCache
from charutei_contracts import BandImage
from charutei_knowledge import (
    InMemoryKnowledgeGraph,
    InMemoryVectorRepository,
    NodeType,
    seed_knowledge_graph,
)
from charutei_orchestrator import (
    AgentRegistry,
    FakeEmbeddingProvider,
    FakeLLMProvider,
    Governance,
    build_band_providers,
    build_tracer,
)
from charutei_orchestrator.langfuse_tracer import LangfuseTracer

ROOT = Path(__file__).resolve().parents[1]

ASSISTANT_QUERIES = [
    "Com o que harmoniza o Cohiba Robustos?",  # KG (determinístico)
    "Qual o país do Davidoff Grand Cru No. 3?",  # KG
    "Como devo armazenar meus charutos no humidor?",  # RAG (Sonnet)
    "Qual a melhor forma de cortar um charuto?",  # RAG
    "Como devo armazenar meus charutos no humidor?",  # repetição → cache
]
BAND_IMAGES = [
    {"ref": "demo-1", "visual_text": "Partagás Serie D No. 4", "ocr_text": None},
    {"ref": "demo-2", "visual_text": "Cohiba", "ocr_text": None},  # ambíguo → visão
]


async def main() -> None:
    tracer = build_tracer()
    if not isinstance(tracer, LangfuseTracer):
        raise SystemExit("LANGFUSE_* não configurado — tracer real não foi criado.")

    kg = InMemoryKnowledgeGraph()
    await seed_knowledge_graph(kg)

    embed = FakeEmbeddingProvider()
    doc_store = DocumentStore(embed, InMemoryVectorRepository())
    docs = json.loads((ROOT / "evals/datasets/cigar_docs.json").read_text())["docs"]
    await doc_store.index_docs([Document(**d) for d in docs])

    kv = InMemoryKV()
    semantic = SemanticCache(InMemoryVectorRepository(), kv, lambda t: _embed_one(embed, t))
    assistant = Assistant(
        kg=kg,
        llm=FakeLLMProvider(),
        embed=embed,
        doc_store=doc_store,
        tracer=tracer,
        exact_cache=ExactCache(kv),
        semantic_cache=semantic,
    )

    for q in ASSISTANT_QUERIES:
        result = await assistant.ask(q)
        # score de qualidade (groundedness) ligado à trace — alimenta o dashboard de Qualidade.
        if result.trace_id:
            tracer.score(
                trace_id=result.trace_id,
                name="groundedness",
                value=1.0 if result.citations else 0.0,
            )
        tier = result.tier_resolved.name
        print(f"[assistant] tier={tier:13} cost=${result.cost_usd:.5f} :: {q[:40]}")

    # Band Recognition
    image_embed, ocr, vision = build_band_providers()
    vec = InMemoryVectorRepository()
    cigars = await kg.nodes_by_type(NodeType.CIGAR)
    labels = await build_band_catalog(image_embed, vec, [(c.id, c.label) for c in cigars])
    registry = AgentRegistry()
    registry.register(default_spec())
    band = BandRecognitionAgent(
        registry=registry,
        governance=Governance(),
        image_embed=image_embed,
        ocr=ocr,
        vision=vision,
        vector_repo=vec,
        tracer=tracer,
        labels=labels,
    )
    for img in BAND_IMAGES:
        r = await band.recognize(
            BandImage(ref=img["ref"], visual_text=img["visual_text"], ocr_text=img["ocr_text"])
        )
        print(f"[band]      cigar={r.cigar_id} vision={r.used_vision_llm} conf={r.confidence:.2f}")

    tracer.flush()
    print("\nflush enviado ao Langfuse.")


async def _embed_one(embed: FakeEmbeddingProvider, text: str) -> list[float]:
    return (await embed.embed([text]))[0]


if __name__ == "__main__":
    asyncio.run(main())
