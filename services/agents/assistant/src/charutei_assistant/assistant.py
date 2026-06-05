"""Conversational Assistant (síncrono).

Orquestra, pela cascata: cache → KG (fato) → RAG (Sonnet) → Opus (gated), sempre com
citações. Todas as ferramentas passam pela cascata — nenhum SDK direto.
"""

from __future__ import annotations

from charutei_cache import ExactCache, SemanticCache
from charutei_contracts import CascadeResult, Tier
from charutei_knowledge import KnowledgeGraphRepo
from charutei_orchestrator import (
    AgentRegistry,
    AgentSpec,
    Cascade,
    EmbeddingProvider,
    Governance,
    LLMProvider,
    Tracer,
)

from charutei_assistant.kg_resolver import KGAssistantResolver
from charutei_assistant.rag import DocumentStore, RagGenerator

CAPABILITY = "assistant"
SYSTEM = (
    "Você é um assistente especialista em charutos. Responda de forma objetiva, em português, "
    "e cite as fontes fornecidas. Se não houver base, diga que não sabe."
)


def default_spec() -> AgentSpec:
    """Assistente pode escalar a Opus (gated por confiança) — é o caso de raciocínio difícil."""
    return AgentSpec(
        capability=CAPABILITY,
        description="Assistente especialista em charutos (cache→KG→RAG→Opus)",
        max_tier=Tier.LARGE,
        token_budget=8000,
        allow_opus_gating=True,
    )


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
    ) -> None:
        registry = registry or AgentRegistry()
        if registry.get(CAPABILITY) is None:
            registry.register(default_spec())
        rag = RagGenerator(embed, doc_store, llm)
        self._resolver = KGAssistantResolver(kg)
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
        )

    async def ask(self, text: str) -> CascadeResult:
        return await self._cascade.resolve(
            CAPABILITY, text, deterministic=self._resolver.resolve, system=SYSTEM
        )
