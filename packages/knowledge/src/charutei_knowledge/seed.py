"""Carrega o seed curado de charutos no Knowledge Graph.

Constrói nós (cigar/brand/country/vitola/strength/factory/pairing) e arestas a partir de
`evals/datasets/cigars_seed.json`. Idempotente: roda quantas vezes quiser (upsert por id
canônico). Funciona contra QUALQUER `KnowledgeGraphRepo` (in-memory ou Postgres).
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from charutei_knowledge.interfaces import KnowledgeGraphRepo
from charutei_knowledge.memory import node_id
from charutei_knowledge.models import EdgeRel, KGEdge, KGNode, NodeType

DEFAULT_DATASET = Path(__file__).resolve().parents[4] / "evals" / "datasets" / "cigars_seed.json"


def slugify(value: str) -> str:
    """Slug ASCII estável p/ ids de nó (remove acentos, espaços → hífen)."""
    norm = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", norm.lower()).strip("-")


@dataclass
class SeedStats:
    nodes: int
    edges: int
    cigars: int


async def seed_knowledge_graph(
    kg: KnowledgeGraphRepo, dataset_path: Path | None = None
) -> SeedStats:
    path = dataset_path or DEFAULT_DATASET
    data = json.loads(path.read_text(encoding="utf-8"))
    pairings: dict[str, str] = data.get("pairings", {})

    seen_nodes: set[str] = set()
    edge_count = 0

    async def add_node(node_type: NodeType, slug: str, label: str, **props: object) -> str:
        nid = node_id(node_type, slug)
        if nid not in seen_nodes:
            await kg.upsert_node(KGNode(id=nid, type=node_type, label=label, props=props))
            seen_nodes.add(nid)
        return nid

    async def add_edge(src: str, dst: str, rel: EdgeRel) -> None:
        nonlocal edge_count
        await kg.upsert_edge(KGEdge(src=src, dst=dst, rel=rel))
        edge_count += 1

    # Nós de harmonização (pairings) primeiro.
    for pslug, plabel in pairings.items():
        await add_node(NodeType.PAIRING, pslug, plabel)

    cigars = data.get("cigars", [])
    for c in cigars:
        cigar_nid = await add_node(NodeType.CIGAR, c["slug"], c["name"], strength=c.get("strength"))

        brand_nid = await add_node(NodeType.BRAND, slugify(c["brand"]), c["brand"])
        await add_edge(cigar_nid, brand_nid, EdgeRel.MADE_BY)

        country_nid = await add_node(NodeType.COUNTRY, slugify(c["country"]), c["country"])
        await add_edge(cigar_nid, country_nid, EdgeRel.FROM_COUNTRY)

        if c.get("vitola"):
            vitola_nid = await add_node(NodeType.VITOLA, slugify(c["vitola"]), c["vitola"])
            await add_edge(cigar_nid, vitola_nid, EdgeRel.HAS_VITOLA)

        if c.get("strength"):
            strength_nid = await add_node(NodeType.STRENGTH, c["strength"], c["strength"])
            await add_edge(cigar_nid, strength_nid, EdgeRel.HAS_STRENGTH)

        # fábrica raramente é pública por SKU — só cria nó quando informada (não inventar).
        if c.get("factory"):
            factory_nid = await add_node(NodeType.FACTORY, slugify(c["factory"]), c["factory"])
            await add_edge(cigar_nid, factory_nid, EdgeRel.PRODUCED_AT)

        for pslug in c.get("pairings", []):
            await add_edge(cigar_nid, node_id(NodeType.PAIRING, pslug), EdgeRel.PAIRS_WITH)

    return SeedStats(nodes=len(seen_nodes), edges=edge_count, cigars=len(cigars))
