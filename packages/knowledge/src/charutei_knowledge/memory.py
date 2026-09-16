"""Implementações in-memory dos repositórios.

Servem a dois propósitos: (1) testes/CI sem Postgres no ar; (2) desenvolvimento local rápido.
Satisfazem exatamente os mesmos Protocols que a implementação Postgres — é o que prova que o
acesso a dados está atrás de interface (swap sem reescrita).
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

from charutei_knowledge.models import (
    Band,
    Collection,
    CollectionItem,
    EdgeRel,
    KGEdge,
    KGNode,
    NodeType,
    TastingNote,
    User,
)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class InMemoryKnowledgeGraph:
    """KG em dicionários. Mesma semântica do CTE recursivo da impl Postgres."""

    def __init__(self) -> None:
        self._nodes: dict[str, KGNode] = {}
        self._edges: list[KGEdge] = []
        self._version = 0

    async def upsert_node(self, node: KGNode) -> None:
        self._nodes[node.id] = node
        self._version += 1

    async def upsert_edge(self, edge: KGEdge) -> None:
        # Dedupe por (src, dst, rel) — idempotente, como o ON CONFLICT do Postgres.
        for existing in self._edges:
            if (existing.src, existing.dst, existing.rel) == (edge.src, edge.dst, edge.rel):
                existing.props = edge.props
                return
        self._edges.append(edge)
        self._version += 1

    async def get_node(self, node_id: str) -> KGNode | None:
        return self._nodes.get(node_id)

    async def neighbors(self, node_id: str, rel: str | None = None) -> list[KGNode]:
        out: list[KGNode] = []
        for edge in self._edges:
            if edge.src != node_id:
                continue
            if rel is not None and edge.rel != rel:
                continue
            target = self._nodes.get(edge.dst)
            if target is not None:
                out.append(target)
        return out

    async def harmonizations(self, cigar_id: str) -> list[KGNode]:
        return await self.neighbors(cigar_id, rel=EdgeRel.PAIRS_WITH)

    async def nodes_by_type(self, node_type: str) -> list[KGNode]:
        return [n for n in self._nodes.values() if n.type == node_type]

    async def version(self) -> int:
        return self._version


class InMemoryVectorRepository:
    """Busca ANN por força bruta (cosseno). Suficiente para o seed do MVP."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, tuple[list[float], dict[str, Any]]]] = {}

    async def upsert(
        self,
        kind: str,
        item_id: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._store.setdefault(kind, {})[item_id] = (embedding, metadata or {})

    async def ann_search(
        self,
        kind: str,
        embedding: list[float],
        k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[str, float]]:
        items = self._store.get(kind, {})
        scored: list[tuple[str, float]] = []
        for item_id, (vec, meta) in items.items():
            if filters and any(meta.get(key) != val for key, val in filters.items()):
                continue
            scored.append((item_id, _cosine(embedding, vec)))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:k]


class InMemoryOltp:
    """Estado operacional em dicionários."""

    def __init__(self) -> None:
        self._users: dict[str, User] = {}
        self._bands: dict[str, Band] = {}
        self._collections: dict[str, Collection] = {}
        self._tastings: list[TastingNote] = []
        self._idempotency_keys: set[str] = set()

    async def create_user(self, user: User) -> User:
        self._users[user.id] = user
        return user

    async def get_user(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    async def save_band(self, band: Band) -> Band:
        self._bands[band.id] = band
        return band

    async def create_collection(self, collection: Collection) -> Collection:
        self._collections[collection.id] = collection
        return collection

    async def add_collection_item(self, item: CollectionItem) -> CollectionItem:
        collection = self._collections.get(item.collection_id)
        if collection is None:
            raise KeyError(f"coleção inexistente: {item.collection_id}")
        if item.created_at is None:  # carimba a entrada no humidor (aging)
            item = item.model_copy(update={"created_at": datetime.now(UTC)})
        collection.items.append(item)
        return item

    async def get_collection(self, collection_id: str) -> Collection | None:
        return self._collections.get(collection_id)

    async def list_collections(self, user_id: str) -> list[Collection]:
        return [c for c in self._collections.values() if c.user_id == user_id]

    async def add_tasting(self, note: TastingNote) -> TastingNote:
        if note.created_at is None:
            note = note.model_copy(update={"created_at": datetime.now(UTC)})
        self._tastings.append(note)
        return note

    async def list_tastings(self, user_id: str, cigar_id: str | None = None) -> list[TastingNote]:
        found = [
            t
            for t in self._tastings
            if t.user_id == user_id and (cigar_id is None or t.cigar_id == cigar_id)
        ]
        # mais recentes primeiro (created_at sempre setado no add)
        epoch = datetime.min.replace(tzinfo=UTC)
        return sorted(found, key=lambda t: t.created_at or epoch, reverse=True)

    async def idempotency_seen(self, key: str) -> bool:
        return key in self._idempotency_keys

    async def idempotency_mark(self, key: str) -> None:
        self._idempotency_keys.add(key)


def node_id(node_type: NodeType, slug: str) -> str:
    """ID canônico e estável de nó: `<tipo>:<slug>`. Garante upsert idempotente."""
    return f"{node_type}:{slug}"
