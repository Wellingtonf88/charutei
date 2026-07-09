"""Testes do Supervisor (S15): roteamento determinístico, kill-switch e dispatch."""

import pytest
from charutei_contracts import Tier
from charutei_orchestrator import (
    AgentRegistry,
    AgentSpec,
    GovernanceError,
    RequestKind,
    Supervisor,
)


def _registry(enabled: bool = True) -> AgentRegistry:
    reg = AgentRegistry()
    reg.register(AgentSpec(capability="band_recognition", enabled=enabled))
    reg.register(AgentSpec(capability="assistant", max_tier=Tier.LARGE, allow_opus_gating=True))
    return reg


def test_route_maps_kind_to_capability() -> None:
    sup = Supervisor(_registry())
    assert sup.route(RequestKind.BAND_IMAGE).capability == "band_recognition"
    assert sup.route(RequestKind.ASSISTANT_TEXT).capability == "assistant"


def test_route_unregistered_capability_raises() -> None:
    sup = Supervisor(_registry())
    with pytest.raises(KeyError):
        sup.route(RequestKind.CATALOG_INGEST)  # cigar_intelligence não registrado


def test_route_respects_kill_switch() -> None:
    sup = Supervisor(_registry(enabled=False))
    with pytest.raises(GovernanceError):
        sup.route(RequestKind.BAND_IMAGE)


async def test_dispatch_calls_registered_handler() -> None:
    sup = Supervisor(_registry())
    seen: list[str] = []

    async def _band_handler(payload: str) -> str:
        seen.append(payload)
        return f"reconhecido:{payload}"

    sup.register("band_recognition", _band_handler)
    result = await sup.dispatch(RequestKind.BAND_IMAGE, "anilha-x")
    assert result == "reconhecido:anilha-x"
    assert seen == ["anilha-x"]


async def test_dispatch_without_handler_raises() -> None:
    sup = Supervisor(_registry())  # assistant registrado no registry, mas sem handler
    with pytest.raises(KeyError):
        await sup.dispatch(RequestKind.ASSISTANT_TEXT, "pergunta")


def test_allow_agentic_loop_defaults_false_and_opt_in() -> None:
    assert AgentSpec(capability="x").allow_agentic_loop is False
    assert AgentSpec(capability="assistant", allow_agentic_loop=True).allow_agentic_loop is True
