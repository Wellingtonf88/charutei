"""Ferramentas do laço agêntico — read-only, DETERMINÍSTICAS, sem LLM.

Envolvem o Knowledge Graph e a recuperação de documentos (RAG) já existentes. São a única
"superfície de ação" do loop Opus (S13): o modelo decide *quais* chamar, mas cada ferramenta
resolve por SQL/grafo/retrieval — nenhuma chama LLM/embedding de geração. Isso mantém
"LLM é o último recurso": o loop é o último recurso, e suas ferramentas continuam baratas.

Fonte única da lógica (`CigarTools`), exposta por dois caminhos:
- `build_cigar_tools()` → `list[AgentTool]` para o `FakeToolRunner` (CI, hermético);
- `build_mcp_server()` → servidor MCP in-process para o `AnthropicToolRunner` real (S14).

O Orchestrator NÃO importa o pacote `assistant` (direção de dependência): a recuperação de
documentos entra por um Protocol `DocRetriever`, que o Assistant adapta na S16.
"""

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from charutei_contracts import Citation
from charutei_knowledge import KnowledgeGraphRepo, NodeType
from pydantic import BaseModel

from charutei_orchestrator.agent_loop import AgentTool, ToolResult

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def _norm(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()


class RetrievedDoc(BaseModel):
    """Documento recuperado pela busca (sem geração de LLM)."""

    id: str
    title: str
    text: str
    score: float = 0.0


@runtime_checkable
class DocRetriever(Protocol):
    """Recuperação de documentos para `rag_search` — adaptada do `DocumentStore` na S16."""

    async def search(self, query: str, k: int = 4) -> list[RetrievedDoc]: ...


class CigarTools:
    """Lógica determinística das 4 ferramentas. Reusada pelo caminho fake e pelo MCP real."""

    def __init__(self, kg: KnowledgeGraphRepo, retriever: DocRetriever | None = None) -> None:
        self._kg = kg
        self._retriever = retriever
        self._index: dict[str, str] | None = None  # nome normalizado → cigar_id (lazy)

    async def _ensure_index(self) -> dict[str, str]:
        if self._index is None:
            cigars = await self._kg.nodes_by_type(NodeType.CIGAR)
            self._index = {_norm(n.label): n.id for n in cigars}
        return self._index

    async def _match_cigars(self, text: str) -> list[str]:
        """Casa nomes de charutos contidos no texto (mais longos primeiro, sem sobreposição)."""
        index = await self._ensure_index()
        q = _norm(text)
        matches = sorted(
            ((name, cid) for name, cid in index.items() if name in q),
            key=lambda nc: len(nc[0]),
            reverse=True,
        )
        chosen: list[str] = []
        consumed = ""
        for name, cid in matches:
            if name in consumed:
                continue
            chosen.append(cid)
            consumed += " " + name
        return chosen

    async def kg_query(self, query: str) -> ToolResult:
        """Ficha técnica do charuto citado (vizinhos no grafo) — fato determinístico."""
        cigars = await self._match_cigars(query)
        if not cigars:
            return ToolResult(text="")
        cid = cigars[0]
        neighbors = await self._kg.neighbors(cid)
        node = await self._kg.get_node(cid)
        title = node.label if node else cid
        if not neighbors:
            return ToolResult(text="")
        facts = "; ".join(f"{n.type}: {n.label}" for n in neighbors)
        return ToolResult(
            text=f"{title} — {facts}",
            citations=[Citation(source_id=cid, title=title)],
        )

    async def harmonize(self, query: str) -> ToolResult:
        """Harmonizações (arestas pairs_with) do charuto citado."""
        cigars = await self._match_cigars(query)
        if not cigars:
            return ToolResult(text="")
        cid = cigars[0]
        pairings = await self._kg.harmonizations(cid)
        if not pairings:
            return ToolResult(text="")
        text = "Harmoniza com: " + ", ".join(p.label for p in pairings) + "."
        return ToolResult(
            text=text,
            citations=[Citation(source_id=p.id, title=p.label) for p in pairings],
        )

    async def compare(self, query: str) -> ToolResult:
        """Fichas lado a lado de dois charutos citados."""
        cigars = await self._match_cigars(query)
        if len(cigars) < 2:
            return ToolResult(text="")
        parts: list[str] = []
        citations: list[Citation] = []
        for cid in cigars[:2]:
            node = await self._kg.get_node(cid)
            title = node.label if node else cid
            neighbors = await self._kg.neighbors(cid)
            facts = "; ".join(f"{n.type}: {n.label}" for n in neighbors) or "sem dados"
            parts.append(f"{title}: {facts}")
            citations.append(Citation(source_id=cid, title=title))
        return ToolResult(text=" | ".join(parts), citations=citations)

    async def rag_search(self, query: str) -> ToolResult:
        """Recupera trechos de documentos relevantes (retrieval + compressão, sem geração)."""
        if self._retriever is None:
            return ToolResult(text="")
        docs = await self._retriever.search(query, k=4)
        if not docs:
            return ToolResult(text="")
        snippets = [f"[{d.id}] {d.title}: {d.text}" for d in docs[:3]]
        citations = [Citation(source_id=d.id, title=d.title, snippet=d.text) for d in docs[:3]]
        return ToolResult(text=" ".join(snippets), citations=citations)


_TOOL_SPECS: list[tuple[str, str]] = [
    ("kg_query", "Retorna a ficha técnica (país, marca, força, vitola) do charuto citado."),
    ("harmonize", "Retorna as harmonizações (bebidas/acompanhamentos) do charuto citado."),
    ("compare", "Compara as fichas de dois charutos citados na pergunta."),
    ("rag_search", "Recupera trechos de documentos de conhecimento geral sobre charutos."),
]


def build_cigar_tools(tools: CigarTools) -> list[AgentTool]:
    """Lista de `AgentTool` (caminho `FakeToolRunner`) — cada uma envolve um método."""
    handlers = {
        "kg_query": tools.kg_query,
        "harmonize": tools.harmonize,
        "compare": tools.compare,
        "rag_search": tools.rag_search,
    }
    return [
        AgentTool(name=name, description=desc, handler=handlers[name]) for name, desc in _TOOL_SPECS
    ]


def build_mcp_server(tools: CigarTools, *, name: str = "charutei-cigar-tools") -> FastMCP:
    """Servidor MCP in-process expondo as 4 ferramentas (caminho `AnthropicToolRunner`).

    `mcp` é lazy-import (extra `providers`); cada tool aceita `query: str` e devolve o
    `ToolResult` serializado em JSON — o runner real extrai texto + citações de volta.
    """
    from mcp.server.fastmcp import FastMCP

    server = FastMCP(name)
    methods = {
        "kg_query": tools.kg_query,
        "harmonize": tools.harmonize,
        "compare": tools.compare,
        "rag_search": tools.rag_search,
    }

    def _register(tool_name: str, desc: str) -> None:
        method = methods[tool_name]

        async def _tool(query: str) -> str:
            result = await method(query)
            return result.model_dump_json()

        _tool.__name__ = tool_name
        _tool.__doc__ = desc
        server.add_tool(_tool, name=tool_name, description=desc)

    for tname, tdesc in _TOOL_SPECS:
        _register(tname, tdesc)
    return server
