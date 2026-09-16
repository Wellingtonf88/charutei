"""Schemas de I/O do BFF (Pydantic)."""

from __future__ import annotations

from charutei_scoring import Badge, ConsumerStatus
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
    # None preserva o comportamento atual (escreve no humidor padrão do usuário). Preenchido,
    # escreve numa collection específica — validada como do próprio usuário no handler.
    collection_id: str | None = None


class CreateCollectionRequest(BaseModel):
    name: str


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


class ProfileOut(BaseModel):
    """Passaporte de experiências (Fase 3 do upgrade — Km de Fumaça). REPUTATION_SCORE e
    INFLUENCE_SCORE não aparecem aqui: dependem de sinal social que só existe a partir da Fase 7
    (Community) — sem dado real, não expomos um "0" enganoso."""

    total_tastings: int
    humidor_size: int  # soma de items em TODAS as collections do usuário (não só o humidor padrão)
    avg_rating: float
    top_flavors: list[str] = Field(default_factory=list)
    distinct_flavors: int
    distinct_countries: int
    streak_days: int
    experience_score: int
    knowledge_score: int
    consumer_status: ConsumerStatus
    badges: list[Badge]
