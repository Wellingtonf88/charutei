"""Contexto da aplicação: monta agentes/repos uma vez e injeta nos handlers.

Por padrão usa implementações in-memory + providers fake (dev/CI). Trocar por Postgres/
Supabase é injetar outra implementação — os handlers não mudam.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from charutei_band_recognition import BandRecognitionAgent, build_band_catalog, default_spec
from charutei_events import InMemoryOutbox
from charutei_knowledge import (
    InMemoryKnowledgeGraph,
    InMemoryOltp,
    InMemoryVectorRepository,
    NodeType,
    OltpRepository,
    seed_knowledge_graph,
)
from charutei_orchestrator import (
    AgentRegistry,
    FakeTracer,
    Governance,
    build_band_providers,
)

from charutei_api.auth import AuthProvider, FakeAuthProvider


@dataclass
class AppContext:
    band_agent: BandRecognitionAgent
    oltp: OltpRepository
    outbox: InMemoryOutbox
    auth: AuthProvider
    idempotency_keys: set[str] = field(default_factory=set)


async def build_context(auth: AuthProvider | None = None) -> AppContext:
    kg = InMemoryKnowledgeGraph()
    await seed_knowledge_graph(kg)

    image_embed, ocr, vision = build_band_providers()
    vector_repo = InMemoryVectorRepository()
    cigars = await kg.nodes_by_type(NodeType.CIGAR)
    labels = await build_band_catalog(image_embed, vector_repo, [(c.id, c.label) for c in cigars])

    registry = AgentRegistry()
    registry.register(default_spec())
    band_agent = BandRecognitionAgent(
        registry=registry,
        governance=Governance(),
        image_embed=image_embed,
        ocr=ocr,
        vision=vision,
        vector_repo=vector_repo,
        tracer=FakeTracer(),
        labels=labels,
    )

    return AppContext(
        band_agent=band_agent,
        oltp=InMemoryOltp(),
        outbox=InMemoryOutbox(),
        auth=auth or FakeAuthProvider(),
    )
