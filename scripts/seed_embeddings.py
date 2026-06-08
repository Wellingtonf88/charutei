"""Materializa embeddings de texto de charuto no pgvector (Voyage AI).

Carrega todos os nós `cigar` do Knowledge Graph (Postgres), embeda os labels via
Voyage voyage-4-lite e upserta na tabela `embeddings` (kind='cigar_text'). Idempotente:
re-embeda apenas o que foi alterado (upsert por kind+item_id).

Pré-requisitos:
  - Postgres rodando com schema aplicado (alembic upgrade head ou apply_schema)
  - Catálogo ingerido (scripts/ingest_catalog.py --postgres)
  - Chaves de API no ambiente

Uso:
    DATABASE_URL=postgresql://charutei:charutei@localhost:5432/charutei \\
    VOYAGE_API_KEY=... \\
    uv run python scripts/seed_embeddings.py

    # Valida pipeline sem persistir:
    ... uv run python scripts/seed_embeddings.py --dry-run
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_BATCH = 50  # voyage-4-lite aceita até 128; 50 por margem de segurança


async def main(*, dry_run: bool = False) -> None:
    voyage_key = os.environ.get("VOYAGE_API_KEY")
    db_url = os.environ.get("DATABASE_URL")
    if not voyage_key:
        print("Erro: VOYAGE_API_KEY não definida", file=sys.stderr)
        sys.exit(1)
    if not db_url:
        print("Erro: DATABASE_URL não definida", file=sys.stderr)
        sys.exit(1)

    import psycopg
    from charutei_knowledge.models import NodeType
    from charutei_knowledge.postgres import (
        PostgresKnowledgeGraph,
        PostgresVectorRepository,
        apply_schema,
    )
    from charutei_orchestrator.providers import VoyageEmbeddingProvider

    dsn = db_url.replace("postgresql+psycopg://", "postgresql://")
    conn = await psycopg.AsyncConnection.connect(dsn)
    await apply_schema(conn)

    kg = PostgresKnowledgeGraph(conn)
    vec = PostgresVectorRepository(conn)
    provider = VoyageEmbeddingProvider(api_key=voyage_key)

    cigars = await kg.nodes_by_type(NodeType.CIGAR)
    if not cigars:
        print("Nenhum cigar no KG. Rode ingest_catalog.py --postgres primeiro.")
        await conn.close()
        return

    verb = "[dry-run] gerando" if dry_run else "Embeddando"
    print(f"{verb} {len(cigars)} charutos via voyage-4-lite …")
    total = 0

    for i in range(0, len(cigars), _BATCH):
        batch = cigars[i : i + _BATCH]
        labels = [c.label for c in batch]
        embeddings = await provider.embed(labels)
        if not dry_run:
            for cigar, emb in zip(batch, embeddings, strict=True):
                await vec.upsert("cigar_text", cigar.id, emb, {"cigar_id": cigar.id})
        total += len(batch)
        print(f"  {total}/{len(cigars)}")

    if dry_run:
        dim = len(embeddings[0])
        print(f"[dry-run] {len(cigars)} embeddings gerados (dim={dim}), não persistidos.")
    else:
        print(f"✓ {len(cigars)} embeddings upsertados (kind='cigar_text')")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main(dry_run="--dry-run" in sys.argv))
