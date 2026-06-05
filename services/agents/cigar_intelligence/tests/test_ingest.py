"""Testes do Cigar Intelligence: criação, idempotência, conflito→HITL e enriquecimento."""

import pytest
from charutei_cigar_intelligence import (
    CatalogIngestor,
    CatalogRecord,
    InMemoryReviewQueue,
    parse_catalog_csv,
)
from charutei_events import InMemoryOutbox
from charutei_knowledge import InMemoryKnowledgeGraph, KGNode, NodeType, node_id

_REC = CatalogRecord(
    slug="oliva-serie-o-robusto",
    name="Oliva Serie O Robusto",
    brand="Oliva",
    country="Nicaragua",
    vitola="Robusto",
    strength="medium",
)
_FULL = CatalogRecord(
    slug="ashton-vsg-robusto",
    name="Ashton VSG Robusto",
    brand="Ashton",
    country="República Dominicana",
    vitola="Robusto",
    strength="full",
)


async def test_creates_cigar_with_edges_and_pairings() -> None:
    kg = InMemoryKnowledgeGraph()
    outbox = InMemoryOutbox()
    report = await CatalogIngestor(kg, outbox=outbox).ingest([_REC, _FULL])

    assert report.created == 2
    cid = node_id(NodeType.CIGAR, "ashton-vsg-robusto")
    brands = await kg.neighbors(cid, rel="made_by")
    assert brands[0].label == "Ashton"
    pairings = {p.label for p in await kg.harmonizations(cid)}
    assert "Rum envelhecido" in pairings  # regra de força (full)
    assert outbox._pending  # publicou sku.detectado  # noqa: SLF001


async def test_idempotent_reingest_is_unchanged() -> None:
    kg = InMemoryKnowledgeGraph()
    ingestor = CatalogIngestor(kg)
    await ingestor.ingest([_REC])
    report = await ingestor.ingest([_REC])  # segunda vez
    assert report.created == 0
    assert report.unchanged == 1


async def test_conflict_goes_to_review_without_overwrite() -> None:
    kg = InMemoryKnowledgeGraph()
    review = InMemoryReviewQueue()
    await CatalogIngestor(kg, review_queue=review).ingest([_REC])

    # mesmo SKU, marca divergente → conflito
    conflicting = _REC.model_copy(update={"brand": "OUTRA MARCA"})
    report = await CatalogIngestor(kg, review_queue=review).ingest([conflicting])
    assert report.conflicts == 1
    assert review.items[0].field == "brand"
    # não sobrescreveu
    node = await kg.get_node(node_id(NodeType.CIGAR, _REC.slug))
    assert node is not None and node.props["brand"] == "Oliva"


async def test_apply_conflicts_overwrites() -> None:
    kg = InMemoryKnowledgeGraph()
    await CatalogIngestor(kg).ingest([_REC])
    conflicting = _REC.model_copy(update={"brand": "Oliva Tabacalera"})
    report = await CatalogIngestor(kg).ingest([conflicting], apply_conflicts=True)
    assert report.updated == 1
    node = await kg.get_node(node_id(NodeType.CIGAR, _REC.slug))
    assert node is not None and node.props["brand"] == "Oliva Tabacalera"


async def test_enriches_missing_field() -> None:
    kg = InMemoryKnowledgeGraph()
    cid = node_id(NodeType.CIGAR, _REC.slug)
    # nó pré-existente só com strength (como vem do seed) — sem brand
    await kg.upsert_node(
        KGNode(id=cid, type=NodeType.CIGAR, label=_REC.name, props={"strength": "medium"})
    )
    report = await CatalogIngestor(kg).ingest([_REC])
    assert report.updated == 1  # preencheu brand/country/vitola ausentes
    node = await kg.get_node(cid)
    assert node is not None and node.props["brand"] == "Oliva"
    assert (await kg.neighbors(cid, rel="made_by"))[0].label == "Oliva"


async def test_parser_reads_real_catalog(tmp_path) -> None:  # type: ignore[no-untyped-def]
    csv = tmp_path / "c.csv"
    csv.write_text(
        "slug,name,brand,country,vitola,strength,factory\nx-1,Charuto X,Marca,Cuba,Robusto,full,\n",
        encoding="utf-8",
    )
    records = parse_catalog_csv(csv)
    assert len(records) == 1 and records[0].strength == "full"


async def test_parser_rejects_invalid_strength(tmp_path) -> None:  # type: ignore[no-untyped-def]
    csv = tmp_path / "c.csv"
    csv.write_text(
        "slug,name,brand,country,vitola,strength,factory\nx,X,M,Cuba,R,ULTRA,\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="força inválida"):
        parse_catalog_csv(csv)
