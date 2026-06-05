"""Testes do Embedding Worker: materialização, idempotência, cache por conteúdo e DLQ."""

from charutei_cache import InMemoryKV
from charutei_contracts import BandImage
from charutei_embedding_worker import (
    BAND_KIND,
    ContentEmbeddingCache,
    EmbeddingWorker,
)
from charutei_events import (
    Event,
    EventType,
    InMemoryEventBus,
    InMemoryProcessedRegistry,
    RetryPolicy,
)
from charutei_knowledge import InMemoryVectorRepository
from charutei_orchestrator import FakeEmbeddingProvider, FakeImageEmbeddingProvider


def _make(bus: InMemoryEventBus) -> tuple[EmbeddingWorker, InMemoryVectorRepository]:
    vec = InMemoryVectorRepository()
    worker = EmbeddingWorker(
        bus=bus,
        processed=InMemoryProcessedRegistry(),
        image_embed=FakeImageEmbeddingProvider(),
        text_embed=FakeEmbeddingProvider(),
        vector_repo=vec,
        content_cache=ContentEmbeddingCache(InMemoryKV()),
    )
    return worker, vec


async def test_processes_image_event_and_stores_vector() -> None:
    bus = InMemoryEventBus()
    worker, vec = _make(bus)
    await bus.publish(
        Event(type=EventType.IMAGEM_ENVIADA, payload={"ref": "img-1", "visual_text": "Cohiba"})
    )
    report = await worker.drain()
    assert report.processed == 1
    assert report.provider_calls == 1
    hits = await vec.ann_search(
        BAND_KIND,
        await FakeImageEmbeddingProvider().embed_image(
            BandImage(ref="img-1", visual_text="Cohiba")
        ),
    )
    assert hits and hits[0][0] == "img-1"


async def test_duplicate_event_is_idempotent() -> None:
    bus = InMemoryEventBus()
    worker, _ = _make(bus)
    evt = Event(
        event_id="dup",
        type=EventType.SKU_DETECTADO,
        payload={"cigar_id": "cigar:x", "text": "Cohiba Robustos"},
    )
    await bus.publish(evt)
    await bus.publish(evt)  # mesmo event_id chega 2×
    report = await worker.drain()
    assert report.processed == 1
    assert report.skipped_duplicate == 1


async def test_content_cache_avoids_reembedding() -> None:
    bus = InMemoryEventBus()
    worker, _ = _make(bus)
    # Dois eventos, refs diferentes, MESMO conteúdo → segundo deve ser cache hit.
    await bus.publish(
        Event(
            type=EventType.IMAGEM_ENVIADA,
            payload={"ref": "a", "visual_text": "Trinidad Fundadores"},
        )
    )
    await bus.publish(
        Event(
            type=EventType.IMAGEM_ENVIADA,
            payload={"ref": "b", "visual_text": "Trinidad Fundadores"},
        )
    )
    report = await worker.drain()
    assert report.processed == 2
    assert report.provider_calls == 1  # só o primeiro chamou o provider


class _FailingImageEmbed:
    async def embed_image(
        self, image: BandImage, *, model: str = "voyage-multimodal-4"
    ) -> list[float]:
        raise RuntimeError("provider indisponível")


async def test_failure_retries_then_dead_letters() -> None:
    bus = InMemoryEventBus(RetryPolicy(max_attempts=2))
    vec = InMemoryVectorRepository()
    worker = EmbeddingWorker(
        bus=bus,
        processed=InMemoryProcessedRegistry(),
        image_embed=_FailingImageEmbed(),
        text_embed=FakeEmbeddingProvider(),
        vector_repo=vec,
        content_cache=ContentEmbeddingCache(InMemoryKV()),
    )
    await bus.publish(
        Event(type=EventType.IMAGEM_ENVIADA, payload={"ref": "img-x", "visual_text": "X"})
    )
    await worker.drain()
    dlq = await bus.dead_letters()
    assert len(dlq) == 1
    assert dlq[0].attempts == 2
