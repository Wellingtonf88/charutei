"""Fila de revisão humana (HITL) — conflitos de ingestão não se resolvem em silêncio.

Quando um SKU já existe com um fato de alta confiança diferente do catálogo, o item vai para
revisão em vez de sobrescrever (evita corromper o KG com dado divergente).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class ReviewItem(BaseModel):
    cigar_id: str
    field: str
    existing: str | None
    incoming: str | None
    reason: str = "conflito de fato de alta confiança"


@runtime_checkable
class ReviewQueue(Protocol):
    async def submit(self, item: ReviewItem) -> None: ...


class InMemoryReviewQueue:
    def __init__(self) -> None:
        self.items: list[ReviewItem] = []

    async def submit(self, item: ReviewItem) -> None:
        self.items.append(item)
