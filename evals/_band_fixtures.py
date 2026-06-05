"""Montagem de um Band Recognition Agent com fakes + catálogo semeado (para evals/testes)."""

from __future__ import annotations

import json
from pathlib import Path

from charutei_band_recognition import BandRecognitionAgent, build_band_catalog, default_spec
from charutei_knowledge import InMemoryVectorRepository, NodeType, node_id
from charutei_orchestrator import AgentRegistry, FakeTracer, Governance, build_band_providers

_SEED = Path(__file__).resolve().parent / "datasets" / "cigars_seed.json"


async def build_band_agent() -> BandRecognitionAgent:
    cigars = json.loads(_SEED.read_text(encoding="utf-8"))["cigars"]
    catalog_input = [(node_id(NodeType.CIGAR, c["slug"]), c["name"]) for c in cigars]

    image_embed, ocr, vision = build_band_providers(use_fake=True)
    vector_repo = InMemoryVectorRepository()
    labels = await build_band_catalog(image_embed, vector_repo, catalog_input)

    registry = AgentRegistry()
    registry.register(default_spec())

    return BandRecognitionAgent(
        registry=registry,
        governance=Governance(),
        image_embed=image_embed,
        ocr=ocr,
        vision=vision,
        vector_repo=vector_repo,
        tracer=FakeTracer(),
        labels=labels,
    )


def cigar_node(slug: str) -> str:
    return node_id(NodeType.CIGAR, slug)
