"""Ingere o catálogo de charutos no Knowledge Graph (Cigar Intelligence).

Por padrão usa o KG in-memory (semeado) e imprime o relatório. Com --postgres, ingere no
banco real (requer Postgres no ar + extra `postgres`).

    uv run python scripts/ingest_catalog.py
    DATABASE_URL=postgresql://charutei:charutei@localhost:5432/charutei \
      uv run --extra postgres python scripts/ingest_catalog.py --postgres
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from charutei_cigar_intelligence import CatalogIngestor, InMemoryReviewQueue, parse_catalog_csv
from charutei_knowledge import InMemoryKnowledgeGraph, NodeType, seed_knowledge_graph

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog" / "cigars.csv"


async def run_in_memory() -> None:
    kg = InMemoryKnowledgeGraph()
    before = len(await kg.nodes_by_type(NodeType.CIGAR))
    await seed_knowledge_graph(kg)
    seeded = len(await kg.nodes_by_type(NodeType.CIGAR))

    review = InMemoryReviewQueue()
    ingestor = CatalogIngestor(kg, review_queue=review)
    records = parse_catalog_csv(CATALOG)
    report = await ingestor.ingest(records)
    after = len(await kg.nodes_by_type(NodeType.CIGAR))

    print(f"charutos: {before} → seed {seeded} → catálogo {after}")
    print(f"ingestão: {report.model_dump()} | revisão(HITL): {len(review.items)} item(ns)")


async def run_postgres() -> None:
    import psycopg
    from charutei_knowledge.postgres import PostgresKnowledgeGraph, apply_schema

    dsn = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    conn = await psycopg.AsyncConnection.connect(dsn)
    await apply_schema(conn)
    kg = PostgresKnowledgeGraph(conn)

    before = len(await kg.nodes_by_type(NodeType.CIGAR))
    report = await CatalogIngestor(kg).ingest(parse_catalog_csv(CATALOG))
    after = len(await kg.nodes_by_type(NodeType.CIGAR))
    print(f"[postgres] charutos: {before} → {after} | ingestão: {report.model_dump()}")
    await conn.close()


def main() -> None:
    if "--postgres" in sys.argv[1:]:
        asyncio.run(run_postgres())
    else:
        asyncio.run(run_in_memory())


if __name__ == "__main__":
    main()
