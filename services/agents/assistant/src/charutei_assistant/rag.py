"""RAG mínimo (degrau 4): recuperação híbrida → rerank → compressão → geração com citações.

Preferimos responder pelo KG (fato determinístico); o RAG entra só quando a resposta é
não-estruturada (ex.: "como armazenar"). Reduz tokens com rerank (poucos chunks) + compressão
extrativa, e devolve **citações** das fontes recuperadas — base da groundedness.
"""

from __future__ import annotations

import re

from charutei_cache.interfaces import VectorIndex
from charutei_contracts import Citation
from charutei_orchestrator import EmbeddingProvider, GenerationOutput, LLMProvider
from charutei_orchestrator.providers import EMBED_PRICING
from pydantic import BaseModel

DOCS_KIND = "docs"
_EMBED_MODEL = "voyage-4-lite"


class Document(BaseModel):
    id: str
    title: str
    text: str


def _tokens(text: str) -> set[str]:
    return set(re.sub(r"[^a-z0-9 ]+", " ", text.lower()).split())


def _compress(text: str, query: str, max_sentences: int = 2) -> str:
    """Compressão extrativa: mantém as frases mais relevantes à pergunta (corta tokens)."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    q = _tokens(query)
    ranked = sorted(sentences, key=lambda s: len(_tokens(s) & q), reverse=True)
    kept = [s for s in ranked if _tokens(s) & q][:max_sentences] or sentences[:1]
    # preserva a ordem original das frases mantidas
    return " ".join(s for s in sentences if s in kept)


class DocumentStore:
    def __init__(self, embed: EmbeddingProvider, index: VectorIndex) -> None:
        self._embed = embed
        self._index = index
        self._docs: dict[str, Document] = {}

    async def index_docs(self, docs: list[Document]) -> None:
        for doc in docs:
            (vec,) = await self._embed.embed([doc.text], model=_EMBED_MODEL)
            await self._index.upsert(DOCS_KIND, doc.id, vec, {"title": doc.title})
            self._docs[doc.id] = doc

    async def search(self, query: str, k: int = 4) -> list[tuple[Document, float]]:
        (q_vec,) = await self._embed.embed([query], model=_EMBED_MODEL)
        hits = await self._index.ann_search(DOCS_KIND, q_vec, k=k)
        return [(self._docs[i], s) for i, s in hits if i in self._docs]


class RagGenerator:
    """Implementa o hook `Generator` da cascata: gera ancorado em documentos recuperados."""

    def __init__(
        self,
        embed: EmbeddingProvider,
        doc_store: DocumentStore,
        llm: LLMProvider,
        *,
        k: int = 4,
        top_n: int = 3,
    ) -> None:
        self._embed = embed
        self._store = doc_store
        self._llm = llm
        self._k = k
        self._top_n = top_n

    async def generate(self, model: str, system: str, prompt: str) -> GenerationOutput:
        hits = await self._store.search(prompt, k=self._k)
        # rerank leve por sobreposição lexical (cross-encoder/Voyage rerank na produção).
        q = _tokens(prompt)
        reranked = sorted(hits, key=lambda h: len(_tokens(h[0].text) & q), reverse=True)
        chosen = reranked[: self._top_n]

        embed_cost = EMBED_PRICING[_EMBED_MODEL] * len(prompt.split())
        if not chosen:
            # Sem fonte recuperada → resposta não ancorada: baixa confiança permite que a
            # governança escale a Opus/HITL (último recurso). Não é o score de retrieval.
            resp = await self._llm.generate(model=model, system=system, prompt=prompt)
            return GenerationOutput(
                text=resp.text,
                model=resp.model,
                citations=[],
                input_tokens=resp.input_tokens,
                output_tokens=resp.output_tokens,
                cost_usd=resp.cost_usd + embed_cost,
                confidence=0.4,
            )

        context_parts = []
        citations: list[Citation] = []
        for doc, _ in chosen:
            snippet = _compress(doc.text, prompt)
            context_parts.append(f"[{doc.id}] {doc.title}: {snippet}")
            citations.append(Citation(source_id=doc.id, title=doc.title, snippet=snippet))
        context = "\n".join(context_parts)

        # Prompt caching nativo se aplica ao system/instruções na produção (-90% no cacheado).
        resp = await self._llm.generate(
            model=model,
            system=f"{system}\n\nContexto:\n{context}",
            prompt=prompt,
        )
        # Resposta ancorada em fontes → confiança alta (não escala a Opus). O score de retrieval
        # mede relevância da recuperação, não a confiança final da geração.
        return GenerationOutput(
            text=resp.text,
            model=resp.model,
            citations=citations,
            input_tokens=resp.input_tokens,
            output_tokens=resp.output_tokens,
            cost_usd=resp.cost_usd + embed_cost,
            confidence=0.9,
        )
