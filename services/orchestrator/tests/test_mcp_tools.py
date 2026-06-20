"""Testes das ferramentas MCP (S14).

A lógica determinística (`CigarTools`) e a camada MCP in-process são verificáveis SEM chave
de API (MCP é local). Só o `AnthropicToolRunner` end-to-end exige chave (`skipif`).
"""

import os

import pytest
from charutei_knowledge import (
    EdgeRel,
    InMemoryKnowledgeGraph,
    KGEdge,
    KGNode,
    NodeType,
    node_id,
)
from charutei_orchestrator import (
    AgentTool,
    CigarTools,
    FakeToolRunner,
    RetrievedDoc,
    build_cigar_tools,
    build_mcp_server,
)

COHIBA = node_id(NodeType.CIGAR, "cohiba-siglo-vi")
MONTE = node_id(NodeType.CIGAR, "montecristo-no-4")


async def _kg() -> InMemoryKnowledgeGraph:
    kg = InMemoryKnowledgeGraph()
    for cid, label in [(COHIBA, "Cohiba Siglo VI"), (MONTE, "Montecristo No. 4")]:
        await kg.upsert_node(KGNode(id=cid, type=NodeType.CIGAR, label=label))
    cuba = node_id(NodeType.COUNTRY, "cuba")
    await kg.upsert_node(KGNode(id=cuba, type=NodeType.COUNTRY, label="Cuba"))
    rum = node_id(NodeType.PAIRING, "rum-anejo")
    await kg.upsert_node(KGNode(id=rum, type=NodeType.PAIRING, label="Rum envelhecido"))
    for cid in (COHIBA, MONTE):
        await kg.upsert_edge(KGEdge(src=cid, dst=cuba, rel=EdgeRel.FROM_COUNTRY))
    await kg.upsert_edge(KGEdge(src=COHIBA, dst=rum, rel=EdgeRel.PAIRS_WITH))
    return kg


class _FakeRetriever:
    async def search(self, query: str, k: int = 4) -> list[RetrievedDoc]:
        return [RetrievedDoc(id="doc:storage", title="Armazenamento", text="Use umidor a 70%.")]


async def test_kg_query_returns_facts_with_citation() -> None:
    tools = CigarTools(await _kg())
    res = await tools.kg_query("fale do Cohiba Siglo VI")
    assert "Cuba" in res.text
    assert res.citations and res.citations[0].source_id == COHIBA


async def test_harmonize_returns_pairings() -> None:
    tools = CigarTools(await _kg())
    res = await tools.harmonize("com o que harmoniza o cohiba siglo vi?")
    assert "Rum" in res.text
    assert res.citations[0].source_id == node_id(NodeType.PAIRING, "rum-anejo")


async def test_compare_needs_two_cigars() -> None:
    tools = CigarTools(await _kg())
    one = await tools.compare("fale do cohiba siglo vi")
    assert one.text == ""  # só um charuto → sem comparação
    two = await tools.compare("compare cohiba siglo vi com montecristo no. 4")
    assert "Cohiba" in two.text and "Montecristo" in two.text
    assert {c.source_id for c in two.citations} == {COHIBA, MONTE}


async def test_rag_search_returns_snippets() -> None:
    tools = CigarTools(await _kg(), retriever=_FakeRetriever())
    res = await tools.rag_search("como armazenar charutos?")
    assert "umidor" in res.text.lower()
    assert res.citations[0].source_id == "doc:storage"
    # sem retriever → vazio (não inventa)
    assert (await CigarTools(await _kg()).rag_search("x")).text == ""


async def test_build_cigar_tools_feeds_fake_runner() -> None:
    tools = build_cigar_tools(CigarTools(await _kg(), retriever=_FakeRetriever()))
    assert {t.name for t in tools} == {"kg_query", "harmonize", "compare", "rag_search"}
    assert all(isinstance(t, AgentTool) for t in tools)
    out = await FakeToolRunner().run(
        model="opus-4.8", system="s", prompt="fale do cohiba siglo vi", tools=tools
    )
    assert out.confidence == 1.0
    assert any(c.source_id == COHIBA for c in out.citations)


# --- Camada MCP in-process (local, sem chave; pulada no CI sem o extra `providers`) ---


@pytest.mark.asyncio
async def test_mcp_server_lists_and_executes_tools() -> None:
    pytest.importorskip("mcp")
    from mcp.shared.memory import create_connected_server_and_client_session

    server = build_mcp_server(CigarTools(await _kg(), retriever=_FakeRetriever()))
    async with create_connected_server_and_client_session(server) as session:
        await session.initialize()
        listed = await session.list_tools()
        assert {t.name for t in listed.tools} == {
            "kg_query",
            "harmonize",
            "compare",
            "rag_search",
        }
        call = await session.call_tool("harmonize", arguments={"query": "cohiba siglo vi"})
        raw = "".join(getattr(c, "text", "") for c in call.content)
        assert "Rum" in raw and "rum-anejo" in raw  # ToolResult serializado com citação


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"), reason="exige ANTHROPIC_API_KEY (loop Opus real)"
)
async def test_anthropic_tool_runner_end_to_end() -> None:
    from charutei_orchestrator import AnthropicToolRunner

    server = build_mcp_server(CigarTools(await _kg(), retriever=_FakeRetriever()))
    runner = AnthropicToolRunner(server)
    out = await runner.run(
        model="opus-4.8",
        system="Você é especialista em charutos. Use as ferramentas e cite as fontes.",
        prompt="Com o que harmoniza o Cohiba Siglo VI?",
        tools=[],
    )
    assert out.text
    assert out.cost_usd > 0.0
    assert out.tool_calls  # o modelo deve ter chamado ao menos uma ferramenta
