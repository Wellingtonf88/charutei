"""Recommendation Engine v1: candidate generation + ranking determinístico (Fase 6 do upgrade)."""

from charutei_recommendation.ranking import CigarProfile, RecommendationCandidate, recommend

__all__ = [
    "CigarProfile",
    "RecommendationCandidate",
    "recommend",
]
