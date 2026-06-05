"""Band Recognition Agent (síncrono).

Pipeline cost-aware: embedding multimodal → ANN (pgvector) → desempate por OCR → fallback
a LLM de visão (Gemini Flash) **só quando ambíguo** e autorizado pela governança. A maioria
resolve nos degraus baratos (alvo: ≥80% sem visão). Nunca inventa: incerto → `needs_human`.
"""

from __future__ import annotations

import re
import unicodedata

from charutei_cache.interfaces import VectorIndex
from charutei_contracts import BandCandidate, BandImage, BandRecognitionResult, Tier
from charutei_orchestrator import (
    AgentRegistry,
    AgentSpec,
    Governance,
    ImageEmbeddingProvider,
    OCRProvider,
    Tracer,
    TraceRecord,
    VisionProvider,
)
from charutei_orchestrator.providers import EMBED_PRICING, IMAGE_TOKENS

from charutei_band_recognition.catalog import BAND_KIND

CAPABILITY = "band_recognition"
_EMBED_MODEL = "voyage-multimodal-4"


def _strip(text: str) -> str:
    """Minúsculas, sem acentos e sem pontuação — tokens estáveis p/ casamento por OCR."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()


def default_spec() -> AgentSpec:
    """Spec recomendada: visão autorizada (gated), Opus de visão fora do MVP."""
    return AgentSpec(
        capability=CAPABILITY,
        description="Reconhecimento de anilha por embedding+OCR, com fallback de visão",
        max_tier=Tier.MEDIUM,
        token_budget=4000,
        allow_vision_fallback=True,
    )


class BandRecognitionAgent:
    def __init__(
        self,
        *,
        registry: AgentRegistry,
        governance: Governance,
        image_embed: ImageEmbeddingProvider,
        ocr: OCRProvider,
        vision: VisionProvider,
        vector_repo: VectorIndex,
        tracer: Tracer,
        labels: dict[str, str],
        accept_threshold: float = 0.92,
        margin: float = 0.08,
        k: int = 3,
    ) -> None:
        self._registry = registry
        self._gov = governance
        self._embed = image_embed
        self._ocr = ocr
        self._vision = vision
        self._vec = vector_repo
        self._tracer = tracer
        self._labels = labels
        self._accept = accept_threshold
        self._margin = margin
        self._k = k

    async def recognize(self, image: BandImage) -> BandRecognitionResult:
        spec = self._registry.require(CAPABILITY)
        self._gov.ensure_enabled(spec)
        embed_cost = EMBED_PRICING[_EMBED_MODEL] * IMAGE_TOKENS

        # ---- Degrau 3: embedding multimodal + ANN ----
        emb = await self._embed.embed_image(image, model=_EMBED_MODEL)
        hits = await self._vec.ann_search(BAND_KIND, emb, k=self._k)
        candidates = [
            BandCandidate(cigar_id=cid, label=self._labels.get(cid), score=max(0.0, min(1.0, s)))
            for cid, s in hits
        ]
        await self._trace("embedding_ann", Tier.SMALL, cost=embed_cost)

        if not candidates:
            return BandRecognitionResult(
                tier_resolved=Tier.SMALL, needs_human=True, cost_usd=embed_cost
            )

        top = candidates[0]
        runner_up = candidates[1].score if len(candidates) > 1 else 0.0

        # Caso claro: top-1 forte e destacado → resolve sem OCR nem visão.
        if top.score >= self._accept and (top.score - runner_up) >= self._margin:
            return BandRecognitionResult(
                cigar_id=top.cigar_id,
                confidence=top.score,
                candidates=candidates,
                tier_resolved=Tier.SMALL,
                cost_usd=embed_cost,
            )

        # ---- Degrau 3: desempate por OCR ----
        ocr_text = await self._ocr.extract_text(image)
        await self._trace("ocr", Tier.SMALL)
        if ocr_text:
            matched = self._match_by_ocr(ocr_text, candidates)
            if len(matched) == 1:
                return BandRecognitionResult(
                    cigar_id=matched[0].cigar_id,
                    confidence=max(top.score, 0.9),  # OCR confirmou a marca/modelo
                    candidates=candidates,
                    tier_resolved=Tier.SMALL,
                    cost_usd=embed_cost,
                )

        # ---- Fallback de visão (gated): só ambíguo + autorizado ----
        decision = self._gov.can_use_vision(spec)
        if decision.allowed:
            vres = await self._vision.identify(image, candidates)
            await self._trace("vision_llm", Tier.MEDIUM, model=vres.model, cost=vres.cost_usd)
            if vres.cigar_id and vres.confidence > 0.0:
                return BandRecognitionResult(
                    cigar_id=vres.cigar_id,
                    confidence=vres.confidence,
                    candidates=candidates,
                    used_vision_llm=True,
                    tier_resolved=Tier.MEDIUM,
                    cost_usd=embed_cost + vres.cost_usd,
                )

        # Incerto e sem como confirmar → humano decide (não chuta).
        return BandRecognitionResult(
            cigar_id=None,
            confidence=top.score,
            candidates=candidates,
            needs_human=True,
            tier_resolved=Tier.SMALL,
            cost_usd=embed_cost,
        )

    def _match_by_ocr(self, ocr_text: str, candidates: list[BandCandidate]) -> list[BandCandidate]:
        ocr_tokens = set(_strip(ocr_text).split())
        out: list[BandCandidate] = []
        for cand in candidates:
            label = cand.label or cand.cigar_id
            label_tokens = set(_strip(label).split())
            if label_tokens and label_tokens <= ocr_tokens:
                out.append(cand)
        return out

    async def _trace(
        self, name: str, tier: Tier, *, model: str | None = None, cost: float = 0.0
    ) -> None:
        await self._tracer.log(TraceRecord(name=name, tier=int(tier), model=model, cost_usd=cost))
