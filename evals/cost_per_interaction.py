"""Eval `cost_per_interaction` — custo médio por mensagem do assistente.

Gate (critério de aceite #4): custo médio ≤ ~US$0,005/mensagem no dataset (preços jun/2026).
A cascata (cache/KG resolvem a maioria a custo ~0) é o que mantém a média baixa.
"""

from __future__ import annotations

import json
from pathlib import Path

from charutei_orchestrator import cascade_metrics

from evals._fixtures import build_assistant
from evals.harness import EvalReport

_QUERIES = Path(__file__).resolve().parent / "datasets" / "assistant_queries.json"
GATE_AVG_COST_USD = 0.005


async def run() -> EvalReport:
    assistant = await build_assistant()
    queries = json.loads(_QUERIES.read_text(encoding="utf-8"))["queries"]
    results = [await assistant.ask(item["q"]) for item in queries]
    m = cascade_metrics(results)
    return EvalReport(
        name="cost_per_interaction",
        passed=m.avg_cost_usd <= GATE_AVG_COST_USD,
        summary=f"custo médio ${m.avg_cost_usd:.5f}/msg (limite ${GATE_AVG_COST_USD:.3f})",
        details={"avg_cost_usd": m.avg_cost_usd},
    )
