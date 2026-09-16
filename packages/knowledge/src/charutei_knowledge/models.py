"""Modelos de domínio do CHARUTEI (Pydantic).

Estes são os *fatos* do domínio (charuto, marca, anilha, coleção) e a forma genérica do
Knowledge Graph (nó/aresta). Ficam aqui — não em `contracts`, que é I/O de agente — porque
são consumidos pelos repositórios. O grafo é modelado de forma relacional, mas a API
(`KGNode`/`KGEdge`) é genérica o bastante para mapear 1:1 a AGE/Neo4j na escala.
"""

from __future__ import annotations

from datetime import datetime
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
    created_at: datetime | None = None  # entrada no humidor — base do aging (F2.5)


class Collection(BaseModel):
    id: str
    user_id: str
    name: str = "Meu humidor"
    items: list[CollectionItem] = Field(default_factory=list)


class TastingNote(BaseModel):
    """Registro de degustação de um charuto por um usuário (F2.5)."""

    id: str
    user_id: str
    cigar_id: str
    rating: int = Field(ge=1, le=5)
    flavors: list[str] = Field(default_factory=list)
    occasion: str = ""
    note: str = ""
    created_at: datetime | None = None


# --- Location (Fase 4 do upgrade) ---


class AvailabilityStatus(StrEnum):
    """Nunca trate 'estabelecimento existe' como 'produto disponível' (prompt mestre §10)."""

    CONFIRMED = "confirmed"
    RECENTLY_CONFIRMED = "recently_confirmed"
    COMMUNITY_REPORTED = "community_reported"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


class Establishment(BaseModel):
    """Tabacaria/loja/distribuidor. OLTP, não KG — campos operacionais mutáveis (endereço,
    confiança) em vez de fatos estáveis do domínio de charutos."""

    id: str
    name: str
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    address: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    est_type: str = "tabacaria"
    source: str = ""  # proveniência (ex.: "community:{user_id}") — nunca oculta a origem do dado
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    updated_at: datetime | None = None


class ProductAvailability(BaseModel):
    """Disponibilidade de um charuto num estabelecimento — entidade própria, nunca inferida da
    mera existência do estabelecimento."""

    id: str
    establishment_id: str
    cigar_id: str
    status: AvailabilityStatus = AvailabilityStatus.UNKNOWN
    source: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    price: float | None = None
    quantity: int | None = None
    observed_at: datetime | None = None
