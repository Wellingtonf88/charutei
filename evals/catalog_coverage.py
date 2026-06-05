"""Eval `catalog_coverage` — integridade do KG após ingestão do catálogo de SKU.

Verifica quatro propriedades usando o KG in-memory semeado + catálogo completo (sem I/O externo,
sem LLM): cobertura de SKUs, arestas obrigatórias, pairings por regra de força e ausência de
vitola apenas onde o CSV também não tem.

Gates:
- catalog_coverage   = 1.0  → todo SKU do CSV existe no KG como nó `cigar`
- required_edges_pct = 1.0  → cada cigar tem made_by + from_country + has_strength
- pairing_coverage   = 1.0  → cigars com strength known têm ≥1 aresta pairs_with
- vitola_null_ok     = 1.0  → has_vitola ausente somente nos SKUs com vitola=null no CSV
"""

from __future__ import annotations

from pathlib import Path

from charutei_cigar_intelligence import CatalogIngestor, parse_catalog_csv
from charutei_knowledge import InMemoryKnowledgeGraph, NodeType, node_id, seed_knowledge_graph

from evals.harness import EvalReport

_CATALOG = Path(__file__).resolve().parents[1] / "data" / "catalog" / "cigars.csv"

GATE_COVERAGE = 1.0
GATE_EDGES = 1.0
GATE_PAIRINGS = 1.0
GATE_VITOLA = 1.0


async def run() -> EvalReport:
    kg = InMemoryKnowledgeGraph()
    await seed_knowledge_graph(kg)
    records = parse_catalog_csv(_CATALOG)
    await CatalogIngestor(kg).ingest(records)

    total = len(records)
    missing_skus: list[str] = []
    missing_edges: list[str] = []
    missing_pairings: list[str] = []
    wrong_vitola: list[str] = []

    for rec in records:
        cid = node_id(NodeType.CIGAR, rec.slug)
        node = await kg.get_node(cid)
        if node is None:
            missing_skus.append(rec.slug)
            continue

        # made_by + from_country + has_strength são obrigatórios (campos always-present no CSV)
        neighbors_made_by = await kg.neighbors(cid, rel="made_by")
        neighbors_country = await kg.neighbors(cid, rel="from_country")
        neighbors_strength = await kg.neighbors(cid, rel="has_strength")
        if not (neighbors_made_by and neighbors_country and neighbors_strength):
            missing_edges.append(rec.slug)

        # pairings: obrigatório quando strength está presente
        if rec.strength is not None:
            pairings = await kg.harmonizations(cid)
            if not pairings:
                missing_pairings.append(rec.slug)

        # vitola: has_vitola ausente só é válido se vitola=null no CSV
        neighbors_vitola = await kg.neighbors(cid, rel="has_vitola")
        if rec.vitola is not None and not neighbors_vitola:
            wrong_vitola.append(rec.slug)

    catalog_coverage = (total - len(missing_skus)) / total
    required_edges_pct = (total - len(missing_edges)) / total
    pairing_coverage = (total - len(missing_pairings)) / total
    vitola_null_ok = (total - len(wrong_vitola)) / total

    passed = (
        catalog_coverage >= GATE_COVERAGE
        and required_edges_pct >= GATE_EDGES
        and pairing_coverage >= GATE_PAIRINGS
        and vitola_null_ok >= GATE_VITOLA
    )

    issues: list[str] = []
    if missing_skus:
        issues.append(f"SKUs ausentes: {missing_skus}")
    if missing_edges:
        issues.append(f"arestas obrigatórias faltando: {missing_edges}")
    if missing_pairings:
        issues.append(f"pairings ausentes: {missing_pairings}")
    if wrong_vitola:
        issues.append(f"vitola faltando indevida: {wrong_vitola}")

    summary = (
        f"{total} SKUs · cobertura {catalog_coverage:.0%} · "
        f"arestas {required_edges_pct:.0%} · pairings {pairing_coverage:.0%} · "
        f"vitola_null_ok {vitola_null_ok:.0%}"
    )
    if issues:
        summary += " | " + "; ".join(issues)

    return EvalReport(
        name="catalog_coverage",
        passed=passed,
        summary=summary,
        details={
            "catalog_coverage": catalog_coverage,
            "required_edges_pct": required_edges_pct,
            "pairing_coverage": pairing_coverage,
            "vitola_null_ok": vitola_null_ok,
        },
    )
