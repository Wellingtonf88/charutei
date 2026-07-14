"""Interfaces de acesso a dados (Protocols).

TODO acesso a OLTP/KG/vetor passa por aqui. As implementações (in-memory, Postgres hoje;
Qdrant/Neo4j na escala) são intercambiáveis sem tocar nos chamadores — requisito do blueprint
("escalar sem reescrita estrutural"). Métodos são async para casar com FastAPI/serviços.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from charutei_knowledge.models import (
    Band,
    Collection,
    CollectionItem,
    KGEdge,
    KGNode,
    TastingNote,
    User,
)


@runtime_checkable
class KnowledgeGraphRepo(Protocol):
    """Grafo de conhecimento de charutos. Resolve fatos no degrau DETERMINÍSTICO (sem LLM)."""

    async def upsert_node(self, node: KGNode) -> None: ...

    async def upsert_edge(self, edge: KGEdge) -> None: ...

    async def get_node(self, node_id: str) -> KGNode | None: ...

    async def neighbors(self, node_id: str, rel: str | None = None) -> list[KGNode]:
        """Vizinhos de saída de `node_id`, opcionalmente filtrados por relação."""
        ...

    async def nodes_by_type(self, node_type: str) -> list[KGNode]:
        """Todos os nós de um tipo (ex.: 'cigar') — usado p/ detectar entidades citadas."""
        ...

    async def harmonizations(self, cigar_id: str) -> list[KGNode]:
        """Harmonizações (pairings) de um charuto — pergunta-âncora do assistente."""
        ...

    async def version(self) -> int:
        """Versão do KG — invalida o cache semântico quando o conhecimento muda."""
        ...


@runtime_checkable
class VectorRepository(Protocol):
    """Índice vetorial (pgvector hoje → Qdrant na escala). `kind` separa namespaces."""

    async def upsert(
        self,
        kind: str,
        item_id: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None: ...

    async def ann_search(
        self,
        kind: str,
        embedding: list[float],
        k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[str, float]]:
        """Top-k por similaridade de cosseno → lista de (item_id, score) decrescente."""
        ...


@runtime_checkable
class OltpRepository(Protocol):
    """Estado operacional (usuários, anilhas, coleções) — ACID."""

    async def create_user(self, user: User) -> User: ...

    async def get_user(self, user_id: str) -> User | None: ...

    async def save_band(self, band: Band) -> Band: ...

    async def create_collection(self, collection: Collection) -> Collection: ...

    async def add_collection_item(self, item: CollectionItem) -> CollectionItem: ...

    async def get_collection(self, collection_id: str) -> Collection | None: ...

    async def add_tasting(self, note: TastingNote) -> TastingNote:
        """Registra uma degustação (rating/sabores/nota) — F2.5."""
        ...

    async def list_tastings(self, user_id: str, cigar_id: str | None = None) -> list[TastingNote]:
        """Degustações do usuário (opc. por charuto), mais recentes primeiro."""
        ...
