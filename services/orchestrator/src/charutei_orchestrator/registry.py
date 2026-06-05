"""Agent Registry — catálogo declarativo de capabilities.

Cada agente declara: tier máximo permitido, orçamento de tokens e custo estimado. A cascata
e a governança leem daqui — é o que impede, por construção, que uma capability barata escale
para Opus sem autorização. Versionável (cada spec tem `version`).
"""

from __future__ import annotations

from charutei_contracts import Tier
from pydantic import BaseModel, Field

# Modelo concreto por degrau gerador da cascata.
TIER_MODELS: dict[Tier, str] = {
    Tier.SMALL: "haiku-4.5",
    Tier.MEDIUM: "sonnet-4.6",
    Tier.LARGE: "opus-4.8",
}


class AgentSpec(BaseModel):
    """Contrato declarativo de uma capability registrada."""

    capability: str
    version: int = 1
    description: str = ""
    max_tier: Tier = Tier.MEDIUM  # teto de escalada; Opus exige max_tier=LARGE + gating
    token_budget: int = Field(default=4000, gt=0)
    allow_opus_gating: bool = False  # só True habilita o degrau LARGE (ainda sob confiança)
    enabled: bool = True  # kill-switch por agente


class AgentRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, AgentSpec] = {}

    def register(self, spec: AgentSpec) -> None:
        self._specs[spec.capability] = spec

    def get(self, capability: str) -> AgentSpec | None:
        return self._specs.get(capability)

    def require(self, capability: str) -> AgentSpec:
        spec = self._specs.get(capability)
        if spec is None:
            raise KeyError(f"capability não registrada: {capability}")
        return spec

    def all(self) -> list[AgentSpec]:
        return list(self._specs.values())
