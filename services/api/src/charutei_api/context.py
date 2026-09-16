"""Contexto da aplicação: monta agentes/repos uma vez e injeta nos handlers.

Persistência selecionada por env (espelha `build_providers`/`build_auth_provider`):
- `DATABASE_URL` presente → repositórios **Postgres** (KG + OLTP duráveis; sobrevivem a restart);
- ausente → **in-memory** (dev/CI/demo).

Índices derivados (catálogo vetorial do reconhecimento + corpus RAG) ficam sempre in-memory,
reconstruídos do KG a cada boot — não são estado durável, são cache de recuperação.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from charutei_assistant import Assistant, Document, DocumentStore
from charutei_band_recognition import BandRecognitionAgent, build_band_catalog, default_spec
from charutei_cache import InMemoryKV
from charutei_cigar_intelligence import CatalogIngestor, parse_catalog_csv
from charutei_embedding_worker import ContentEmbeddingCache, EmbeddingWorker
from charutei_events import (
    EventBus,
    InMemoryEventBus,
    InMemoryOutbox,
    InMemoryProcessedRegistry,
    Outbox,
    ProcessedRegistry,
)
from charutei_knowledge import (
    InMemoryKnowledgeGraph,
    InMemoryOltp,
    InMemoryVectorRepository,
    KnowledgeGraphRepo,
    NodeType,
    OltpRepository,
    VectorRepository,
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

# Dados da demo: catálogo completo (410 SKUs) + corpus de conhecimento para o RAG.
# Resolvidos da raiz do repo; sobrescrevíveis por CHARUTEI_DATA_DIR (deploy/container).
_DATA_DIR = Path(os.environ.get("CHARUTEI_DATA_DIR", Path(__file__).resolve().parents[4] / "data"))
_CATALOG_CSV = _DATA_DIR / "catalog" / "cigars.csv"
_DOCS_JSON = _DATA_DIR / "docs" / "cigar_docs.json"


@dataclass
class AppContext:
    band_agent: BandRecognitionAgent
    assistant: Assistant
    oltp: OltpRepository
    outbox: Outbox
    auth: AuthProvider
    kg: KnowledgeGraphRepo
    supervisor: Supervisor
    bus: EventBus
    embedding_worker: EmbeddingWorker
    vector_repo: VectorRepository
    conn: Any = None  # conexão Postgres (None em modo in-memory) — fechada por aclose()

    async def aclose(self) -> None:
        """Libera recursos (conexão Postgres) no shutdown do app."""
        if self.conn is not None:
            await self.conn.close()


async def _build_durable(
    dsn: str,
) -> tuple[KnowledgeGraphRepo, OltpRepository, Outbox, ProcessedRegistry, Any]:
    """Repositórios Postgres (KG + OLTP + outbox/idempotência de eventos) sob uma conexão.

    Semeia+ingere só se o KG estiver vazio. Os repos commitam internamente por operação →
    escritas são duráveis. `psycopg` é lazy-import (extra `postgres`). Uma conexão por
    processo — pooling/concorrência é o passo de escala.
    """
    import psycopg
    from charutei_events.postgres import (
        PostgresOutbox,
        PostgresProcessedRegistry,
        apply_events_schema,
    )
    from charutei_knowledge.postgres import PostgresKnowledgeGraph, PostgresOltp, apply_schema

    # Normaliza o prefixo SQLAlchemy do .env.example (psycopg.connect não aceita `+psycopg`).
    conn = await psycopg.AsyncConnection.connect(
        dsn.replace("postgresql+psycopg://", "postgresql://")
    )
    await apply_schema(conn)
    # outbox/processed_events — mesma rede de segurança idempotente do apply_schema acima.
    await apply_events_schema(conn)
    kg: KnowledgeGraphRepo = PostgresKnowledgeGraph(conn)
    oltp: OltpRepository = PostgresOltp(conn)
    outbox: Outbox = PostgresOutbox(conn)
    processed: ProcessedRegistry = PostgresProcessedRegistry(conn)

    if not await kg.nodes_by_type(NodeType.CIGAR):  # primeira subida → popula uma vez
        await seed_knowledge_graph(kg)
        if _CATALOG_CSV.exists():
            # outbox=outbox: emite sku.detectado por SKU → o worker materializa o embedding de
            # texto (kind=cigar_text) de forma assíncrona. Antes desta Fase 1, `outbox` não era
            # passado aqui — a ingestão nunca emitia o evento (achado do audit).
            await CatalogIngestor(kg, outbox=outbox).ingest(parse_catalog_csv(_CATALOG_CSV))
    return kg, oltp, outbox, processed, conn


async def _build_memory() -> tuple[
    KnowledgeGraphRepo, OltpRepository, Outbox, ProcessedRegistry, None
]:
    """Repositórios in-memory (dev/CI/demo). Semeia + ingere o catálogo a cada boot (barato)."""
    kg = InMemoryKnowledgeGraph()
    outbox = InMemoryOutbox()
    await seed_knowledge_graph(kg)
    if _CATALOG_CSV.exists():
        await CatalogIngestor(kg, outbox=outbox).ingest(parse_catalog_csv(_CATALOG_CSV))
    return kg, InMemoryOltp(), outbox, InMemoryProcessedRegistry(), None


async def build_context(auth: AuthProvider | None = None) -> AppContext:
    dsn = os.environ.get("DATABASE_URL")
    kg, oltp, outbox, processed_registry, conn = await (
        _build_durable(dsn) if dsn else _build_memory()
    )

    # Índices derivados (in-memory, reconstruídos do KG): catálogo vetorial do reconhecimento.
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
    # Indexa o corpus de conhecimento geral → respostas não-estruturadas (RAG) ficam ancoradas;
    # sem ele, perguntas gerais escalariam ao laço Opus sem fonte para citar.
    if _DOCS_JSON.exists():
        docs = json.loads(_DOCS_JSON.read_text(encoding="utf-8"))["docs"]
        await doc_store.index_docs([Document(**d) for d in docs])
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

    # Fila interna (sempre em memória — plumbing de processo único, não a fronteira de
    # durabilidade: essa é o outbox Postgres acima). O worker materializa embeddings a partir
    # dos mesmos eventos que o outbox publica; roda dentro do próprio BFF (pump_events, chamado
    # pelo loop de fundo em app.py) porque hoje só o BFF é implantado (ver
    # PROJECT_UPGRADE_AUDIT.md).
    bus: EventBus = InMemoryEventBus()
    embedding_worker = EmbeddingWorker(
        bus=bus,
        processed=processed_registry,
        image_embed=image_embed,
        text_embed=embed,
        vector_repo=vector_repo,
        content_cache=ContentEmbeddingCache(InMemoryKV()),
    )

    return AppContext(
        band_agent=band_agent,
        assistant=assistant,
        oltp=oltp,
        outbox=outbox,
        auth=auth or build_auth_provider(),
        kg=kg,
        supervisor=supervisor,
        bus=bus,
        embedding_worker=embedding_worker,
        vector_repo=vector_repo,
        conn=conn,
    )


async def pump_events(ctx: AppContext, batch: int = 100) -> None:
    """Move o outbox pendente para o bus e processa (embeddings). Idempotente — chamável a
    qualquer momento (loop de fundo em app.py, ou diretamente em teste, sem depender de tempo)."""
    await ctx.outbox.publish_pending(ctx.bus, batch=batch)
    await ctx.embedding_worker.drain()
