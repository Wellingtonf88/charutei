"""Testes do motor da cascata: parada no degrau barato, gating, cache e tracing."""

from charutei_cache import ExactCache, InMemoryKV
from charutei_contracts import CascadeResult, Citation, Tier
from charutei_orchestrator import (
    AgentRegistry,
    AgentSpec,
    Cascade,
    FakeLLMProvider,
    FakeTracer,
    Governance,
    LLMResponse,
    cascade_metrics,
    llm_cost,
)
from charutei_orchestrator.router import Intent, RouteDecision


def _registry(**kw: object) -> AgentRegistry:
    reg = AgentRegistry()
    reg.register(AgentSpec(capability="assistant", **kw))  # type: ignore[arg-type]
    return reg


async def _ver() -> int:
    return 1


async def _kg_resolver(text: str, route: RouteDecision) -> CascadeResult | None:
    if route.intent == Intent.HARMONIZATION and "cohiba" in text.lower():
        return CascadeResult(
            answer="Harmoniza com rum envelhecido.",
            tier_resolved=Tier.DETERMINISTIC,
            citations=[Citation(source_id="pairing:rum-anejo", title="Rum envelhecido")],
        )
    return None


async def test_stops_at_deterministic_tier_with_citations() -> None:
    cascade = Cascade(
        registry=_registry(max_tier=Tier.MEDIUM),
        governance=Governance(),
        llm=FakeLLMProvider(),
        tracer=FakeTracer(),
        kg_version=_ver,
    )
    result = await cascade.resolve(
        "assistant", "Com o que harmoniza o Cohiba?", deterministic=_kg_resolver
    )
    assert result.tier_resolved == Tier.DETERMINISTIC
    assert result.cost_usd == 0.0
    assert result.citations and result.citations[0].source_id == "pairing:rum-anejo"


async def test_falls_back_to_generation_when_kg_silent() -> None:
    cascade = Cascade(
        registry=_registry(max_tier=Tier.MEDIUM),
        governance=Governance(),
        llm=FakeLLMProvider(),
        tracer=FakeTracer(),
        kg_version=_ver,
    )
    result = await cascade.resolve(
        "assistant", "Como armazenar charutos?", deterministic=_kg_resolver
    )
    assert result.tier_resolved == Tier.MEDIUM  # Sonnet (default de geração)
    assert result.cost_usd > 0.0
    assert result.answer


async def test_second_identical_query_hits_cache() -> None:
    cascade = Cascade(
        registry=_registry(max_tier=Tier.MEDIUM),
        governance=Governance(),
        llm=FakeLLMProvider(),
        tracer=FakeTracer(),
        exact_cache=ExactCache(InMemoryKV()),
        kg_version=_ver,
    )
    q = "Como armazenar charutos?"
    first = await cascade.resolve("assistant", q, deterministic=_kg_resolver)
    second = await cascade.resolve("assistant", q, deterministic=_kg_resolver)
    assert first.tier_resolved == Tier.MEDIUM
    assert second.tier_resolved == Tier.CACHE
    assert second.cost_usd == 0.0


class _LowConfidenceLLM(FakeLLMProvider):
    """Sonnet 'inseguro' → dispara o gating para Opus."""

    async def generate(
        self, *, model: str, system: str, prompt: str, max_tokens: int = 512
    ) -> LLMResponse:
        base = await super().generate(
            model=model, system=system, prompt=prompt, max_tokens=max_tokens
        )
        # Opus retorna confiança alta; Sonnet, baixa (força a escalada).
        return base.model_copy(update={"confidence": 0.9 if model.startswith("opus") else 0.2})


async def test_opus_escalation_only_when_authorized_and_unconfident() -> None:
    cascade = Cascade(
        registry=_registry(max_tier=Tier.LARGE, allow_opus_gating=True, token_budget=100000),
        governance=Governance(opus_confidence_threshold=0.6),
        llm=_LowConfidenceLLM(),
        tracer=FakeTracer(),
        kg_version=_ver,
    )
    result = await cascade.resolve(
        "assistant", "pergunta difícil de raciocínio", deterministic=_kg_resolver
    )
    assert result.tier_resolved == Tier.LARGE
    assert result.used_large_model is True


async def test_no_escalation_without_gating_authorization() -> None:
    cascade = Cascade(
        registry=_registry(max_tier=Tier.LARGE, allow_opus_gating=False),
        governance=Governance(),
        llm=_LowConfidenceLLM(),
        tracer=FakeTracer(),
        kg_version=_ver,
    )
    result = await cascade.resolve("assistant", "pergunta difícil", deterministic=_kg_resolver)
    assert result.tier_resolved == Tier.MEDIUM  # teto efetivo sem gating


async def test_tracer_records_each_step() -> None:
    tracer = FakeTracer()
    cascade = Cascade(
        registry=_registry(max_tier=Tier.MEDIUM),
        governance=Governance(),
        llm=FakeLLMProvider(),
        tracer=tracer,
        kg_version=_ver,
    )
    await cascade.resolve("assistant", "Como armazenar charutos?", deterministic=_kg_resolver)
    assert tracer.records
    assert tracer.records[-1].tier == int(Tier.MEDIUM)
    assert tracer.records[-1].model == "sonnet-4.6"


def test_metrics_distribution_and_cost() -> None:
    results = [
        CascadeResult(tier_resolved=Tier.DETERMINISTIC),
        CascadeResult(tier_resolved=Tier.MEDIUM, cost_usd=0.004),
        CascadeResult(tier_resolved=Tier.CACHE),
    ]
    m = cascade_metrics(results)
    assert m.total == 3
    assert m.pct_without_opus == 1.0
    assert round(m.avg_cost_usd, 5) == round(0.004 / 3, 5)


def test_pricing_sonnet_cost() -> None:
    # 1000 in + 500 out no Sonnet (3/15 por Mtok)
    assert round(llm_cost("sonnet-4.6", 1000, 500), 6) == round(0.003 + 0.0075, 6)
