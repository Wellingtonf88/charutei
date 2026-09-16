"""Camada de conhecimento do CHARUTEI: acesso a OLTP/KG/vetor atrás de interfaces."""

from charutei_knowledge.interfaces import (
    KnowledgeGraphRepo,
    LocationRepo,
    OltpRepository,
    VectorRepository,
)
from charutei_knowledge.memory import (
    InMemoryKnowledgeGraph,
    InMemoryLocationRepo,
    InMemoryOltp,
    InMemoryVectorRepository,
    node_id,
)
from charutei_knowledge.models import (
    AvailabilityStatus,
    Band,
    Collection,
    CollectionItem,
    EdgeRel,
    Establishment,
    KGEdge,
    KGNode,
    NodeType,
    ProductAvailability,
    TastingNote,
    User,
)
from charutei_knowledge.seed import SeedStats, seed_knowledge_graph, slugify

__all__ = [
    "KnowledgeGraphRepo",
    "LocationRepo",
    "OltpRepository",
    "VectorRepository",
    "InMemoryKnowledgeGraph",
    "InMemoryLocationRepo",
    "InMemoryOltp",
    "InMemoryVectorRepository",
    "node_id",
    "AvailabilityStatus",
    "Band",
    "Collection",
    "CollectionItem",
    "EdgeRel",
    "Establishment",
    "KGEdge",
    "KGNode",
    "NodeType",
    "ProductAvailability",
    "TastingNote",
    "User",
    "SeedStats",
    "seed_knowledge_graph",
    "slugify",
]
