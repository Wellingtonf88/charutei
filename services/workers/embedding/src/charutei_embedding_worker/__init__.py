"""Embedding Worker: materializa embeddings a partir de eventos (assíncrono, idempotente)."""

from charutei_embedding_worker.cache import ContentEmbeddingCache, content_hash
from charutei_embedding_worker.worker import (
    BAND_KIND,
    CIGAR_TEXT_KIND,
    EmbeddingWorker,
    ProcessReport,
)

__all__ = [
    "EmbeddingWorker",
    "ProcessReport",
    "ContentEmbeddingCache",
    "content_hash",
    "BAND_KIND",
    "CIGAR_TEXT_KIND",
]
