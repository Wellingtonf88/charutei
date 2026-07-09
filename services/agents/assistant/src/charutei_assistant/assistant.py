"""Conversational Assistant (síncrono).

Orquestra, pela cascata: cache → KG (fato) → RAG (Sonnet) → **laço agêntico Opus (gated)**,
sempre com citações. Todas as ferramentas passam pela cascata — nenhum SDK direto.

O laço agêntico (tool-use sobre KG/RAG via MCP) só dispara no degrau Opus gated, quando o RAG
não ancora E a governança autoriza Opus — preservando "LLM é o último recurso". É habilitado
por `AgentSpec.allow_agentic_loop` (default do Assistant).
"""

from __future__ import annotations

import os

from charutei_cache import ExactCache, SemanticCache
from charutei_contracts import CascadeResult, Tier
from charutei_knowledge import KnowledgeGraphRepo
from charutei_orchestrator import (
    AgentRegistry,
    AgentSpec,
    Cascade,
    CigarTools,
    EmbeddingProvider,
    FakeToolRunner,
    Governance,
    LLMProvider,
    RetrievedDoc,
    ToolRunner,
    Tracer,
    build_cigar_tools,
)

from charutei_assistant.kg_resolver import KGAssistantResolver
from charutei_assistant.rag import DocumentStore, RagGenerator

CAPABILITY = "assistant"
SYSTEM = (
    "Você é um assistente especialista em charutos. Responda de forma objetiva, em português, "
    "e cite as fontes fornecidas. Se não houver base, diga que não sabe."
)


def default_spec() -> AgentSpec:
    """Assistente escala a Opus (gated) via laço agêntico — caso de raciocínio difícil."""
    return AgentSpec(
        capability=CAPABILITY,
        description="Assistente especialista em charutos (cache→KG→RAG→Opus agêntico)",
        max_tier=Tier.LARGE,
        token_budget=8000,
        allow_opus_gating=True,
        allow_agentic_loop=True,
    )


class _DocStoreRetriever:
    """Adapta o `DocumentStore` (RAG) ao Protocol `DocRetriever` da ferramenta `rag_search`."""

    def __init__(self, store: DocumentStore) -> None:
        self._store = store

    async def search(self, query: str, k: int = 4) -> list[RetrievedDoc]:
        hits = await self._store.search(query, k=k)
        return [
            RetrievedDoc(id=d.id, title=d.title, text=d.text, score=score) for d, score in hits
        ]


def _build_tool_runner(cigar_tools: CigarTools) -> ToolRunner:
    """FakeToolRunner em CI/dev; AnthropicToolRunner (Opus + MCP) quando providers reais."""
    use_fake = os.environ.get("USE_FAKE_PROVIDERS", "true").lower() in {"1", "true", "yes"}
    if use_fake:
        return FakeToolRunner()
    from charutei_orchestrator import AnthropicToolRunner, build_mcp_server

    return AnthropicToolRunner(build_mcp_server(cigar_tools))


class Assistant:
    def __init__(
        self,
        *,
        kg: KnowledgeGraphRepo,
        llm: LLMProvider,
        embed: EmbeddingProvider,
        doc_store: DocumentStore,
        tracer: Tracer,
        exact_cache: ExactCache | None = None,
        semantic_cache: SemanticCache | None = None,
        registry: AgentRegistry | None = None,
        governance: Governance | None = None,
        tool_runner: ToolRunner | None = None,
    ) -> None:
        registry = registry or AgentRegistry()
        spec = registry.get(CAPABILITY) or default_spec()
        if registry.get(CAPABILITY) is None:
            registry.register(spec)
        rag = RagGenerator(embed, doc_store, llm)
        self._resolver = KGAssistantResolver(kg)

        # Ferramentas do laço agêntico (read-only, sem LLM) — só montadas se a spec habilitar.
        tools = None
        runner = tool_runner
        if spec.allow_agentic_loop:
            cigar_tools = CigarTools(kg, _DocStoreRetriever(doc_store))
            tools = build_cigar_tools(cigar_tools)
            runner = runner or _build_tool_runner(cigar_tools)

        self._cascade = Cascade(
            registry=registry,
            governance=governance or Governance(),
            llm=llm,
            tracer=tracer,
            exact_cache=exact_cache,
            semantic_cache=semantic_cache,
            kg_version=kg.version,
            generation_start=Tier.MEDIUM,
            generator=rag.generate,
            tool_runner=runner,
            tools=tools,
        )

    async def ask(self, text: str) -> CascadeResult:
        return await self._cascade.resolve(
            CAPABILITY, text, deterministic=self._resolver.resolve, system=SYSTEM
        )
