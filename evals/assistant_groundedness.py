"""Eval `assistant_groundedness` — respostas ancoradas nas fontes citadas.

Gate (Anexo C): sem alucinação acima do limite. Heurística do MVP (substituível por juiz LLM):
toda resposta gerada/determinística deve trazer ≥1 citação, e ao menos uma fonte citada deve
ser relevante à pergunta (sobreposição lexical p/ RAG; nó do KG p/ fato).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from charutei_contracts import Tier

from evals._fixtures import build_assistant
from evals.harness import EvalReport

_QUERIES = Path(__file__).resolve().parent / "datasets" / "assistant_queries.json"
GATE_GROUNDED = 0.90


def _tokens(text: str) -> set[str]:
    return set(re.sub(r"[^a-z0-9 ]+", " ", text.lower()).split())


async def run() -> EvalReport:
    assistant = await build_assistant()
    queries = json.loads(_QUERIES.read_text(encoding="utf-8"))["queries"]

    answered = 0
    grounded = 0
    for item in queries:
        result = await assistant.ask(item["q"])
        if result.answer is None or result.needs_human:
            continue
        answered += 1
        if not result.citations:
            continue  # resposta sem fonte = não ancorada
        # KG (degrau 2) é ancorado por construção; RAG exige sobreposição com a pergunta.
        if result.tier_resolved <= Tier.DETERMINISTIC:
            grounded += 1
        else:
            q = _tokens(item["q"])
            if any(
                _tokens((c.snippet or "") + " " + (c.title or "")) & q for c in result.citations
            ):
                grounded += 1

    rate = grounded / answered if answered else 1.0
    return EvalReport(
        name="assistant_groundedness",
        passed=rate >= GATE_GROUNDED,
        summary=f"{rate:.0%} das respostas ancoradas em fontes citadas ({grounded}/{answered})",
        details={"grounded_rate": rate},
    )
