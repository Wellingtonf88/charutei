"""Cascata de inteligência — desce pelos degraus e para no mais barato que resolve.

`1 cache → 2 KG/SQL → 3/4 geração (Haiku/Sonnet) → 5 Opus (gated)`. Toda etapa é
contabilizada (tier, custo, tokens, latência) via Tracer. Governança decide cada escalada;
cache exato+semântico guarda o resultado. A geração é plugável via `Generator` — o assistente
injeta RAG (recuperação + citações) sem mudar o motor. Nenhum SDK é chamado fora daqui.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from charutei_cache import ExactCache, SemanticCache
from charutei_contracts import CascadeResult, Citation, Tier
from pydantic import BaseModel, Field

from charutei_orchestrator.governance import Governance
from charutei_orchestrator.providers import LLMProvider, Tracer, TraceRecord
from charutei_orchestrator.registry import TIER_MODELS, AgentRegistry, AgentSpec
from charutei_orchestrator.router import RouteDecision, classify

# Resolver determinístico fornecido pelo chamador (KG/SQL). Retorna resultado ancorado
# (com citações) ou None se não souber responder — aí a cascata sobe para geração.
DeterministicResolver = Callable[[str, RouteDecision], Awaitable[CascadeResult | None]]
KgVersionFn = Callable[[], Awaitable[int]]


class GenerationOutput(BaseModel):
    """Saída de um passo de geração (com ou sem RAG)."""

    text: str
    model: str
    citations: list[Citation] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    confidence: float = 1.0


# Gerador plugável: recebe (model, system, prompt) e devolve texto + citações + custo.
Generator = Callable[[str, str, str], Awaitable[GenerationOutput]]


class Cascade:
    def __init__(
        self,
        *,
        registry: AgentRegistry,
        governance: Governance,
        llm: LLMProvider,
        tracer: Tracer,
        exact_cache: ExactCache | None = None,
        semantic_cache: SemanticCache | None = None,
        kg_version: KgVersionFn | None = None,
        generation_start: Tier = Tier.MEDIUM,
        generator: Generator | None = None,
    ) -> None:
        self._registry = registry
        self._gov = governance
        self._llm = llm
        self._tracer = tracer
        self._exact = exact_cache
        self._semantic = semantic_cache
        self._kg_version = kg_version
        self._gen_start = generation_start
        self._generator = generator or self._default_generator

    async def resolve(
        self,
        capability: str,
        text: str,
        *,
        deterministic: DeterministicResolver | None = None,
        system: str = "Você é um assistente especialista em charutos. Responda com citações.",
    ) -> CascadeResult:
        spec = self._registry.require(capability)
        self._gov.ensure_enabled(spec)
        version = await self._kg_version() if self._kg_version else 0

        # ---- Degrau 1: cache (exato → semântico) ----
        for cache_get in self._cache_getters():
            t0 = time.perf_counter()
            hit = await cache_get(capability, version, text)
            if hit is not None:
                await self._trace("cache", Tier.CACHE, t0)
                return hit

        route = classify(text)

        # ---- Degrau 2: determinístico (KG/SQL) ----
        if route.kg_lookup and deterministic is not None:
            t0 = time.perf_counter()
            resolved = await deterministic(text, route)
            if resolved is not None:
                await self._trace("deterministic", Tier.DETERMINISTIC, t0)
                await self._store(capability, version, text, resolved)
                return resolved

        # ---- Degraus 3-5: geração (com gating de Opus) ----
        if route.allow_generation:
            result = await self._generate(spec, text, system)
            await self._store(capability, version, text, result)
            return result

        # Nada resolveu → encaminhar para humano (nunca alucina).
        return CascadeResult(tier_resolved=Tier.DETERMINISTIC, needs_human=True)

    async def _generate(self, spec: AgentSpec, text: str, system: str) -> CascadeResult:
        tier: Tier = min(self._gen_start, self._gov.effective_max_tier(spec))
        t0 = time.perf_counter()
        out = await self._generator(TIER_MODELS[tier], system, text)
        tokens_used = out.input_tokens + out.output_tokens
        cost = out.cost_usd
        await self._trace("generation", tier, t0, output=out)

        # Gating de Opus: só sobe se confiança baixa E governança autorizar.
        decision = self._gov.can_escalate(
            spec, Tier.LARGE, confidence=out.confidence, tokens_used=tokens_used
        )
        if decision.allowed:
            t1 = time.perf_counter()
            out = await self._generator(TIER_MODELS[Tier.LARGE], system, text)
            tier = Tier.LARGE
            tokens_used += out.input_tokens + out.output_tokens
            cost += out.cost_usd
            await self._trace("generation_escalated", tier, t1, output=out)

        return CascadeResult(
            answer=out.text,
            tier_resolved=tier,
            cost_usd=cost,
            input_tokens=tokens_used,
            output_tokens=out.output_tokens,
            citations=out.citations,
        )

    async def _default_generator(self, model: str, system: str, prompt: str) -> GenerationOutput:
        """Geração padrão (sem RAG): chama o LLM e devolve sem citações."""
        resp = await self._llm.generate(model=model, system=system, prompt=prompt)
        return GenerationOutput(
            text=resp.text,
            model=resp.model,
            input_tokens=resp.input_tokens,
            output_tokens=resp.output_tokens,
            cost_usd=resp.cost_usd,
            confidence=resp.confidence,
        )

    # ------------------------------------------------------------------ helpers

    def _cache_getters(
        self,
    ) -> list[Callable[[str, int, str], Awaitable[CascadeResult | None]]]:
        getters: list[Callable[[str, int, str], Awaitable[CascadeResult | None]]] = []
        if self._exact is not None:
            getters.append(self._exact.get)
        if self._semantic is not None:
            getters.append(self._semantic.get)
        return getters

    async def _store(self, capability: str, version: int, text: str, result: CascadeResult) -> None:
        if self._exact is not None:
            await self._exact.set(capability, version, text, result)
        if self._semantic is not None:
            await self._semantic.set(capability, version, text, result)

    async def _trace(
        self, name: str, tier: Tier, t0: float, *, output: GenerationOutput | None = None
    ) -> None:
        record = TraceRecord(
            name=name,
            tier=int(tier),
            model=output.model if output else None,
            latency_ms=(time.perf_counter() - t0) * 1000.0,
            cost_usd=output.cost_usd if output else 0.0,
            input_tokens=output.input_tokens if output else 0,
            output_tokens=output.output_tokens if output else 0,
        )
        await self._tracer.log(record)
