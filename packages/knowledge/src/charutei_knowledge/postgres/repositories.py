"""Repositórios Postgres — mesmas interfaces que os in-memory.

Grafo servido por SQL (CTE/joins) sobre kg_nodes/kg_edges. Vetores via pgvector usando
literais `::vector` (sem exigir o pacote python pgvector). Async via psycopg 3.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Json

from charutei_knowledge.models import (
    Band,
    Collection,
    CollectionItem,
    KGEdge,
    KGNode,
    NodeType,
    TastingNote,
    User,
)

_SCHEMA = Path(__file__).with_name("schema.sql")


async def apply_schema(conn: psycopg.AsyncConnection[Any]) -> None:
    """Aplica o DDL da fundação (idempotente). Para dev/testes; produção usa Alembic."""
    await conn.execute(_SCHEMA.read_text(encoding="utf-8"))
    await conn.commit()


def _vec_literal(embedding: list[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"


class PostgresKnowledgeGraph:
    """KnowledgeGraphRepo sobre tabelas relacionais."""

    def __init__(self, conn: psycopg.AsyncConnection[Any]) -> None:
        self._conn = conn

    async def _bump_version(self) -> None:
        await self._conn.execute("UPDATE kg_version SET version = version + 1 WHERE id = 1")

    async def upsert_node(self, node: KGNode) -> None:
        await self._conn.execute(
            """
            INSERT INTO kg_nodes (id, type, label, props)
            VALUES (%s, %s, %s, %s::jsonb)
            ON CONFLICT (id) DO UPDATE
              SET label = EXCLUDED.label, props = EXCLUDED.props
            """,
            (node.id, str(node.type), node.label, Json(node.props)),
        )
        await self._bump_version()
        await self._conn.commit()

    async def upsert_edge(self, edge: KGEdge) -> None:
        await self._conn.execute(
            """
            INSERT INTO kg_edges (src, dst, rel, props)
            VALUES (%s, %s, %s, %s::jsonb)
            ON CONFLICT (src, dst, rel) DO UPDATE SET props = EXCLUDED.props
            """,
            (edge.src, edge.dst, str(edge.rel), Json(edge.props)),
        )
        await self._bump_version()
        await self._conn.commit()

    async def get_node(self, node_id: str) -> KGNode | None:
        cur = await self._conn.execute(
            "SELECT id, type, label, props FROM kg_nodes WHERE id = %s", (node_id,)
        )
        row = await cur.fetchone()
        return self._row_to_node(row) if row else None

    async def neighbors(self, node_id: str, rel: str | None = None) -> list[KGNode]:
        sql = """
            SELECT n.id, n.type, n.label, n.props
            FROM kg_edges e JOIN kg_nodes n ON n.id = e.dst
            WHERE e.src = %s
        """
        params: list[Any] = [node_id]
        if rel is not None:
            sql += " AND e.rel = %s"
            params.append(rel)
        cur = await self._conn.execute(sql, tuple(params))
        return [self._row_to_node(r) for r in await cur.fetchall()]

    async def harmonizations(self, cigar_id: str) -> list[KGNode]:
        return await self.neighbors(cigar_id, rel="pairs_with")

    async def nodes_by_type(self, node_type: str) -> list[KGNode]:
        cur = await self._conn.execute(
            "SELECT id, type, label, props FROM kg_nodes WHERE type = %s", (node_type,)
        )
        return [self._row_to_node(r) for r in await cur.fetchall()]

    async def version(self) -> int:
        cur = await self._conn.execute("SELECT version FROM kg_version WHERE id = 1")
        row = await cur.fetchone()
        return int(row[0]) if row else 0

    @staticmethod
    def _row_to_node(row: tuple[Any, ...]) -> KGNode:
        return KGNode(id=row[0], type=NodeType(row[1]), label=row[2], props=row[3] or {})


class PostgresVectorRepository:
    """VectorRepository sobre a tabela `embeddings` (pgvector, cosseno via `<=>`)."""

    def __init__(self, conn: psycopg.AsyncConnection[Any]) -> None:
        self._conn = conn

    async def upsert(
        self,
        kind: str,
        item_id: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        await self._conn.execute(
            """
            INSERT INTO embeddings (kind, item_id, embedding, metadata)
            VALUES (%s, %s, %s::vector, %s::jsonb)
            ON CONFLICT (kind, item_id) DO UPDATE
              SET embedding = EXCLUDED.embedding, metadata = EXCLUDED.metadata
            """,
            (kind, item_id, _vec_literal(embedding), Json(metadata or {})),
        )
        await self._conn.commit()

    async def ann_search(
        self,
        kind: str,
        embedding: list[float],
        k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[str, float]]:
        sql = (
            "SELECT item_id, 1 - (embedding <=> %s::vector) AS score "
            "FROM embeddings WHERE kind = %s"
        )
        params: list[Any] = [_vec_literal(embedding), kind]
        if filters:
            sql += " AND metadata @> %s::jsonb"
            params.append(Json(filters))
        sql += " ORDER BY embedding <=> %s::vector LIMIT %s"
        params.extend([_vec_literal(embedding), k])
        cur = await self._conn.execute(sql, tuple(params))
        return [(r[0], float(r[1])) for r in await cur.fetchall()]


class PostgresOltp:
    """OltpRepository sobre as tabelas operacionais."""

    def __init__(self, conn: psycopg.AsyncConnection[Any]) -> None:
        self._conn = conn

    async def create_user(self, user: User) -> User:
        await self._conn.execute(
            "INSERT INTO users (id, email, display_name) VALUES (%s, %s, %s) "
            "ON CONFLICT (id) DO NOTHING",
            (user.id, user.email, user.display_name),
        )
        await self._conn.commit()
        return user

    async def get_user(self, user_id: str) -> User | None:
        cur = await self._conn.execute(
            "SELECT id, email, display_name FROM users WHERE id = %s", (user_id,)
        )
        row = await cur.fetchone()
        return User(id=row[0], email=row[1], display_name=row[2]) if row else None

    async def save_band(self, band: Band) -> Band:
        await self._conn.execute(
            """
            INSERT INTO bands (id, user_id, image_ref, cigar_id, confidence, needs_human)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
              cigar_id = EXCLUDED.cigar_id, confidence = EXCLUDED.confidence,
              needs_human = EXCLUDED.needs_human
            """,
            (
                band.id,
                band.user_id,
                band.image_ref,
                band.cigar_id,
                band.confidence,
                band.needs_human,
            ),
        )
        await self._conn.commit()
        return band

    async def create_collection(self, collection: Collection) -> Collection:
        await self._conn.execute(
            "INSERT INTO collections (id, user_id, name) VALUES (%s, %s, %s) "
            "ON CONFLICT (id) DO NOTHING",
            (collection.id, collection.user_id, collection.name),
        )
        await self._conn.commit()
        return collection

    async def add_collection_item(self, item: CollectionItem) -> CollectionItem:
        cur = await self._conn.execute(
            "INSERT INTO collection_items (id, collection_id, cigar_id, quantity) "
            "VALUES (%s, %s, %s, %s) RETURNING created_at",
            (item.id, item.collection_id, item.cigar_id, item.quantity),
        )
        row = await cur.fetchone()
        await self._conn.commit()
        return item.model_copy(update={"created_at": row[0]}) if row else item

    async def get_collection(self, collection_id: str) -> Collection | None:
        cur = await self._conn.execute(
            "SELECT id, user_id, name FROM collections WHERE id = %s", (collection_id,)
        )
        row = await cur.fetchone()
        if not row:
            return None
        items_cur = await self._conn.execute(
            "SELECT id, collection_id, cigar_id, quantity, created_at FROM collection_items "
            "WHERE collection_id = %s ORDER BY created_at",
            (collection_id,),
        )
        items = [
            CollectionItem(
                id=r[0], collection_id=r[1], cigar_id=r[2], quantity=r[3], created_at=r[4]
            )
            for r in await items_cur.fetchall()
        ]
        return Collection(id=row[0], user_id=row[1], name=row[2], items=items)

    async def add_tasting(self, note: TastingNote) -> TastingNote:
        cur = await self._conn.execute(
            "INSERT INTO tasting_notes "
            "(id, user_id, cigar_id, rating, flavors, occasion, note) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING created_at",
            (
                note.id,
                note.user_id,
                note.cigar_id,
                note.rating,
                Json(note.flavors),
                note.occasion,
                note.note,
            ),
        )
        row = await cur.fetchone()
        await self._conn.commit()
        return note.model_copy(update={"created_at": row[0]}) if row else note

    async def list_tastings(self, user_id: str, cigar_id: str | None = None) -> list[TastingNote]:
        sql = (
            "SELECT id, user_id, cigar_id, rating, flavors, occasion, note, created_at "
            "FROM tasting_notes WHERE user_id = %s"
        )
        params: list[Any] = [user_id]
        if cigar_id is not None:
            sql += " AND cigar_id = %s"
            params.append(cigar_id)
        sql += " ORDER BY created_at DESC"
        cur = await self._conn.execute(sql, tuple(params))
        return [
            TastingNote(
                id=r[0],
                user_id=r[1],
                cigar_id=r[2],
                rating=r[3],
                flavors=r[4],
                occasion=r[5],
                note=r[6],
                created_at=r[7],
            )
            for r in await cur.fetchall()
        ]
