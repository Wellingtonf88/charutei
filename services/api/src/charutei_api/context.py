"""Contexto da aplicação: monta agentes/repos uma vez e injeta nos handlers.

Por padrão usa implementações in-memory + providers fake (dev/CI). Trocar por Postgres/
Supabase é injetar outra implementação — os handlers não mudam.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from charutei_assistant import Assistant, DocumentStore
from charutei_band_recognition import BandRecognitionAgent, build_band_catalog, default_spec
from charutei_events import InMemoryOutbox
from charutei_knowledge import (
    InMemoryKnowledgeGraph,
    InMemoryOltp,
    InMemoryVectorRepository,
    KnowledgeGraphRepo,
    NodeType,
    OltpRepository,
    seed_knowledge_graph,
)
from charutei_orchestrator import (
    AgentRegistry,
    FakeTracer,
    Governance,
    Supervisor,
    build_band_providers,
    build_providers,
)

from charutei_api.auth import AuthProvider, build_auth_provider


@dataclass
class AppContext:
    band_agent: BandRecognitionAgent
    assistant: Assistant
    oltp: OltpRepository
    outbox: InMemoryOutbox
    auth: AuthProvider
    kg: KnowledgeGraphRepo
    supervisor: Supervisor
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
    governance = Governance()
    band_agent = BandRecognitionAgent(
        registry=registry,
        governance=governance,
        image_embed=image_embed,
        ocr=ocr,
        vision=vision,
        vector_repo=vector_repo,
        tracer=FakeTracer(),
        labels=labels,
    )

    # Assistant: cascata cache→KG→RAG→Opus agêntico. Compartilha registry/governance para o
    # Supervisor enxergar a capability 'assistant' (roteamento + kill-switch).
    llm, embed, tracer = build_providers()
    doc_store = DocumentStore(embed, InMemoryVectorRepository())
    assistant = Assistant(
        kg=kg,
        llm=llm,
        embed=embed,
        doc_store=doc_store,
        tracer=tracer,
        registry=registry,
        governance=governance,
    )

    # Supervisor: roteia requisições aos especialistas sob o registro/kill-switch (sem LLM).
    supervisor = Supervisor(registry, governance)
    supervisor.register("band_recognition", band_agent.recognize)
    supervisor.register("assistant", assistant.ask)

    return AppContext(
        band_agent=band_agent,
        assistant=assistant,
        oltp=InMemoryOltp(),
        outbox=InMemoryOutbox(),
        auth=auth or build_auth_provider(),
        kg=kg,
        supervisor=supervisor,
    )
