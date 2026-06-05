"""Métricas da cascata — base do dashboard Langfuse e dos gates de eval.

Métrica-âncora do projeto: **% do tráfego resolvido sem o modelo grande (Opus)** e
**custo médio por interação**. Empurrar a primeira para cima e a segunda para baixo.
"""

from __future__ import annotations

from collections import Counter

from charutei_contracts import CascadeResult, Tier
from pydantic import BaseModel


class CascadeMetrics(BaseModel):
    total: int
    by_tier: dict[str, int]
    pct_without_opus: float
    avg_cost_usd: float

    def format_distribution(self) -> str:
        if self.total == 0:
            return "sem tráfego"
        parts = [f"{name} {count / self.total:.0%}" for name, count in self.by_tier.items()]
        return " · ".join(parts)


def cascade_metrics(results: list[CascadeResult]) -> CascadeMetrics:
    total = len(results)
    counter: Counter[str] = Counter(r.tier_resolved.name for r in results)
    without_opus = sum(1 for r in results if not r.used_large_model)
    cost = sum(r.cost_usd for r in results)
    return CascadeMetrics(
        total=total,
        by_tier={t.name: counter.get(t.name, 0) for t in Tier},
        pct_without_opus=(without_opus / total) if total else 1.0,
        avg_cost_usd=(cost / total) if total else 0.0,
    )
