"""CatalogIngestor — ingere registros de catálogo no Knowledge Graph (batch).

Pipeline: resolução de entidades (slug canônico) → dedup por SKU → detecção de conflito de
fatos de alta confiança (→ HITL, nunca sobrescreve em silêncio) → upsert idempotente de
nós/arestas → enriquecimento de harmonização por regra de força → evento `sku.detectado`.
"""

from __future__ import annotations

from charutei_events import EventType, Outbox
from charutei_events.models import Event
from charutei_knowledge import (
    EdgeRel,
    KGEdge,
    KGNode,
    KnowledgeGraphRepo,
    NodeType,
    node_id,
    slugify,
)
from pydantic import BaseModel

from charutei_cigar_intelligence.catalog import CatalogRecord
from charutei_cigar_intelligence.review import InMemoryReviewQueue, ReviewItem, ReviewQueue

# Campo do catálogo → (tipo de nó, relação). Define como cada fato vira grafo.
_FIELD_SPEC: dict[str, tuple[NodeType, EdgeRel]] = {
    "brand": (NodeType.BRAND, EdgeRel.MADE_BY),
    "country": (NodeType.COUNTRY, EdgeRel.FROM_COUNTRY),
    "vitola": (NodeType.VITOLA, EdgeRel.HAS_VITOLA),
    "strength": (NodeType.STRENGTH, EdgeRel.HAS_STRENGTH),
    "factory": (NodeType.FACTORY, EdgeRel.PRODUCED_AT),
}

# Harmonizações convencionais por categoria de força (não por SKU — evita inventar dado).
_STRENGTH_PAIRINGS: dict[str, list[str]] = {
    "mild": ["champagne", "cafe-coado", "vinho-branco-seco"],
    "medium": ["cafe-coado", "bourbon"],
    "medium-full": ["bourbon", "espresso"],
    "full": ["rum-anejo", "whisky-single-malt", "espresso"],
}
_PAIRING_LABELS: dict[str, str] = {
    "rum-anejo": "Rum envelhecido",
    "whisky-single-malt": "Whisky single malt",
    "bourbon": "Bourbon",
    "espresso": "Espresso",
    "cafe-coado": "Café coado",
    "porto-tawny": "Vinho do Porto tawny",
    "champagne": "Champagne",
    "vinho-branco-seco": "Vinho branco seco",
    "conhaque": "Conhaque",
}


class IngestReport(BaseModel):
    created: int = 0
    updated: int = 0  # SKU existente enriquecido (campos antes ausentes)
    unchanged: int = 0
    conflicts: int = 0  # divergência de fato → fila de revisão (HITL)


class CatalogIngestor:
    def __init__(
        self,
        kg: KnowledgeGraphRepo,
        *,
        review_queue: ReviewQueue | None = None,
        outbox: Outbox | None = None,
    ) -> None:
        self._kg = kg
        self._review = review_queue or InMemoryReviewQueue()
        self._outbox = outbox

    async def ingest(
        self, records: list[CatalogRecord], *, apply_conflicts: bool = False
    ) -> IngestReport:
        report = IngestReport()
        for record in records:
            cigar_id = node_id(NodeType.CIGAR, record.slug)
            existing = await self._kg.get_node(cigar_id)
            if existing is None:
                await self._create(cigar_id, record)
                report.created += 1
            else:
                await self._merge(cigar_id, existing, record, report, apply_conflicts)
        return report

    async def _create(self, cigar_id: str, record: CatalogRecord) -> None:
        props = {k: v for k, v in record.core.items() if v is not None}
        await self._kg.upsert_node(
            KGNode(id=cigar_id, type=NodeType.CIGAR, label=record.name, props=props)
        )
        for field, value in record.core.items():
            if value is not None:
                await self._link_field(cigar_id, field, value)
        if record.factory:
            await self._link_field(cigar_id, "factory", record.factory)
        if record.strength:
            await self._link_pairings(cigar_id, record.strength)
        if self._outbox is not None:
            await self._outbox.add(
                Event(
                    type=EventType.SKU_DETECTADO,
                    payload={"cigar_id": cigar_id, "text": record.name},
                )
            )

    async def _merge(
        self,
        cigar_id: str,
        existing: KGNode,
        record: CatalogRecord,
        report: IngestReport,
        apply_conflicts: bool,
    ) -> None:
        enrich: dict[str, str] = {}
        conflicts: list[ReviewItem] = []
        for field, incoming in record.core.items():
            if incoming is None:
                continue
            current = existing.props.get(field)
            if current is None:
                enrich[field] = incoming  # preenche fato antes ausente
            elif current != incoming:
                conflicts.append(
                    ReviewItem(
                        cigar_id=cigar_id, field=field, existing=str(current), incoming=incoming
                    )
                )

        if conflicts and not apply_conflicts:
            for item in conflicts:
                await self._review.submit(item)
            report.conflicts += 1
            return

        applied = dict(enrich)
        if apply_conflicts:
            applied.update({c.field: c.incoming for c in conflicts if c.incoming})
        if not applied:
            report.unchanged += 1
            return

        merged_props = {**existing.props, **applied}
        await self._kg.upsert_node(
            KGNode(id=cigar_id, type=NodeType.CIGAR, label=existing.label, props=merged_props)
        )
        for field, value in applied.items():
            await self._link_field(cigar_id, field, value)
            if field == "strength":
                await self._link_pairings(cigar_id, value)
        report.updated += 1

    async def _link_field(self, cigar_id: str, field: str, value: str) -> None:
        node_type, rel = _FIELD_SPEC[field]
        target = node_id(node_type, slugify(value))
        await self._kg.upsert_node(KGNode(id=target, type=node_type, label=value))
        await self._kg.upsert_edge(KGEdge(src=cigar_id, dst=target, rel=rel))

    async def _link_pairings(self, cigar_id: str, strength: str) -> None:
        for pslug in _STRENGTH_PAIRINGS.get(strength, []):
            label = _PAIRING_LABELS.get(pslug, pslug)
            pid = node_id(NodeType.PAIRING, pslug)
            await self._kg.upsert_node(KGNode(id=pid, type=NodeType.PAIRING, label=label))
            await self._kg.upsert_edge(KGEdge(src=cigar_id, dst=pid, rel=EdgeRel.PAIRS_WITH))
