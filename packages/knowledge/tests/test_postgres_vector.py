"""Integração: PostgresVectorRepository (pgvector) — upsert + ANN cosseno + filtro.

Valida o caminho que o Band Recognition usa em produção. Pula sem o banco
(CHARUTEI_TEST_DATABASE_URL). Rode com Postgres no ar e o extra `postgres`.
"""

import os

import pytest

DB_URL = os.environ.get("CHARUTEI_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DB_URL, reason="defina CHARUTEI_TEST_DATABASE_URL para o teste de integração pgvector"
)


@pytest.fixture
async def vec():  # type: ignore[no-untyped-def]
    psycopg = pytest.importorskip("psycopg")
    from charutei_knowledge.postgres import PostgresVectorRepository, apply_schema

    conn = await psycopg.AsyncConnection.connect(DB_URL)
    await apply_schema(conn)
    await conn.execute("TRUNCATE embeddings")
    await conn.commit()
    yield PostgresVectorRepository(conn)
    await conn.close()


async def test_ann_cosine_nearest_first_and_filter(vec) -> None:  # type: ignore[no-untyped-def]
    await vec.upsert("band", "a", [1.0, 0.0, 0.0], {"country": "Cuba"})
    await vec.upsert("band", "b", [0.9, 0.1, 0.0], {"country": "Nicaragua"})
    await vec.upsert("band", "c", [0.0, 1.0, 0.0], {"country": "Cuba"})

    ranked = await vec.ann_search("band", [1.0, 0.0, 0.0], k=2)
    assert [item_id for item_id, _ in ranked] == ["a", "b"]
    assert ranked[0][1] >= ranked[1][1]  # score = 1 - distância cosseno

    filtered = await vec.ann_search("band", [1.0, 0.0, 0.0], k=5, filters={"country": "Cuba"})
    assert {item_id for item_id, _ in filtered} == {"a", "c"}
