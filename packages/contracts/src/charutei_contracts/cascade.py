"""Contrato do resultado da cascata de inteligência.

A cascata para no degrau mais barato que resolve a requisição. `Tier` registra QUAL
degrau resolveu — base das métricas de FinOps e do gate `cascade_efficiency` (>=70%
do tráfego deve ser resolvido sem Opus).
"""

from __future__ import annotations

from enum import IntEnum

from pydantic import BaseModel, Field


class Tier(IntEnum):
    """Degrau da cascata que resolveu a requisição (menor = mais barato)."""

    CACHE = 1  # cache exato + semântico — custo ~0
    DETERMINISTIC = 2  # SQL / Knowledge Graph / regras — custo ~0
    SMALL = 3  # modelo pequeno + embeddings (Haiku 4.5 / Voyage) — $
    MEDIUM = 4  # modelo médio + RAG (Sonnet 4.6) — $$
    LARGE = 5  # modelo grande (Opus 4.8) — $$$ + porta p/ HITL


class Citation(BaseModel):
    """Fonte que ancora uma resposta (groundedness). Assistente sempre cita."""

    source_id: str
    title: str | None = None
    snippet: str | None = None


class CascadeResult(BaseModel):
    """Saída padronizada de qualquer resolução que passe pelo Orchestrator."""

    answer: str | None = None
    tier_resolved: Tier
    cost_usd: float = Field(default=0.0, ge=0.0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    latency_ms: float = Field(default=0.0, ge=0.0)
    citations: list[Citation] = Field(default_factory=list)
    needs_human: bool = False

    @property
    def used_large_model(self) -> bool:
        """Verdadeiro quando Opus foi acionado — vigiado pelo gate de eficiência."""
        return self.tier_resolved >= Tier.LARGE
