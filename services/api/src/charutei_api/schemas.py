"""Schemas de I/O do BFF (Pydantic)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RecognizeRequest(BaseModel):
    """Captura de anilha. `data_b64` aceita imagem JPEG/PNG em base64 (providers reais);
    `visual_text`/`ocr_text` são o atalho determinístico (demo/CI)."""

    ref: str
    visual_text: str = ""
    ocr_text: str | None = None
    data_b64: str | None = None  # base64 da imagem — usado pelos providers reais


class AddItemRequest(BaseModel):
    cigar_id: str
    quantity: int = Field(default=1, gt=0)


class AskRequest(BaseModel):
    """Pergunta em texto livre para o Assistant (cascata cache→KG→RAG→Opus agêntico)."""

    q: str


class TastingRequest(BaseModel):
    """Registro de degustação de um charuto (F2.5)."""

    cigar_id: str
    rating: int = Field(ge=1, le=5)
    flavors: list[str] = Field(default_factory=list)
    occasion: str = ""
    note: str = ""


class CatalogEntry(BaseModel):
    id: str
    label: str
    strength: str | None = None
    brand: str | None = None
    country: str | None = None
    pairings: list[str] = Field(default_factory=list)
