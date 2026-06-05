"""Testes do LangfuseTracer com um cliente fake (sem SDK/rede) — valida o mapeamento."""

from typing import Any

from charutei_contracts import Tier
from charutei_orchestrator import TraceRecord
from charutei_orchestrator.langfuse_tracer import LangfuseTracer


class _FakeTrace:
    def __init__(self) -> None:
        self.generations: list[dict[str, Any]] = []
        self.spans: list[dict[str, Any]] = []

    def generation(self, **kw: Any) -> None:
        self.generations.append(kw)

    def span(self, **kw: Any) -> None:
        self.spans.append(kw)


class _FakeLangfuse:
    def __init__(self) -> None:
        self.traces: dict[str, _FakeTrace] = {}
        self.scores: list[dict[str, Any]] = []
        self.flushed = 0

    def trace(self, *, id: str, **kw: Any) -> _FakeTrace:
        t = _FakeTrace()
        self.traces[id] = t
        return t

    def score(self, **kw: Any) -> None:
        self.scores.append(kw)

    def flush(self) -> None:
        self.flushed += 1


async def test_generation_and_span_grouped_by_trace() -> None:
    fake = _FakeLangfuse()
    tracer = LangfuseTracer(client=fake)

    # passo determinístico (sem modelo) → span; geração (com modelo) → generation
    await tracer.log(
        TraceRecord(
            name="deterministic",
            tier=int(Tier.DETERMINISTIC),
            trace_id="r1",
            capability="assistant",
        )
    )
    await tracer.log(
        TraceRecord(
            name="generation",
            tier=int(Tier.MEDIUM),
            model="sonnet-4.6",
            input_tokens=30,
            output_tokens=20,
            cost_usd=0.0004,
            trace_id="r1",
            capability="assistant",
        )
    )

    assert set(fake.traces) == {"r1"}  # mesma requisição → uma trace
    trace = fake.traces["r1"]
    assert len(trace.spans) == 1
    assert len(trace.generations) == 1
    gen = trace.generations[0]
    assert gen["model"] == "sonnet-4.6"
    assert gen["usage"]["total_cost"] == 0.0004
    assert gen["metadata"]["tier"] == "MEDIUM"


async def test_score_and_flush() -> None:
    fake = _FakeLangfuse()
    tracer = LangfuseTracer(client=fake)
    tracer.score(trace_id="r1", name="groundedness", value=1.0)
    tracer.flush()
    assert fake.scores[0]["name"] == "groundedness"
    assert fake.flushed == 1
