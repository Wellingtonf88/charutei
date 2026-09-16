"""GeocodingProvider — abstração de vendor externo (Protocol + Fake), mesmo padrão de
LLMProvider/EmbeddingProvider em services/orchestrator/providers.py.

`PlacesProvider` e `MapsProvider` (citados no prompt mestre) não têm chamador nesta fase — não
construídos (ver docs/DATA_MODEL.md, Fase 4, decisões de escopo).
"""

from __future__ import annotations

import hashlib
import os
from typing import Protocol, runtime_checkable


@runtime_checkable
class GeocodingProvider(Protocol):
    async def geocode(self, address: str) -> tuple[float, float] | None:
        """Endereço/cidade em texto livre → (lat, lng). None se não resolveu."""
        ...


class FakeGeocodingProvider:
    """Determinístico: hash do texto → coordenadas estáveis dentro de faixas válidas. Zero
    custo/rede — mesmo espírito de FakeLLMProvider/FakeEmbeddingProvider."""

    async def geocode(self, address: str) -> tuple[float, float] | None:
        text = address.strip()
        if not text:
            return None
        h = int(hashlib.sha256(text.lower().encode()).hexdigest(), 16)
        lat = -90.0 + (h % 18000) / 100.0
        lng = -180.0 + ((h >> 20) % 36000) / 100.0
        return (lat, lng)


class RealGeocodingProvider:
    """Placeholder até a decisão de vendor (Google Geocoding? Mapbox? Nominatim/OSM?) — decisão
    de negócio/custo, não técnica. Quando a chave existir, troque por um adaptador real seguindo
    o padrão de AnthropicLLMProvider (lazy-import do SDK, api_key do env) — o resto do sistema
    (endpoint /nearby, testes) não muda, só a implementação injetada."""

    async def geocode(self, address: str) -> tuple[float, float] | None:
        raise NotImplementedError(
            "GeocodingProvider real ainda não tem vendor escolhido (Google/Mapbox/Nominatim). "
            "Use USE_FAKE_PROVIDERS=true, ou implemente o adaptador quando a decisão existir."
        )


def build_geocoding_provider(use_fake: bool | None = None) -> GeocodingProvider:
    """Mesmo padrão de build_providers/build_band_providers: lê USE_FAKE_PROVIDERS quando
    `use_fake` não é passado."""
    if use_fake is None:
        use_fake = os.environ.get("USE_FAKE_PROVIDERS", "true").lower() in {"1", "true", "yes"}
    return FakeGeocodingProvider() if use_fake else RealGeocodingProvider()
