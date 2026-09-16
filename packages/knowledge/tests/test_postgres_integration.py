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
    await conn.execute("TRUNCATE idempotency_keys, collection_items, collections, users CASCADE")
    await conn.commit()
    yield PostgresOltp(conn)
    await conn.close()


async def test_postgres_idempotency_keys_durable(oltp_conn) -> None:  # type: ignore[no-untyped-def]
    assert await oltp_conn.idempotency_seen("key-durable-1") is False
    await oltp_conn.idempotency_mark("key-durable-1")
    assert await oltp_conn.idempotency_seen("key-durable-1") is True
    # marcar de novo não é erro (ON CONFLICT DO NOTHING)
    await oltp_conn.idempotency_mark("key-durable-1")


async def test_postgres_list_collections(oltp_conn) -> None:  # type: ignore[no-untyped-def]
    from charutei_knowledge import Collection, User

    await oltp_conn.create_user(User(id="u1", email="u1@example.com"))
    await oltp_conn.create_user(User(id="u2", email="u2@example.com"))
    await oltp_conn.create_collection(Collection(id="col:u1", user_id="u1"))
    await oltp_conn.create_collection(Collection(id="col-extra", user_id="u1", name="Viagem"))
    await oltp_conn.create_collection(Collection(id="col:u2", user_id="u2"))

    u1_collections = await oltp_conn.list_collections("u1")
    assert {c.id for c in u1_collections} == {"col:u1", "col-extra"}
    assert {c.id for c in await oltp_conn.list_collections("u2")} == {"col:u2"}


@pytest.fixture
async def location_conn():  # type: ignore[no-untyped-def]
    psycopg = pytest.importorskip("psycopg")
    from charutei_knowledge.postgres import PostgresLocationRepo, apply_schema

    conn = await psycopg.AsyncConnection.connect(DB_URL)
    await apply_schema(conn)
    await conn.execute("TRUNCATE product_availability, establishments CASCADE")
    await conn.commit()
    yield PostgresLocationRepo(conn)
    await conn.close()


async def test_postgres_establishments_and_availability(location_conn) -> None:  # type: ignore[no-untyped-def]
    from charutei_knowledge import AvailabilityStatus, Establishment, ProductAvailability

    await location_conn.create_establishment(
        Establishment(id="est-1", name="Tabacaria Teste", lat=-23.5, lng=-46.6, city="São Paulo")
    )
    assert [e.id for e in await location_conn.list_establishments()] == ["est-1"]

    saved = await location_conn.set_availability(
        ProductAvailability(
            id="avail-1",
            establishment_id="est-1",
            cigar_id="cigar:cohiba-robustos",
            status=AvailabilityStatus.COMMUNITY_REPORTED,
        )
    )
    assert saved.observed_at is not None

    found = await location_conn.list_availability("cigar:cohiba-robustos")
    assert len(found) == 1
    assert found[0].status == AvailabilityStatus.COMMUNITY_REPORTED
