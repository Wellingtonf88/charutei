"""Teste de integração Postgres — mesmas asserções de contrato dos repositórios in-memory.

Pula automaticamente quando não há banco (CHARUTEI_TEST_DATABASE_URL ausente) ou quando o
extra `postgres` não está instalado. Rode com Postgres no ar:

    CHARUTEI_TEST_DATABASE_URL=postgresql://charutei:charutei@localhost:5432/charutei \\
      uv run --extra postgres pytest packages/knowledge/tests/test_postgres_integration.py
"""

import os

import pytest
from charutei_knowledge import NodeType, node_id, seed_knowledge_graph

DB_URL = os.environ.get("CHARUTEI_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DB_URL, reason="defina CHARUTEI_TEST_DATABASE_URL para rodar o teste de integração Postgres"
)


@pytest.fixture
async def kg_conn():  # type: ignore[no-untyped-def]
    psycopg = pytest.importorskip("psycopg")
    from charutei_knowledge.postgres import PostgresKnowledgeGraph, apply_schema

    conn = await psycopg.AsyncConnection.connect(DB_URL)
    await apply_schema(conn)
    # limpa para isolar o teste
    await conn.execute("TRUNCATE kg_edges, kg_nodes RESTART IDENTITY CASCADE")
    await conn.commit()
    yield PostgresKnowledgeGraph(conn)
    await conn.close()


async def test_postgres_seed_and_harmonizations(kg_conn) -> None:  # type: ignore[no-untyped-def]
    stats = await seed_knowledge_graph(kg_conn)
    assert stats.cigars >= 30

    cigar = node_id(NodeType.CIGAR, "partagas-serie-d-no-4")
    pairings = await kg_conn.harmonizations(cigar)
    assert {p.label for p in pairings}
    assert all(p.type == NodeType.PAIRING for p in pairings)
    assert await kg_conn.version() > 0


@pytest.fixture
async def oltp_conn():  # type: ignore[no-untyped-def]
    psycopg = pytest.importorskip("psycopg")
    from charutei_knowledge.postgres import PostgresOltp, apply_schema

    conn = await psycopg.AsyncConnection.connect(DB_URL)
    await apply_schema(conn)
    await conn.execute("TRUNCATE idempotency_keys")
    await conn.commit()
    yield PostgresOltp(conn)
    await conn.close()


async def test_postgres_idempotency_keys_durable(oltp_conn) -> None:  # type: ignore[no-untyped-def]
    assert await oltp_conn.idempotency_seen("key-durable-1") is False
    await oltp_conn.idempotency_mark("key-durable-1")
    assert await oltp_conn.idempotency_seen("key-durable-1") is True
    # marcar de novo não é erro (ON CONFLICT DO NOTHING)
    await oltp_conn.idempotency_mark("key-durable-1")
