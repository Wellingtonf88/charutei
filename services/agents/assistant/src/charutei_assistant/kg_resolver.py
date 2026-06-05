"""Resolver determinístico do assistente (degrau 2): responde fatos pelo KG, sem LLM.

Detecta o charuto citado e devolve harmonização (pairs_with) ou ficha técnica (vizinhos),
sempre com **citações** ancoradas em nós do grafo. Não sabe responder → None (sobe p/ RAG).
"""

from __future__ import annotations

import re
import unicodedata

from charutei_contracts import CascadeResult, Citation, Tier
from charutei_knowledge import KnowledgeGraphRepo, NodeType
from charutei_orchestrator.router import Intent, RouteDecision


def _norm(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()


class KGAssistantResolver:
    def __init__(self, kg: KnowledgeGraphRepo) -> None:
        self._kg = kg
        self._index: dict[str, str] | None = None  # nome normalizado → cigar_id (lazy)

    async def _ensure_index(self) -> dict[str, str]:
        if self._index is None:
            cigars = await self._kg.nodes_by_type(NodeType.CIGAR)
            self._index = {_norm(n.label): n.id for n in cigars}
        return self._index

    async def _find_cigar(self, text: str) -> str | None:
        index = await self._ensure_index()
        q = _norm(text)
        # casa o nome mais longo contido na pergunta (evita match parcial ambíguo).
        best: str | None = None
        best_len = 0
        for name, cid in index.items():
            if name in q and len(name) > best_len:
                best, best_len = cid, len(name)
        return best

    async def resolve(self, text: str, route: RouteDecision) -> CascadeResult | None:
        cigar_id = await self._find_cigar(text)
        if cigar_id is None:
            return None

        if route.intent == Intent.HARMONIZATION:
            pairings = await self._kg.harmonizations(cigar_id)
            if not pairings:
                return None
            answer = "Harmoniza com: " + ", ".join(p.label for p in pairings) + "."
            citations = [Citation(source_id=p.id, title=p.label) for p in pairings]
            return CascadeResult(
                answer=answer, tier_resolved=Tier.DETERMINISTIC, citations=citations
            )

        if route.intent == Intent.FACT_LOOKUP:
            neighbors = await self._kg.neighbors(cigar_id)
            if not neighbors:
                return None
            facts = "; ".join(f"{n.type}: {n.label}" for n in neighbors)
            node = await self._kg.get_node(cigar_id)
            title = node.label if node else cigar_id
            return CascadeResult(
                answer=facts,
                tier_resolved=Tier.DETERMINISTIC,
                citations=[Citation(source_id=cigar_id, title=title)],
            )

        return None
