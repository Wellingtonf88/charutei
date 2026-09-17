"""Recommendation Engine v1 — puro, determinístico, sem LLM (prompt mestre §31: não usar agente
quando função determinística resolve — mesmo raciocínio que já manteve `/nearby` fora do
Supervisor na Fase 4).

Candidate generation (catálogo inteiro, menos o que o usuário já tem/avaliou) → ranking por
afinidade de marca/país/força com o que o usuário avaliou bem (rating >= 4) ou já possui.

Sem fallback de popularidade para usuários sem histórico (v1): exigiria uma query cross-user que
não existe hoje em OltpRepository (list_tastings/list_collections são escopados por usuário) —
ver docs/DATA_MODEL.md, Fase 6, decisão de escopo. Usuário sem sinal recebe lista vazia — honesto,
não fabrica popularidade sem o dado que a sustentaria.
"""

from __future__ import annotations

from pydantic import BaseModel

_BRAND_WEIGHT = 2
_COUNTRY_WEIGHT = 1
_STRENGTH_WEIGHT = 1


class CigarProfile(BaseModel):
    cigar_id: str
    label: str
    brand: str | None = None
    country: str | None = None
    strength: str | None = None


class RecommendationCandidate(BaseModel):
    cigar_id: str
    label: str
    score: int
    reasons: list[str]


def recommend(
    catalog: list[CigarProfile],
    *,
    liked_brands: set[str],
    liked_countries: set[str],
    liked_strengths: set[str],
    exclude_cigar_ids: set[str],
    limit: int = 10,
) -> list[RecommendationCandidate]:
    candidates: list[RecommendationCandidate] = []
    for cigar in catalog:
        if cigar.cigar_id in exclude_cigar_ids:
            continue
        score = 0
        reasons: list[str] = []
        if cigar.brand and cigar.brand in liked_brands:
            score += _BRAND_WEIGHT
            reasons.append(f"mesma marca: {cigar.brand}")
        if cigar.country and cigar.country in liked_countries:
            score += _COUNTRY_WEIGHT
            reasons.append(f"mesmo país: {cigar.country}")
        if cigar.strength and cigar.strength in liked_strengths:
            score += _STRENGTH_WEIGHT
            reasons.append(f"mesma força: {cigar.strength}")
        if score > 0:
            candidates.append(
                RecommendationCandidate(
                    cigar_id=cigar.cigar_id, label=cigar.label, score=score, reasons=reasons
                )
            )
    candidates.sort(key=lambda c: (-c.score, c.label))
    return candidates[:limit]
