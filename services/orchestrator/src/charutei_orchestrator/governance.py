"""Agent Governance — políticas que tornam a cascata segura e barata por construção.

Responsabilidades: kill-switch por agente, teto de tier, orçamento de tokens (degradação
graciosa ao exceder, nunca falha silenciosa) e *gating* do Opus (degrau LARGE só por baixa
confiança + autorização explícita no Registry).
"""

from __future__ import annotations

from charutei_contracts import Tier
from pydantic import BaseModel

from charutei_orchestrator.registry import AgentSpec


class GovernanceError(RuntimeError):
    """Capability desabilitada (kill-switch) ou política violada de forma dura."""


class EscalationDecision(BaseModel):
    allowed: bool
    reason: str


class Governance:
    def __init__(self, opus_confidence_threshold: float = 0.6) -> None:
        # Escala para Opus apenas quando a confiança do degrau anterior < threshold.
        self._opus_threshold = opus_confidence_threshold

    def ensure_enabled(self, spec: AgentSpec) -> None:
        if not spec.enabled:
            raise GovernanceError(f"capability '{spec.capability}' está desabilitada (kill-switch)")

    def effective_max_tier(self, spec: AgentSpec) -> Tier:
        """Teto real: Opus só se o spec autorizar explicitamente o gating."""
        if spec.max_tier >= Tier.LARGE and not spec.allow_opus_gating:
            return Tier.MEDIUM
        return spec.max_tier

    def can_escalate(
        self, spec: AgentSpec, target: Tier, *, confidence: float, tokens_used: int
    ) -> EscalationDecision:
        """Decide se a cascata pode subir para `target`. Resultado sempre logável."""
        if tokens_used >= spec.token_budget:
            return EscalationDecision(
                allowed=False,
                reason=(
                    f"orçamento de tokens excedido ({tokens_used}/{spec.token_budget}) "
                    "— degradação graciosa"
                ),
            )
        if target > self.effective_max_tier(spec):
            return EscalationDecision(
                allowed=False, reason=f"tier {target.name} acima do teto da capability"
            )
        if target >= Tier.LARGE:
            if not spec.allow_opus_gating:
                return EscalationDecision(
                    allowed=False, reason="Opus não autorizado para esta capability"
                )
            if confidence >= self._opus_threshold:
                return EscalationDecision(
                    allowed=False,
                    reason=(
                        f"confiança {confidence:.2f} >= {self._opus_threshold:.2f}; "
                        "Opus desnecessário"
                    ),
                )
        return EscalationDecision(allowed=True, reason=f"escalada para {target.name} autorizada")
