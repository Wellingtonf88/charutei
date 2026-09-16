"""Km de Fumaça: EXPERIENCE_SCORE/KNOWLEDGE_SCORE/CONSUMER_STATUS, determinístico e sem I/O."""

from charutei_scoring.scoring import (
    STATUS_NAMES,
    STATUS_THRESHOLDS,
    Badge,
    ConsumerStatus,
    compute_badges,
    compute_consumer_status,
    compute_experience_score,
    compute_knowledge_score,
    compute_streak,
)

__all__ = [
    "STATUS_NAMES",
    "STATUS_THRESHOLDS",
    "Badge",
    "ConsumerStatus",
    "compute_badges",
    "compute_consumer_status",
    "compute_experience_score",
    "compute_knowledge_score",
    "compute_streak",
]
