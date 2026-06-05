"""Eval `cascade_efficiency` — % do tráfego resolvido sem Opus + custo médio por mensagem.

Gate (Anexo C / critérios de aceite): >=70% sem Opus e custo médio <= ~US$0,005/msg.
Roda a cascata real (com fakes determinísticos) sobre um dataset versionado de consultas.
"""

from __future__ import annotations

import json
from pathlib import Path

from charutei_orchestrator import cascade_metrics

from evals._fixtures import build_assistant_harness
from evals.harness import EvalReport

_QUERIES = Path(__file__).resolve().parent / "datasets" / "assistant_queries.json"

GATE_PCT_WITHOUT_OPUS = 0.70
GATE_AVG_COST_USD = 0.005


async def run() -> EvalReport:
    harness = await build_assistant_harness()
    queries = json.loads(_QUERIES.read_text(encoding="utf-8"))["queries"]
    results = [await harness.ask(item["q"]) for item in queries]
    m = cascade_metrics(results)

    passed = m.pct_without_opus >= GATE_PCT_WITHOUT_OPUS and m.avg_cost_usd <= GATE_AVG_COST_USD
    return EvalReport(
        name="cascade_efficiency",
        passed=passed,
        summary=(
            f"{m.pct_without_opus:.0%} sem Opus · custo médio ${m.avg_cost_usd:.5f}/msg · "
            f"distribuição: {m.format_distribution()}"
        ),
        details={
            "pct_without_opus": m.pct_without_opus,
            "avg_cost_usd": m.avg_cost_usd,
        },
    )
