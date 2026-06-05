"""Eval `band_recognition` — acurácia top-1 + % resolvido SEM LLM de visão.

Gate (Anexo C): acurácia ≥0.90 e ≥80% das anilhas resolvidas por embedding/OCR (sem visão).
Exercita o pipeline real do agente com providers fake e o catálogo semeado.
"""

from __future__ import annotations

import json
from pathlib import Path

from charutei_contracts import BandImage

from evals._band_fixtures import build_band_agent, cigar_node
from evals.harness import EvalReport

_IMAGES = Path(__file__).resolve().parent / "datasets" / "band_images.json"

GATE_WITHOUT_VISION = 0.80
GATE_ACCURACY = 0.90


async def run() -> EvalReport:
    agent = await build_band_agent()
    images = json.loads(_IMAGES.read_text(encoding="utf-8"))["images"]

    total = len(images)
    correct = 0
    without_vision = 0
    for item in images:
        result = await agent.recognize(
            BandImage(ref=item["ref"], visual_text=item["visual_text"], ocr_text=item["ocr_text"])
        )
        if result.cigar_id == cigar_node(item["truth"]):
            correct += 1
        if result.cigar_id is not None and not result.used_vision_llm:
            without_vision += 1

    accuracy = correct / total if total else 0.0
    pct_without_vision = without_vision / total if total else 1.0
    passed = accuracy >= GATE_ACCURACY and pct_without_vision >= GATE_WITHOUT_VISION
    return EvalReport(
        name="band_recognition",
        passed=passed,
        summary=(
            f"acurácia {accuracy:.0%} · {pct_without_vision:.0%} resolvido sem visão "
            f"({total - without_vision}/{total} usaram visão)"
        ),
        details={"accuracy": accuracy, "pct_without_vision": pct_without_vision},
    )
