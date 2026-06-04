"""Modelos de domínio do CHARUTEI (Pydantic).

Estes são os *fatos* do domínio (charuto, marca, anilha, coleção) e a forma genérica do
Knowledge Graph (nó/aresta). Ficam aqui — não em `contracts`, que é I/O de agente — porque
são consumidos pelos repositórios. O grafo é modelado de forma relacional, mas a API
(`KGNode`/`KGEdge`) é genérica o bastante para mapear 1:1 a AGE/Neo4j na escala.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class NodeType(StrEnum):
    """Tipos de entidade no Knowledge Graph de charutos."""

    BRAND = "brand"  # marca (ex.: Cohiba)
    FACTORY = "factory"  # fábrica / origem de produção
    VITOLA = "vitola"  # formato/medida (ex.: Robusto)
    STRENGTH = "strength"  # força (suave/médio/encorpado)
    COUNTRY = "country"  # país de origem
    CIGAR = "cigar"  # SKU de charuto
    PAIRING = "pairing"  # harmonização (bebida/contexto)


class EdgeRel(StrEnum):
    """Relações entre nós do grafo."""

    MADE_BY = "made_by"  # cigar -> brand
    PRODUCED_AT = "produced_at"  # cigar -> factory
    HAS_VITOLA = "has_vitola"  # cigar -> vitola
    HAS_STRENGTH = "has_strength"  # cigar -> strength
    FROM_COUNTRY = "from_country"  # cigar/brand -> country
    PAIRS_WITH = "pairs_with"  # cigar -> pairing


class KGNode(BaseModel):
    """Nó genérico do grafo. `props` carrega atributos específicos do tipo."""

    id: str
    type: NodeType
    label: str
    props: dict[str, Any] = Field(default_factory=dict)


class KGEdge(BaseModel):
    """Aresta dirigida `src -[rel]-> dst`."""

    src: str
    dst: str
    rel: EdgeRel
    props: dict[str, Any] = Field(default_factory=dict)


# --- OLTP ---


class User(BaseModel):
    id: str
    email: str
    display_name: str | None = None


class Band(BaseModel):
    """Anilha capturada pelo usuário (resultado de reconhecimento, S3)."""

    id: str
    user_id: str
    image_ref: str
    cigar_id: str | None = None
    confidence: float | None = None
    needs_human: bool = False


class CollectionItem(BaseModel):
    id: str
    collection_id: str
    cigar_id: str
    quantity: int = 1


class Collection(BaseModel):
    id: str
    user_id: str
    name: str = "Meu humidor"
    items: list[CollectionItem] = Field(default_factory=list)
