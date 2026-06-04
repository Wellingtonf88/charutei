"""Smoke test da S0: o contrato da cascata importa e se comporta como esperado."""

from charutei_contracts import CascadeResult, Citation, Tier


def test_tier_ordering_cheapest_first() -> None:
    assert Tier.CACHE < Tier.DETERMINISTIC < Tier.SMALL < Tier.MEDIUM < Tier.LARGE


def test_cache_result_is_free_and_not_large() -> None:
    result = CascadeResult(answer="ok", tier_resolved=Tier.CACHE)
    assert result.cost_usd == 0.0
    assert result.used_large_model is False


def test_opus_flagged_as_large_model() -> None:
    result = CascadeResult(answer="raciocínio difícil", tier_resolved=Tier.LARGE)
    assert result.used_large_model is True


def test_citations_round_trip() -> None:
    result = CascadeResult(
        answer="harmoniza com rum envelhecido",
        tier_resolved=Tier.DETERMINISTIC,
        citations=[Citation(source_id="kg:cigar/123", title="Harmonização")],
    )
    assert result.citations[0].source_id == "kg:cigar/123"
    assert result.needs_human is False
