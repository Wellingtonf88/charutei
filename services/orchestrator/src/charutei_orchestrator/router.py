"""Router determinístico — classifica intenção SEM LLM (regras + palavras-chave).

É o coração cost-aware: decide *antes* de gastar token se a consulta é resolvível por
KG/SQL (degrau 2) ou se precisa de geração (degraus 3-5). Roteia a maioria do tráfego para
os degraus baratos. Um classificador leve/destilado pode substituí-lo na escala — mesma saída.
"""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel

_HARMONIZATION = re.compile(
    r"\b(harmoniz\w*|combina\w*|acompanh\w*|pairing|bebida|com o que)\b", re.IGNORECASE
)
_FACT_LOOKUP = re.compile(
    r"\b(o que é|qual\w*|força|vitola|país|pais|marca|fábrica|fabrica|origem)\b", re.IGNORECASE
)


class Intent(StrEnum):
    HARMONIZATION = "harmonization"  # → KG (pairs_with)
    FACT_LOOKUP = "fact_lookup"  # → KG/SQL (ficha técnica)
    GENERAL = "general"  # → geração (RAG)


class RouteDecision(BaseModel):
    intent: Intent
    kg_lookup: bool  # tentar resolver no degrau determinístico antes de gerar
    allow_generation: bool  # pode subir para degraus de modelo se KG/cache falharem


def classify(text: str) -> RouteDecision:
    """Classificação puramente determinística da consulta do usuário."""
    if _HARMONIZATION.search(text):
        return RouteDecision(intent=Intent.HARMONIZATION, kg_lookup=True, allow_generation=True)
    if _FACT_LOOKUP.search(text):
        return RouteDecision(intent=Intent.FACT_LOOKUP, kg_lookup=True, allow_generation=True)
    return RouteDecision(intent=Intent.GENERAL, kg_lookup=False, allow_generation=True)
