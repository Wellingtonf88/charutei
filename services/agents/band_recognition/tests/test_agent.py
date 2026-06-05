"""Testes do Band Recognition Agent: cada degrau do pipeline e o gating de visão."""

from charutei_band_recognition import BandRecognitionAgent, build_band_catalog, default_spec
from charutei_contracts import BandImage, Tier
from charutei_knowledge import InMemoryVectorRepository
from charutei_orchestrator import AgentRegistry, FakeTracer, Governance, build_band_providers

_CIGARS = [
    ("cigar:cohiba-robustos", "Cohiba Robustos"),
    ("cigar:cohiba-siglo-vi", "Cohiba Siglo VI"),
    ("cigar:trinidad-fundadores", "Trinidad Fundadores"),
]


async def _make_agent(*, allow_vision: bool = True) -> BandRecognitionAgent:
    image_embed, ocr, vision = build_band_providers(use_fake=True)
    vec = InMemoryVectorRepository()
    labels = await build_band_catalog(image_embed, vec, _CIGARS)
    registry = AgentRegistry()
    registry.register(default_spec().model_copy(update={"allow_vision_fallback": allow_vision}))
    return BandRecognitionAgent(
        registry=registry,
        governance=Governance(),
        image_embed=image_embed,
        ocr=ocr,
        vision=vision,
        vector_repo=vec,
        tracer=FakeTracer(),
        labels=labels,
    )


async def test_clean_band_resolved_by_embedding() -> None:
    agent = await _make_agent()
    result = await agent.recognize(BandImage(ref="i", visual_text="Trinidad Fundadores"))
    assert result.cigar_id == "cigar:trinidad-fundadores"
    assert result.tier_resolved == Tier.SMALL
    assert result.used_vision_llm is False
    assert result.confidence >= 0.92


async def test_ambiguous_resolved_by_ocr() -> None:
    agent = await _make_agent()
    result = await agent.recognize(
        BandImage(ref="i", visual_text="Cohiba", ocr_text="Cohiba Robustos")
    )
    assert result.cigar_id == "cigar:cohiba-robustos"
    assert result.tier_resolved == Tier.SMALL
    assert result.used_vision_llm is False


async def test_falls_back_to_vision_when_ambiguous_and_no_ocr() -> None:
    agent = await _make_agent()
    result = await agent.recognize(BandImage(ref="i", visual_text="Cohiba", ocr_text=None))
    assert result.used_vision_llm is True
    assert result.tier_resolved == Tier.MEDIUM
    assert result.cost_usd > 0.0


async def test_illegible_band_needs_human() -> None:
    agent = await _make_agent()
    result = await agent.recognize(BandImage(ref="i", visual_text="zzzzz qqqqq", ocr_text=None))
    assert result.cigar_id is None
    assert result.needs_human is True


async def test_vision_disabled_escalates_to_human() -> None:
    agent = await _make_agent(allow_vision=False)
    result = await agent.recognize(BandImage(ref="i", visual_text="Cohiba", ocr_text=None))
    assert result.used_vision_llm is False
    assert result.needs_human is True


async def test_catalog_indexes_all_cigars() -> None:
    image_embed, _, _ = build_band_providers(use_fake=True)
    vec = InMemoryVectorRepository()
    labels = await build_band_catalog(image_embed, vec, _CIGARS)
    assert len(labels) == 3
    assert labels["cigar:cohiba-robustos"] == "Cohiba Robustos"
