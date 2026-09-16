"""Ranking de "onde encontro X perto de mim" — puro, determinístico, sem LLM (prompt mestre §31:
não usar agente quando função determinística resolve).

Distância calculada em Python (haversine), não em SQL geoespacial — a tabela de estabelecimentos
começa vazia; buscar todos e ranquear em memória é correto e simples na escala atual.
PostGIS/earthdistance é o follow-up óbvio de escala (mesmo padrão do índice HNSW adiado na Fase 1
— ver docs/PROJECT_UPGRADE_AUDIT.md).
"""

from __future__ import annotations

import math

from charutei_knowledge import AvailabilityStatus, Establishment, ProductAvailability
from pydantic import BaseModel

_EARTH_RADIUS_KM = 6371.0

# Prioridade de ranking — nunca mostra UNAVAILABLE (excluído antes de chegar aqui). Fontes mais
# confiáveis vêm primeiro, dentro do mesmo raio de distância.
_STATUS_PRIORITY: dict[AvailabilityStatus, int] = {
    AvailabilityStatus.CONFIRMED: 0,
    AvailabilityStatus.RECENTLY_CONFIRMED: 1,
    AvailabilityStatus.COMMUNITY_REPORTED: 2,
    AvailabilityStatus.UNKNOWN: 3,
}


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(min(1.0, a)))


class NearbyResult(BaseModel):
    establishment: Establishment
    distance_km: float
    availability: ProductAvailability


def find_nearby(
    establishments: list[Establishment],
    availability: list[ProductAvailability],
    *,
    lat: float,
    lng: float,
    radius_km: float = 25.0,
) -> list[NearbyResult]:
    """`availability` já filtrado por `cigar_id` pelo chamador (LocationRepo.list_availability).

    Candidate generation (só quem tem registro de disponibilidade) → filtro de distância →
    exclui UNAVAILABLE (nunca apresenta como disponível o que é sabidamente indisponível — prompt
    mestre §10) → ranking por (confiabilidade da fonte, distância).
    """
    by_id = {e.id: e for e in establishments}
    results: list[NearbyResult] = []
    for avail in availability:
        if avail.status == AvailabilityStatus.UNAVAILABLE:
            continue
        est = by_id.get(avail.establishment_id)
        if est is None:
            continue
        distance = haversine_km(lat, lng, est.lat, est.lng)
        if distance > radius_km:
            continue
        results.append(NearbyResult(establishment=est, distance_km=distance, availability=avail))
    results.sort(key=lambda r: (_STATUS_PRIORITY[r.availability.status], r.distance_km))
    return results
