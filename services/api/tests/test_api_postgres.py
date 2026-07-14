"""Teste de integração do caminho durável (Postgres) do BFF (S18/P0.2).

Pula automaticamente sem `CHARUTEI_TEST_DATABASE_URL` ou sem o extra `postgres`. Prova que
`build_context` monta repos Postgres (KG populado + OLTP durável) e que a coleção persiste.

    CHARUTEI_TEST_DATABASE_URL=postgresql://charutei:charutei@localhost:5432/charutei \
      uv run --extra postgres pytest services/api/tests/test_api_postgres.py
"""

import os

import pytest
from charutei_api import build_context
from charutei_knowledge import Collection, CollectionItem, NodeType, TastingNote, User

DB_URL = os.environ.get("CHARUTEI_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DB_URL, reason="defina CHARUTEI_TEST_DATABASE_URL para o teste durável do BFF"
)


async def test_build_context_postgres_durable(monkeypatch: pytest.MonkeyPatch) -> None:
    psycopg = pytest.importorskip("psycopg")
    # Isola: limpa as tabelas antes do build. (normaliza o prefixo +psycopg p/ o setup)
    raw_dsn = str(DB_URL).replace("postgresql+psycopg://", "postgresql://")
    conn = await psycopg.AsyncConnection.connect(raw_dsn)
    from charutei_knowledge.postgres import apply_schema

    await apply_schema(conn)
    await conn.execute(
        "TRUNCATE kg_edges, kg_nodes, collection_items, collections, users, bands, tasting_notes "
        "RESTART IDENTITY CASCADE"
    )
    await conn.commit()
    await conn.close()

    monkeypatch.setenv("DATABASE_URL", str(DB_URL))
    ctx = await build_context()
    try:
        # KG populado (seed + catálogo) no primeiro boot.
        cigars = await ctx.kg.nodes_by_type(NodeType.CIGAR)
        assert len(cigars) > 100
        assert ctx.conn is not None  # modo durável ativo

        # OLTP durável: cria user (FK) + coleção + item e relê da mesma conexão.
        await ctx.oltp.create_user(User(id="u", email="u@t.dev"))
        col = await ctx.oltp.create_collection(Collection(id="col:t", user_id="u"))
        await ctx.oltp.add_collection_item(
            CollectionItem(id="i1", collection_id=col.id, cigar_id="cigar:cohiba-robustos")
        )
        again = await ctx.oltp.get_collection("col:t")
        assert again is not None and len(again.items) == 1
        assert again.items[0].created_at is not None  # aging durável

        # Tastings duráveis (F2.5): grava e relê da mesma conexão.
        await ctx.oltp.add_tasting(
            TastingNote(
                id="t1",
                user_id="u",
                cigar_id="cigar:cohiba-robustos",
                rating=5,
                flavors=["Amadeirado"],
            )
        )
        notes = await ctx.oltp.list_tastings("u", cigar_id="cigar:cohiba-robustos")
        assert len(notes) == 1 and notes[0].flavors == ["Amadeirado"]
        assert notes[0].created_at is not None
    finally:
        await ctx.aclose()
