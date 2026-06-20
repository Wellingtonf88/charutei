"""Supervisor — roteador DETERMINÍSTICO de agentes especialistas (sem LLM).

Centraliza, num só lugar, a decisão de *qual* especialista atende cada requisição e a
aplicação do kill-switch/registro (antes espalhada no `AppContext`). O tipo de payload
desambigua deterministicamente o especialista (imagem → band; texto → assistant; ingestão →
catalog); a classificação fina de intenção do texto continua no `router.classify`, dentro da
cascata do Assistant — o Supervisor não duplica essa lógica.

Não é um agente: não raciocina nem chama LLM. É a camada de orquestração que torna o sistema
multi-agêntico (Supervisor + especialistas), mantendo "LLM é o último recurso".
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Any

from charutei_orchestrator.governance import Governance
from charutei_orchestrator.registry import AgentRegistry, AgentSpec


class RequestKind(StrEnum):
    """Natureza da requisição — determina o especialista sem ambiguidade."""

    BAND_IMAGE = "band_image"  # → band_recognition
    ASSISTANT_TEXT = "assistant_text"  # → assistant
    CATALOG_INGEST = "catalog_ingest"  # → cigar_intelligence (offline)


# Mapa fixo requisição → capability registrada. Determinístico, sem LLM.
_KIND_CAPABILITY: dict[RequestKind, str] = {
    RequestKind.BAND_IMAGE: "band_recognition",
    RequestKind.ASSISTANT_TEXT: "assistant",
    RequestKind.CATALOG_INGEST: "cigar_intelligence",
}

# Entrypoint de um especialista: recebe o payload tipado e devolve o resultado do agente.
AgentHandler = Callable[[Any], Awaitable[Any]]


class Supervisor:
    """Despacha requisições para o especialista certo, sob o registro/governança."""

    def __init__(self, registry: AgentRegistry, governance: Governance | None = None) -> None:
        self._registry = registry
        self._gov = governance or Governance()
        self._handlers: dict[str, AgentHandler] = {}

    def register(self, capability: str, handler: AgentHandler) -> None:
        """Liga uma capability ao entrypoint do seu agente especialista."""
        self._handlers[capability] = handler

    def capability_for(self, kind: RequestKind) -> str:
        return _KIND_CAPABILITY[kind]

    def route(self, kind: RequestKind) -> AgentSpec:
        """Resolve o `AgentSpec` do especialista e aplica o kill-switch. Sem LLM."""
        spec = self._registry.require(self.capability_for(kind))
        self._gov.ensure_enabled(spec)  # GovernanceError se a capability estiver desabilitada
        return spec

    async def dispatch(self, kind: RequestKind, payload: Any) -> Any:
        """Roteia e executa: valida o registro/kill-switch e chama o handler do especialista."""
        spec = self.route(kind)
        handler = self._handlers.get(spec.capability)
        if handler is None:
            raise KeyError(
                f"nenhum handler registrado para a capability '{spec.capability}'"
            )
        return await handler(payload)
