"""Eval `agentic_loop_groundedness` — o laço agêntico produz respostas ancoradas.

Gate: quando a cascata escala ao degrau Opus (último recurso), o laço de tool-use deve
resolver via ferramentas determinísticas (KG/RAG) e devolver resposta **com citações**
(groundedness=1.0) e custo registrado. Cenário forçado: gerador de baixa confiança dispara a
escalada; as ferramentas MCP (fake) ancoram a resposta em nós do KG semeado. CI-safe.
"""

from __future__ import annotations

from charutei_contracts import Tier
from charutei_knowledge import InMemoryKnowledgeGraph, NodeType, seed_knowledge_graph
from charutei_orchestrator import (
    AgentRegistry,
    AgentSpec,
    Cascade,
    CigarTools,
    FakeToolRunner,
    FakeTracer,
    Governance,
    LLMResponse,
    build_cigar_tools,
    llm_cost,
)

from evals.harness import EvalReport

GATE_GROUNDED = 0.90


class _LowConfidenceLLM:
    """Gerador 'inseguro' p/ Sonnet → força a escalada ao degrau Opus (onde o laço roda)."""

    async def generate(
        self, *, model: str, system: str, prompt: str, max_tokens: int = 512
    ) -> LLMResponse:
        in_tok = max(1, len(system.split()) + len(prompt.split()))
        out_tok = 8
        return LLMResponse(
            text=f"[{model}] resposta",
            model=model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            cost_usd=llm_cost(model, in_tok, out_tok),
            confidence=0.9 if model.startswith("opus") else 0.2,
        )


async def _version() -> int:
    return 1


async def run() -> EvalReport:
    kg = InMemoryKnowledgeGraph()
    await seed_knowledge_graph(kg)
    cigars = await kg.nodes_by_type(NodeType.CIGAR)
    labels = [c.label for c in cigars[:3]]

    registry = AgentRegistry()
    registry.register(
        AgentSpec(
            capability="assistant",
            max_tier=Tier.LARGE,
            token_budget=100_000,
            allow_opus_gating=True,
            allow_agentic_loop=True,
        )
    )
    tools = build_cigar_tools(CigarTools(kg))
    cascade = Cascade(
        registry=registry,
        governance=Governance(),
        llm=_LowConfidenceLLM(),
        tracer=FakeTracer(),
        kg_version=_version,
        tool_runner=FakeToolRunner(),
        tools=tools,
    )

    total = 0
    grounded = 0
    used_loop = 0
    # Perguntas GENERAL (sem gatilho de harmonização/fato) → pula o KG determinístico,
    # gera com baixa confiança → escala → laço agêntico ancora pelas ferramentas.
    for label in labels:
        total += 1
        result = await cascade.resolve("assistant", f"me fale em geral sobre {label}")
        if result.tier_resolved >= Tier.LARGE:
            used_loop += 1
        if result.citations and result.cost_usd > 0.0:
            grounded += 1

    rate = grounded / total if total else 1.0
    loop_rate = used_loop / total if total else 0.0
    return EvalReport(
        name="agentic_loop_groundedness",
        passed=rate >= GATE_GROUNDED and loop_rate >= GATE_GROUNDED,
        summary=(
            f"laço ancorou {rate:.0%} das respostas ({grounded}/{total}) · "
            f"{loop_rate:.0%} escalaram ao laço Opus"
        ),
        details={"grounded_rate": rate, "loop_usage_rate": loop_rate},
    )
