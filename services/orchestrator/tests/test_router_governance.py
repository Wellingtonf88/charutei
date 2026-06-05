"""Testes do Router determinístico e da Governance (gating/budget/kill-switch)."""

import pytest
from charutei_contracts import Tier
from charutei_orchestrator import AgentSpec, Governance, GovernanceError
from charutei_orchestrator.router import Intent, classify


def test_router_detects_harmonization() -> None:
    d = classify("Com o que harmoniza o Cohiba?")
    assert d.intent == Intent.HARMONIZATION
    assert d.kg_lookup is True


def test_router_detects_fact_lookup() -> None:
    assert classify("Qual a força do Padrón?").intent == Intent.FACT_LOOKUP


def test_router_defaults_to_general() -> None:
    d = classify("Me conte uma história sobre charutos")
    assert d.intent == Intent.GENERAL
    assert d.kg_lookup is False


def test_kill_switch_blocks_disabled_capability() -> None:
    gov = Governance()
    spec = AgentSpec(capability="x", enabled=False)
    with pytest.raises(GovernanceError):
        gov.ensure_enabled(spec)


def test_effective_max_tier_caps_opus_without_gating() -> None:
    gov = Governance()
    spec = AgentSpec(capability="x", max_tier=Tier.LARGE, allow_opus_gating=False)
    assert gov.effective_max_tier(spec) == Tier.MEDIUM


def test_opus_allowed_only_with_gating_and_low_confidence() -> None:
    gov = Governance(opus_confidence_threshold=0.6)
    spec = AgentSpec(
        capability="x", max_tier=Tier.LARGE, allow_opus_gating=True, token_budget=10000
    )

    # confiança alta → Opus desnecessário
    assert not gov.can_escalate(spec, Tier.LARGE, confidence=0.9, tokens_used=0).allowed
    # confiança baixa → autoriza
    assert gov.can_escalate(spec, Tier.LARGE, confidence=0.3, tokens_used=0).allowed


def test_budget_exceeded_blocks_escalation() -> None:
    gov = Governance()
    spec = AgentSpec(capability="x", max_tier=Tier.LARGE, allow_opus_gating=True, token_budget=100)
    decision = gov.can_escalate(spec, Tier.LARGE, confidence=0.1, tokens_used=150)
    assert decision.allowed is False
    assert "orçamento" in decision.reason
