"""Laço agêntico (tool-use) — o ÚLTIMO recurso do último recurso.

Roda *apenas* no degrau Opus gated da cascata (`Cascade._generate`, ramo de escalada),
quando o RAG não ancorou E a governança autorizou Opus. Substitui a segunda chamada
single-shot a Opus por um loop de raciocínio com ferramentas.

As ferramentas (`AgentTool`) são DETERMINÍSTICAS — envolvem KG/SQL/retrieval e não chamam
LLM. Só o orquestrador do loop (Opus) é LLM; por isso a trava "LLM é o último recurso"
continua intacta. Em produção o loop usa o tool runner do SDK `anthropic` + MCP
(`AnthropicToolRunner`, slice S14); em CI usa o `FakeToolRunner` determinístico, sem rede.
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

from charutei_contracts import Citation
from pydantic import BaseModel, Field

from charutei_orchestrator.providers import llm_cost


def _tokens(text: str) -> int:
    return max(1, len(text.split()))


class ToolResult(BaseModel):
    """Saída de uma ferramenta determinística: texto recuperado + fontes (groundedness)."""

    text: str
    citations: list[Citation] = Field(default_factory=list)


# Handler de uma ferramenta: recebe a consulta do usuário e devolve trechos ancorados.
# Determinístico por construção — NUNCA chama LLM/embedding fora do Orchestrator.
ToolHandler = Callable[[str], Awaitable[ToolResult]]


class AgentTool(BaseModel):
    """Ferramenta exposta ao loop agêntico (read-only, sem LLM).

    `name`/`description` viram a tool definition (MCP no real); `handler` executa a busca.
    """

    model_config = {"arbitrary_types_allowed": True}

    name: str
    description: str
    handler: ToolHandler

    async def call(self, query: str) -> ToolResult:
        return await self.handler(query)


class ToolCallTrace(BaseModel):
    """Uma invocação de ferramenta dentro do loop — vira um TraceRecord filho na cascata."""

    name: str
    cost_usd: float = 0.0  # ferramentas são determinísticas → custo ~0


class AgentRunResult(BaseModel):
    """Resultado do loop agêntico. Espelha `GenerationOutput` para encaixar na cascata."""

    text: str
    model: str
    citations: list[Citation] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    confidence: float = 1.0
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)


@runtime_checkable
class ToolRunner(Protocol):
    async def run(
        self, *, model: str, system: str, prompt: str, tools: list[AgentTool]
    ) -> AgentRunResult: ...


class FakeToolRunner:
    """Loop agêntico determinístico para CI/evals — sem rede, sem chave.

    Simula a trajetória do Opus: invoca cada ferramenta uma vez com a consulta, agrega os
    trechos recuperados e cita todas as fontes. Tokens/custo são reais por modelo (como
    `FakeLLMProvider`), de modo que o FinOps da cascata permanece fiel.
    """

    async def run(
        self, *, model: str, system: str, prompt: str, tools: list[AgentTool]
    ) -> AgentRunResult:
        snippets: list[str] = []
        citations: list[Citation] = []
        tool_calls: list[ToolCallTrace] = []
        for tool in tools:
            res = await tool.call(prompt)
            tool_calls.append(ToolCallTrace(name=tool.name))
            if res.text:
                snippets.append(f"[{tool.name}] {res.text}")
            citations.extend(res.citations)

        body = " ".join(snippets) if snippets else "sem fonte encontrada"
        text = f"[{model} · agentic] {body}".strip()
        input_tokens = _tokens(system) + _tokens(prompt) + sum(_tokens(s) for s in snippets)
        output_tokens = _tokens(text)
        # Loop ancorado em fontes ⇒ confiança alta; sem fontes ⇒ baixa (pode ir a HITL).
        confidence = 1.0 if citations else 0.0
        return AgentRunResult(
            text=text,
            model=model,
            citations=citations,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=llm_cost(model, input_tokens, output_tokens),
            confidence=confidence,
            tool_calls=tool_calls,
        )


class AnthropicToolRunner:
    """Loop agêntico real: Opus orquestra as ferramentas MCP in-process (laço manual).

    Laço manual (não o `tool_runner` automático do SDK) para manter o controle de FinOps —
    soma `usage` de cada iteração e extrai citações de cada `tool_result` (groundedness).
    As ferramentas vêm de um servidor MCP (`build_mcp_server`); a conexão é in-memory, sem
    rede nem subprocess. `anthropic`/`mcp` são lazy-import (extra `providers`).

    O parâmetro `tools` de `run` (compat com o Protocol) é ignorado: a fonte de verdade é o
    servidor MCP — o modelo decide quais chamar a partir das tool definitions do servidor.
    """

    # Mapa IDs internos → IDs do SDK (idêntico a AnthropicLLMProvider).
    _MODEL_IDS: dict[str, str] = {
        "haiku-4.5": "claude-haiku-4-5",
        "sonnet-4.6": "claude-sonnet-4-6",
        "opus-4.8": "claude-opus-4-8",
    }

    def __init__(
        self,
        server: object,
        *,
        api_key: str | None = None,
        max_iterations: int = 6,
        max_tokens: int = 2048,
    ) -> None:
        self._server: Any = server  # FastMCP (lazy; mcp é extra opcional)
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._max_iterations = max_iterations
        self._max_tokens = max_tokens

    async def run(
        self, *, model: str, system: str, prompt: str, tools: list[AgentTool]
    ) -> AgentRunResult:
        import anthropic
        from mcp.shared.memory import create_connected_server_and_client_session

        api_model = self._MODEL_IDS.get(model, model)
        client = anthropic.AsyncAnthropic(api_key=self._api_key)
        in_tokens = 0
        out_tokens = 0
        citations: list[Citation] = []
        tool_calls: list[ToolCallTrace] = []
        final_text = ""

        async with create_connected_server_and_client_session(self._server) as session:
            await session.initialize()
            listed = await session.list_tools()
            tool_params: list[Any] = [
                {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
                for t in listed.tools
            ]
            messages: list[Any] = [{"role": "user", "content": prompt}]

            for _ in range(self._max_iterations):
                resp = await client.messages.create(
                    model=api_model,
                    max_tokens=self._max_tokens,
                    system=system,
                    tools=tool_params,
                    messages=messages,
                    thinking={"type": "adaptive"},
                    output_config={"effort": "high"},
                )
                in_tokens += resp.usage.input_tokens
                out_tokens += resp.usage.output_tokens
                final_text = "".join(b.text for b in resp.content if b.type == "text") or final_text
                if resp.stop_reason != "tool_use":
                    break

                messages.append({"role": "assistant", "content": resp.content})
                results: list[Any] = []
                for block in resp.content:
                    if block.type != "tool_use":
                        continue
                    tool_calls.append(ToolCallTrace(name=block.name))
                    call = await session.call_tool(block.name, arguments=dict(block.input))
                    raw = "".join(getattr(c, "text", "") for c in call.content)
                    try:
                        parsed = ToolResult.model_validate_json(raw)
                    except ValueError:
                        parsed = ToolResult(text=raw)
                    citations.extend(parsed.citations)
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": parsed.text or "sem dados",
                        }
                    )
                messages.append({"role": "user", "content": results})

        # Dedup de citações preservando ordem (várias chamadas podem repetir a fonte).
        seen: set[str] = set()
        deduped: list[Citation] = []
        for c in citations:
            if c.source_id not in seen:
                seen.add(c.source_id)
                deduped.append(c)
        return AgentRunResult(
            text=final_text,
            model=model,
            citations=deduped,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            cost_usd=llm_cost(model, in_tokens, out_tokens),
            confidence=1.0 if deduped else 0.0,
            tool_calls=tool_calls,
        )


def build_tool_runner(use_fake: bool | None = None, *, server: object | None = None) -> ToolRunner:
    """Fábrica do tool runner. Lê USE_FAKE_PROVIDERS quando `use_fake` não é passado.

    `use_fake=False` exige `server` (servidor MCP de `build_mcp_server`) — mesmo padrão de
    `build_providers`: real só quando explicitamente ligado.
    """
    if use_fake is None:
        use_fake = os.environ.get("USE_FAKE_PROVIDERS", "true").lower() in {"1", "true", "yes"}
    if use_fake:
        return FakeToolRunner()
    if server is None:
        raise ValueError("AnthropicToolRunner exige `server` (use build_mcp_server(...)).")
    return AnthropicToolRunner(server)
