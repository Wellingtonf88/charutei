"""Contrato de I/O do Band Recognition Agent (S3).

Entrada: imagem de anilha. Saída: `{cigar_id, confidence, candidates[], needs_human}` —
exatamente o que o blueprint especifica. `tier_resolved`/`used_vision_llm` alimentam o eval
`band_recognition` (gate: ≥80% resolvido sem LLM de visão).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from charutei_contracts.cascade import Tier


class BandImage(BaseModel):
    """Imagem de anilha capturada.

    Em produção: `data_b64` (JPEG/PNG base64) ou `url` alimentam Voyage multimodal + Gemini.
    Em CI/demo: `visual_text`/`ocr_text` são usados pelos providers fake.
    """

    ref: str  # referência no object storage (ou id da captura)
    visual_text: str = ""  # simula o que o modelo multimodal "lê" na anilha (fixtures)
    ocr_text: str | None = None  # texto extraído por OCR; None = ainda não rodou
    data_b64: str | None = None  # imagem em base64 (produção — providers reais)
    url: str | None = None  # URL pública da imagem (alternativa ao base64)


class BandCandidate(BaseModel):
    cigar_id: str
    label: str | None = None
    score: float = Field(ge=0.0, le=1.0)


class BandRecognitionResult(BaseModel):
    cigar_id: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    candidates: list[BandCandidate] = Field(default_factory=list)
    needs_human: bool = False
    used_vision_llm: bool = False  # True quando o fallback de visão (Gemini Flash) foi acionado
    tier_resolved: Tier = Tier.SMALL
    cost_usd: float = Field(default=0.0, ge=0.0)
