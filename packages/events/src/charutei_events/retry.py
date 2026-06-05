"""Política de retry: backoff exponencial + jitter, com teto de tentativas → DLQ."""

from __future__ import annotations

import hashlib

from pydantic import BaseModel, Field


class RetryPolicy(BaseModel):
    max_attempts: int = Field(default=3, gt=0)
    base_delay_seconds: float = Field(default=0.5, ge=0.0)
    max_delay_seconds: float = Field(default=30.0, ge=0.0)
    jitter_ratio: float = Field(default=0.2, ge=0.0, le=1.0)

    def should_retry(self, attempts: int) -> bool:
        """True enquanto ainda houver tentativas; caso contrário, vai para a DLQ."""
        return attempts < self.max_attempts

    def delay_for(self, attempts: int, *, key: str = "") -> float:
        """Backoff exponencial determinístico + jitter derivado de `key` (testável)."""
        raw: float = self.base_delay_seconds * float(2 ** max(0, attempts - 1))
        capped: float = min(raw, self.max_delay_seconds)
        if self.jitter_ratio and key:
            digest = int(hashlib.sha256(f"{key}:{attempts}".encode()).hexdigest(), 16)
            frac = (digest % 1000) / 1000.0  # [0,1)
            capped *= 1.0 + self.jitter_ratio * (frac - 0.5) * 2.0
        return max(0.0, capped)
