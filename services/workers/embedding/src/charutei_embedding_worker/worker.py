"""Embedding Worker — consome eventos e materializa embeddings fora do caminho quente.

Garantias: **idempotência** (dedupe por `event_id`), **cache por conteúdo** (não re-embeda),
**retry/backoff + DLQ** (delegados ao EventBus). Usa os providers via interface — nunca SDK
direto. Eventos tratados: `imagem.enviada` (anilha) e `sku.detectado` (texto de catálogo).
"""

from __future__ import annotations

from charutei_cache.interfaces import VectorIndex
from charutei_contracts import BandImage
from charutei_events import EventBus, EventType, ProcessedRegistry
from charutei_events.models import Event
from charutei_orchestrator import EmbeddingProvider, ImageEmbeddingProvider
from pydantic import BaseModel

from charutei_embedding_worker.cache import ContentEmbeddingCache

BAND_KIND = "band"
CIGAR_TEXT_KIND = "cigar_text"


class ProcessReport(BaseModel):
    processed: int = 0
    skipped_duplicate: int = 0
    failed: int = 0
    provider_calls: int = 0  # nº de chamadas reais ao provider (mede eficácia do cache)


class EmbeddingWorker:
    def __init__(
        self,
        *,
        bus: EventBus,
        processed: ProcessedRegistry,
        image_embed: ImageEmbeddingProvider,
        text_embed: EmbeddingProvider,
        vector_repo: VectorIndex,
        content_cache: ContentEmbeddingCache,
    ) -> None:
        self._bus = bus
        self._processed = processed
        self._image_embed = image_embed
        self._text_embed = text_embed
        self._vec = vector_repo
        self._cache = content_cache

    async def process_once(self, batch: int = 10) -> ProcessReport:
        report = ProcessReport()
        for delivery in await self._bus.poll(batch):
            event = delivery.event
            if await self._processed.seen(event.event_id):
                await self._bus.ack(delivery)
                report.skipped_duplicate += 1
                continue
            try:
                report.provider_calls += await self._handle(event)
                await self._processed.mark(event.event_id)  # marca ANTES do ack (idempotência)
                await self._bus.ack(delivery)
                report.processed += 1
            except Exception as exc:  # noqa: BLE001 — falha vira retry/DLQ, não derruba o worker
                await self._bus.nack(delivery, error=repr(exc))
                report.failed += 1
        return report

    async def drain(self, max_loops: int = 100) -> ProcessReport:
        """Processa até esvaziar (ou estabilizar). Soma os relatórios."""
        total = ProcessReport()
        for _ in range(max_loops):
            report = await self.process_once()
            total.processed += report.processed
            total.skipped_duplicate += report.skipped_duplicate
            total.failed += report.failed
            total.provider_calls += report.provider_calls
            if report.processed == 0 and report.failed == 0 and report.skipped_duplicate == 0:
                break
        return total

    async def _handle(self, event: Event) -> int:
        """Processa um evento. Retorna nº de chamadas reais ao provider (0 = cache hit)."""
        if event.type == EventType.IMAGEM_ENVIADA:
            ref = event.payload["ref"]
            content = event.payload.get("visual_text", ref)
            embedding, calls = await self._embed_cached(content, image=True, ref=ref)
            await self._vec.upsert(BAND_KIND, ref, embedding, {"event_id": event.event_id})
            return calls
        if event.type == EventType.SKU_DETECTADO:
            cigar_id = event.payload["cigar_id"]
            content = event.payload.get("text", cigar_id)
            embedding, calls = await self._embed_cached(content, image=False, ref=cigar_id)
            await self._vec.upsert(CIGAR_TEXT_KIND, cigar_id, embedding, {"cigar_id": cigar_id})
            return calls
        # Eventos não relevantes ao worker são reconhecidos sem efeito.
        return 0

    async def _embed_cached(
        self, content: str, *, image: bool, ref: str
    ) -> tuple[list[float], int]:
        cached = await self._cache.get(content)
        if cached is not None:
            return cached, 0
        if image:
            embedding = await self._image_embed.embed_image(BandImage(ref=ref, visual_text=content))
        else:
            embedding = (await self._text_embed.embed([content]))[0]
        await self._cache.put(content, embedding)
        return embedding, 1
