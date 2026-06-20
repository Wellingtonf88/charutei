"""Testes do laço agêntico (S13): loop fake, encaixe na cascata e invariante de custo.

O loop agêntico só pode rodar no degrau Opus gated. A trava "LLM é o último recurso"
exige que ele NUNCA seja invocado quando cache/KG/RAG resolvem — verificado por espião.
"""

from charutei_contracts import CascadeResult, Citation, Tier
from charutei_orchestrator import (
    AgentTool,
    Cascade,
    FakeLLMProvider,
    FakeToolRunner,
    FakeTracer,
    Governance,
    LLMResponse,
    ToolResult,
)
from charutei_orchestrator.registry import AgentRegistry, AgentSpec
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
            citations=[Citation(source_id="pairing:rum-anejo")],
        )
    return None


async def _kg_tool_handler(query: str) -> ToolResult:
    return ToolResult(
        text="Cohiba Siglo VI: força média-cheia, Cuba.",
        citations=[Citation(source_id="cigar:cohiba-siglo-vi", title="Cohiba Siglo VI")],
    )


def _tools() -> list[AgentTool]:
    return [AgentTool(name="kg_query", description="Consulta o KG", handler=_kg_tool_handler)]


class _LowConfidenceLLM(FakeLLMProvider):
    """Sonnet 'inseguro' → dispara o gating para Opus (degrau do loop agêntico)."""

    async def generate(
        self, *, model: str, system: str, prompt: str, max_tokens: int = 512
    ) -> LLMResponse:
        base = await super().generate(
            model=model, system=system, prompt=prompt, max_tokens=max_tokens
        )
        return base.model_copy(update={"confidence": 0.9 if model.startswith("opus") else 0.2})


class _SpyToolRunner(FakeToolRunner):
    """Conta invocações do loop — prova mecânica de que o loop é o último recurso."""

    def __init__(self) -> None:
        self.calls = 0

    async def run(self, *, model: str, system: str, prompt: str, tools):  # type: ignore[override]
        self.calls += 1
        return await super().run(model=model, system=system, prompt=prompt, tools=tools)


async def test_fake_tool_runner_aggregates_tool_results_with_citations() -> None:
    runner = FakeToolRunner()
    out = await runner.run(
        model="opus-4.8", system="sys", prompt="fale do cohiba", tools=_tools()
    )
    assert out.model == "opus-4.8"
    assert "kg_query" in out.text
    assert out.citations and out.citations[0].source_id == "cigar:cohiba-siglo-vi"
    assert out.cost_usd > 0.0
    assert out.confidence == 1.0
    assert [c.name for c in out.tool_calls] == ["kg_query"]


async def test_fake_tool_runner_low_confidence_without_sources() -> None:
    runner = FakeToolRunner()

    async def _empty(_: str) -> ToolResult:
        return ToolResult(text="", citations=[])

    out = await runner.run(
        model="opus-4.8",
        system="sys",
        prompt="q",
        tools=[AgentTool(name="kg_query", description="d", handler=_empty)],
    )
    assert out.citations == []
    assert out.confidence == 0.0


async def test_cascade_uses_agentic_loop_on_opus_escalation() -> None:
    spy = _SpyToolRunner()
    cascade = Cascade(
        registry=_registry(max_tier=Tier.LARGE, allow_opus_gating=True, token_budget=100000),
        governance=Governance(opus_confidence_threshold=0.6),
        llm=_LowConfidenceLLM(),
        tracer=FakeTracer(),
        kg_version=_ver,
        tool_runner=spy,
        tools=_tools(),
    )
    result = await cascade.resolve(
        "assistant", "pergunta difícil de raciocínio", deterministic=_kg_resolver
    )
    assert result.tier_resolved == Tier.LARGE
    assert spy.calls == 1
    assert result.citations and result.citations[0].source_id == "cigar:cohiba-siglo-vi"


async def test_agentic_loop_never_runs_when_kg_resolves() -> None:
    spy = _SpyToolRunner()
    cascade = Cascade(
        registry=_registry(max_tier=Tier.LARGE, allow_opus_gating=True, token_budget=100000),
        governance=Governance(),
        llm=_LowConfidenceLLM(),
        tracer=FakeTracer(),
        kg_version=_ver,
        tool_runner=spy,
        tools=_tools(),
    )
    result = await cascade.resolve(
        "assistant", "Com o que harmoniza o Cohiba?", deterministic=_kg_resolver
    )
    assert result.tier_resolved == Tier.DETERMINISTIC
    assert spy.calls == 0  # loop é o último recurso: não roda no degrau barato
