"""Schemas de I/O do BFF (Pydantic)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RecognizeRequest(BaseModel):
    """Captura de anilha. Em produção, a imagem é enviada (multipart) e o embedding vem do
    Voyage multimodal; `visual_text`/`ocr_text` são o atalho determinístico do MVP."""

    ref: str
    visual_text: str = ""
    ocr_text: str | None = None


class AddItemRequest(BaseModel):
    cigar_id: str
    quantity: int = Field(default=1, gt=0)


class CatalogEntry(BaseModel):
    id: str
    label: str
    strength: str | None = None
    brand: str | None = None
    country: str | None = None
    pairings: list[str] = Field(default_factory=list)
