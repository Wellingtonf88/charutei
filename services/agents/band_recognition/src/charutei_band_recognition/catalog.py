"""Catálogo de anilhas: indexa cada charuto no espaço vetorial (kind='band').

Em produção, os embeddings vêm da imagem real da anilha (Voyage multimodal), gerados em
batch e versionados por hash de conteúdo. Aqui, partimos do rótulo do charuto via o mesmo
provider — mantendo imagem de busca e catálogo no mesmo espaço.
"""

from __future__ import annotations

from collections.abc import Iterable

from charutei_cache.interfaces import VectorIndex
from charutei_contracts import BandImage
from charutei_orchestrator import ImageEmbeddingProvider

BAND_KIND = "band"


async def build_band_catalog(
    image_embed: ImageEmbeddingProvider,
    vector_repo: VectorIndex,
    cigars: Iterable[tuple[str, str]],
) -> dict[str, str]:
    """Indexa (cigar_id, label) → embedding em `vector_repo`. Retorna o mapa de rótulos."""
    labels: dict[str, str] = {}
    for cigar_id, label in cigars:
        emb = await image_embed.embed_image(BandImage(ref=cigar_id, visual_text=label))
        await vector_repo.upsert(BAND_KIND, cigar_id, emb, {"label": label})
        labels[cigar_id] = label
    return labels
