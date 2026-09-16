"""Testes do Location Intelligence: haversine, ranking, geocoding fake."""

import math

from charutei_knowledge import AvailabilityStatus, Establishment, ProductAvailability
from charutei_location import (
    FakeGeocodingProvider,
    find_nearby,
    haversine_km,
)

_EARTH_RADIUS_KM = 6371.0
# Coordenadas de referência p/ testes de ranking (não dependem do valor exato da distância).
_SP_LAT, _SP_LNG = -23.5505, -46.6333
_SANTOS_LAT, _SANTOS_LNG = -23.9608, -46.3339


def test_haversine_one_degree_on_equator_matches_formula() -> None:
    # No equador, 1° de longitude = R * (π/180) — geometricamente exato, não um valor "de cabeça".
    km = haversine_km(0.0, 0.0, 0.0, 1.0)
    expected = _EARTH_RADIUS_KM * math.pi / 180
    assert abs(km - expected) < 0.01


def test_haversine_antipodal_points_equal_half_circumference() -> None:
    km = haversine_km(0.0, 0.0, 0.0, 180.0)
    assert abs(km - math.pi * _EARTH_RADIUS_KM) < 0.01


def test_haversine_zero_for_same_point() -> None:
    assert haversine_km(_SP_LAT, _SP_LNG, _SP_LAT, _SP_LNG) == 0.0


def _est(id_: str, lat: float, lng: float) -> Establishment:
    return Establishment(id=id_, name=f"Loja {id_}", lat=lat, lng=lng)


def _avail(est_id: str, status: AvailabilityStatus) -> ProductAvailability:
    return ProductAvailability(
        id=f"avail-{est_id}", establishment_id=est_id, cigar_id="cigar:x", status=status
    )


def test_find_nearby_filters_by_radius() -> None:
    near = _est("near", _SP_LAT, _SP_LNG)
    far = _est("far", _SANTOS_LAT, _SANTOS_LNG)
    availability = [
        _avail("near", AvailabilityStatus.CONFIRMED),
        _avail("far", AvailabilityStatus.CONFIRMED),
    ]

    small_radius = find_nearby([near, far], availability, lat=_SP_LAT, lng=_SP_LNG, radius_km=10)
    assert [r.establishment.id for r in small_radius] == ["near"]

    big_radius = find_nearby([near, far], availability, lat=_SP_LAT, lng=_SP_LNG, radius_km=200)
    assert {r.establishment.id for r in big_radius} == {"near", "far"}
    assert big_radius[0].establishment.id == "near"  # mais perto primeiro


def test_find_nearby_excludes_unavailable() -> None:
    est = _est("est-1", _SP_LAT, _SP_LNG)
    availability = [_avail("est-1", AvailabilityStatus.UNAVAILABLE)]
    assert find_nearby([est], availability, lat=_SP_LAT, lng=_SP_LNG, radius_km=50) == []


def test_find_nearby_ranks_by_status_before_distance() -> None:
    # "confirmed" mais longe vence "community_reported" mais perto, dentro do mesmo raio
    closer_but_unreliable = _est("closer", _SP_LAT, _SP_LNG)
    farther_but_confirmed = _est("farther", _SANTOS_LAT, _SANTOS_LNG)
    availability = [
        _avail("closer", AvailabilityStatus.COMMUNITY_REPORTED),
        _avail("farther", AvailabilityStatus.CONFIRMED),
    ]
    results = find_nearby(
        [closer_but_unreliable, farther_but_confirmed],
        availability,
        lat=_SP_LAT,
        lng=_SP_LNG,
        radius_km=200,
    )
    assert results[0].establishment.id == "farther"


async def test_fake_geocoding_deterministic_and_in_range() -> None:
    provider = FakeGeocodingProvider()
    first = await provider.geocode("Av. Paulista, São Paulo")
    second = await provider.geocode("Av. Paulista, São Paulo")
    assert first == second  # determinístico
    assert first is not None
    lat, lng = first
    assert -90 <= lat <= 90
    assert -180 <= lng <= 180


async def test_fake_geocoding_empty_address_returns_none() -> None:
    assert await FakeGeocodingProvider().geocode("   ") is None
