"""Testes de integração dos adaptadores reais de provider.

Cada teste é ignorado silenciosamente se a chave de API correspondente não estiver
presente no ambiente — mesma convenção dos testes de integração com Postgres.

Para rodar:
  ANTHROPIC_API_KEY=... uv run pytest services/orchestrator/tests/test_providers_integration.py -v
"""

from __future__ import annotations

import os

import pytest

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
VOYAGE_KEY = os.environ.get("VOYAGE_API_KEY")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")


@pytest.mark.skipif(not ANTHROPIC_KEY, reason="ANTHROPIC_API_KEY não definida")
async def test_anthropic_llm_provider_haiku_smoke() -> None:
    from charutei_orchestrator.providers import AnthropicLLMProvider

    provider = AnthropicLLMProvider()
    result = await provider.generate(
        model="haiku-4.5",
        system="Responda sempre em português, de forma muito breve.",
        prompt="Diga apenas 'ok'.",
        max_tokens=16,
    )
    assert result.text
    assert result.model == "haiku-4.5"
    assert result.input_tokens > 0
    assert result.output_tokens > 0
    assert result.cost_usd > 0.0


@pytest.mark.skipif(not ANTHROPIC_KEY, reason="ANTHROPIC_API_KEY não definida")
async def test_anthropic_llm_provider_model_mapping() -> None:
    """Garante que todos os IDs internos são mapeados para IDs válidos do SDK."""
    from charutei_orchestrator.providers import AnthropicLLMProvider

    expected = {
        "haiku-4.5": "claude-haiku-4-5",
        "sonnet-4.6": "claude-sonnet-4-6",
        "opus-4.8": "claude-opus-4-8",
    }
    assert expected == AnthropicLLMProvider._MODEL_IDS


@pytest.mark.skipif(not VOYAGE_KEY, reason="VOYAGE_API_KEY não definida")
async def test_voyage_embedding_provider_returns_embeddings() -> None:
    from charutei_orchestrator.providers import VoyageEmbeddingProvider

    provider = VoyageEmbeddingProvider()
    texts = ["Cohiba Siglo VI", "Montecristo No. 2"]
    embeddings = await provider.embed(texts)
    assert len(embeddings) == 2
    assert len(embeddings[0]) > 0
    assert len(embeddings[1]) > 0
    # dimensões consistentes entre si
    assert len(embeddings[0]) == len(embeddings[1])


@pytest.mark.skipif(not VOYAGE_KEY, reason="VOYAGE_API_KEY não definida")
async def test_voyage_image_embedding_provider_text_fallback() -> None:
    from charutei_contracts import BandImage
    from charutei_orchestrator.providers import VoyageImageEmbeddingProvider

    provider = VoyageImageEmbeddingProvider()
    image = BandImage(ref="test-band", visual_text="Cohiba Siglo VI")
    embedding = await provider.embed_image(image)
    assert len(embedding) > 0
    # vetores normalizados — norma ≈ 1 (tolerância 5%)
    import math

    norm = math.sqrt(sum(x * x for x in embedding))
    assert 0.95 <= norm <= 1.05


@pytest.mark.skipif(not GEMINI_KEY, reason="GEMINI_API_KEY não definida")
async def test_gemini_vision_provider_returns_result() -> None:
    from charutei_contracts import BandCandidate, BandImage
    from charutei_orchestrator.providers import GeminiVisionProvider

    provider = GeminiVisionProvider()
    image = BandImage(ref="test-band", visual_text="Cohiba Siglo VI Cuba")
    candidates = [
        BandCandidate(cigar_id="cohiba-siglo-vi", label="Cohiba Siglo VI"),
        BandCandidate(cigar_id="montecristo-no-2", label="Montecristo No. 2"),
    ]
    result = await provider.identify(image, candidates)
    assert result.model == "gemini-3-flash"
    assert result.cost_usd > 0.0
    assert 0.0 <= result.confidence <= 1.0


@pytest.mark.skipif(
    not (ANTHROPIC_KEY and VOYAGE_KEY),
    reason="ANTHROPIC_API_KEY e/ou VOYAGE_API_KEY não definidas",
)
async def test_build_providers_real_returns_real_instances() -> None:
    from charutei_orchestrator.providers import (
        AnthropicLLMProvider,
        VoyageEmbeddingProvider,
        build_providers,
    )

    llm, embed, _tracer = build_providers(use_fake=False)
    assert isinstance(llm, AnthropicLLMProvider)
    assert isinstance(embed, VoyageEmbeddingProvider)


@pytest.mark.skipif(
    not (VOYAGE_KEY and GEMINI_KEY),
    reason="VOYAGE_API_KEY e/ou GEMINI_API_KEY não definidas",
)
async def test_build_band_providers_real_returns_real_instances() -> None:
    from charutei_orchestrator.providers import (
        GeminiVisionProvider,
        VoyageImageEmbeddingProvider,
        build_band_providers,
    )

    img_embed, _ocr, vision = build_band_providers(use_fake=False)
    assert isinstance(img_embed, VoyageImageEmbeddingProvider)
    assert isinstance(vision, GeminiVisionProvider)
