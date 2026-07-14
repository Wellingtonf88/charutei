"""Camada de conhecimento do CHARUTEI: acesso a OLTP/KG/vetor atrás de interfaces."""

from charutei_knowledge.interfaces import (
    KnowledgeGraphRepo,
    OltpRepository,
    VectorRepository,
)
from charutei_knowledge.memory import (
    InMemoryKnowledgeGraph,
    InMemoryOltp,
    InMemoryVectorRepository,
    node_id,
)
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
from charutei_knowledge.seed import SeedStats, seed_knowledge_graph, slugify

__all__ = [
    "KnowledgeGraphRepo",
    "OltpRepository",
    "VectorRepository",
    "InMemoryKnowledgeGraph",
    "InMemoryOltp",
    "InMemoryVectorRepository",
    "node_id",
    "Band",
    "Collection",
    "CollectionItem",
    "EdgeRel",
    "KGEdge",
    "KGNode",
    "NodeType",
    "TastingNote",
    "User",
    "SeedStats",
    "seed_knowledge_graph",
    "slugify",
]
