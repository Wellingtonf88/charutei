"""Location Intelligence: ranking por distância + GeocodingProvider (Fase 4 do upgrade)."""

from charutei_location.providers import (
    FakeGeocodingProvider,
    GeocodingProvider,
    RealGeocodingProvider,
    build_geocoding_provider,
)
from charutei_location.ranking import NearbyResult, find_nearby, haversine_km

__all__ = [
    "FakeGeocodingProvider",
    "GeocodingProvider",
    "RealGeocodingProvider",
    "build_geocoding_provider",
    "NearbyResult",
    "find_nearby",
    "haversine_km",
]
