"""Montagem reutilizável de uma cascata 'assistente' com fakes + KG semeado.

Usada pelos evals (e disponível a testes). O resolver determinístico aqui é uma versão
mínima do que a S5 fará: detecta um charuto citado e responde harmonização/ficha pelo KG,
com citações — ou devolve None para a cascata subir à geração.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from charutei_cache import ExactCache, InMemoryKV, SemanticCache
from charutei_contracts import CascadeResult, Citation, Tier
from charutei_knowledge import (
    InMemoryKnowledgeGraph,
    InMemoryVectorRepository,
    NodeType,
    node_id,
    seed_knowledge_graph,
)
from charutei_orchestrator import (
    AgentRegistry,
    AgentSpec,
    Cascade,
    FakeEmbeddingProvider,
    FakeLLMProvider,
    FakeTracer,
    Governance,
)
from charutei_orchestrator.router import Intent, RouteDecision

CAPABILITY = "assistant"
_DATASET = Path(__file__).resolve().parent / "datasets" / "cigars_seed.json"


def _strip(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


@dataclass
class AssistantHarness:
    cascade: Cascade
    kg: InMemoryKnowledgeGraph
    tracer: FakeTracer
    deterministic: object  # DeterministicResolver

    async def ask(self, text: str) -> CascadeResult:
        return await self.cascade.resolve(
            CAPABILITY,
            text,
            deterministic=self.deterministic,  # type: ignore[arg-type]
        )


async def build_assistant_harness() -> AssistantHarness:
    kg = InMemoryKnowledgeGraph()
    await seed_knowledge_graph(kg)

    # Mapa nome-do-charuto → id, para o resolver detectar a entidade citada.
    data = json.loads(_DATASET.read_text(encoding="utf-8"))
    cigar_index = {_strip(c["name"]): node_id(NodeType.CIGAR, c["slug"]) for c in data["cigars"]}

    async def find_cigar(text: str) -> str | None:
        q = _strip(text)
        for name, cid in cigar_index.items():
            if name in q:
                return cid
        return None

    async def deterministic(text: str, route: RouteDecision) -> CascadeResult | None:
        cigar_id = await find_cigar(text)
        if cigar_id is None:
            return None
        if route.intent == Intent.HARMONIZATION:
            pairings = await kg.harmonizations(cigar_id)
            if not pairings:
                return None
            answer = "Harmoniza com: " + ", ".join(p.label for p in pairings) + "."
            citations = [Citation(source_id=p.id, title=p.label) for p in pairings]
            return CascadeResult(
                answer=answer, tier_resolved=Tier.DETERMINISTIC, citations=citations
            )
        if route.intent == Intent.FACT_LOOKUP:
            neighbors = await kg.neighbors(cigar_id)
            if not neighbors:
                return None
            facts = ", ".join(f"{n.type}: {n.label}" for n in neighbors)
            citations = [Citation(source_id=cigar_id, title="Ficha técnica")]
            return CascadeResult(
                answer=facts, tier_resolved=Tier.DETERMINISTIC, citations=citations
            )
        return None

    registry = AgentRegistry()
    registry.register(
        AgentSpec(
            capability=CAPABILITY,
            description="Assistente especialista em charutos",
            max_tier=Tier.LARGE,
            token_budget=8000,
            allow_opus_gating=True,
        )
    )

    kv = InMemoryKV()
    embed = FakeEmbeddingProvider()
    tracer = FakeTracer()
    semantic = SemanticCache(InMemoryVectorRepository(), kv, lambda t: _embed_one(embed, t))

    cascade = Cascade(
        registry=registry,
        governance=Governance(),
        llm=FakeLLMProvider(),
        tracer=tracer,
        exact_cache=ExactCache(kv),
        semantic_cache=semantic,
        kg_version=kg.version,
        generation_start=Tier.MEDIUM,
    )
    return AssistantHarness(cascade=cascade, kg=kg, tracer=tracer, deterministic=deterministic)


async def _embed_one(embed: FakeEmbeddingProvider, text: str) -> list[float]:
    vectors = await embed.embed([text])
    return vectors[0]
