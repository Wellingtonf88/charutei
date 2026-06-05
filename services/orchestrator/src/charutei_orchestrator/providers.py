"""Provedores de modelo atrás de interface + implementações Fake.

REGRA DE OURO: nenhum serviço fala com SDK de LLM/embedding diretamente. Tudo passa por
estes Protocols, e a cascata é a única a invocá-los. `USE_FAKE_PROVIDERS=true` (padrão)
usa os Fakes — determinísticos, custo/tokens contabilizados, zero chave, zero rede.
"""

from __future__ import annotations

import hashlib
import math
import os
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

# Preços de lista jun/2026, em USD por token (input, output). Revalidar antes de orçar.
LLM_PRICING: dict[str, tuple[float, float]] = {
    "haiku-4.5": (1.0 / 1_000_000, 5.0 / 1_000_000),
    "sonnet-4.6": (3.0 / 1_000_000, 15.0 / 1_000_000),
    "opus-4.8": (5.0 / 1_000_000, 25.0 / 1_000_000),
}
EMBED_PRICING: dict[str, float] = {  # input-only
    "voyage-4-lite": 0.02 / 1_000_000,
}
EMBED_DIM = 64


def llm_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pin, pout = LLM_PRICING[model]
    return input_tokens * pin + output_tokens * pout


class LLMResponse(BaseModel):
    text: str
    model: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cost_usd: float = Field(ge=0.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


@runtime_checkable
class LLMProvider(Protocol):
    async def generate(
        self, *, model: str, system: str, prompt: str, max_tokens: int = 512
    ) -> LLMResponse: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    async def embed(
        self, texts: list[str], *, model: str = "voyage-4-lite"
    ) -> list[list[float]]: ...


class TraceRecord(BaseModel):
    """Uma etapa observada da cascata — alimenta o Langfuse (e os evals de eficiência)."""

    name: str
    tier: int
    model: str | None = None
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    extra: dict[str, str] = Field(default_factory=dict)


@runtime_checkable
class Tracer(Protocol):
    async def log(self, record: TraceRecord) -> None: ...


# --------------------------------------------------------------------------- Fakes


def _tokens(text: str) -> int:
    return max(1, len(text.split()))


class FakeLLMProvider:
    """LLM determinístico: resposta derivada do prompt, tokens/custo reais por modelo."""

    async def generate(
        self, *, model: str, system: str, prompt: str, max_tokens: int = 512
    ) -> LLMResponse:
        text = f"[{model}] resposta para: {prompt.strip()[:120]}"
        input_tokens = _tokens(system) + _tokens(prompt)
        output_tokens = min(_tokens(text), max_tokens)
        return LLMResponse(
            text=text,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=llm_cost(model, input_tokens, output_tokens),
        )


class FakeEmbeddingProvider:
    """Embedding por 'hashing trick' (bag-of-words em EMBED_DIM, normalizado).

    Determinístico e *semântico o bastante* para testes: consultas com palavras em comum
    ficam próximas no cosseno — suficiente para exercitar o cache semântico.
    """

    async def embed(self, texts: list[str], *, model: str = "voyage-4-lite") -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    @staticmethod
    def _embed_one(text: str) -> list[float]:
        vec = [0.0] * EMBED_DIM
        for token in text.lower().split():
            h = int(hashlib.sha256(token.encode()).hexdigest(), 16) % EMBED_DIM
            vec[h] += 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        return [x / norm for x in vec] if norm else vec


class FakeTracer:
    """Tracer em memória — inspecionável nos testes; substituível por Langfuse real."""

    def __init__(self) -> None:
        self.records: list[TraceRecord] = []

    async def log(self, record: TraceRecord) -> None:
        self.records.append(record)


def build_providers(
    use_fake: bool | None = None,
) -> tuple[LLMProvider, EmbeddingProvider, Tracer]:
    """Fábrica única. Lê USE_FAKE_PROVIDERS quando `use_fake` não é passado.

    Os provedores reais (Anthropic/Voyage/Langfuse) são ligados por slice; aqui falham com
    mensagem clara se solicitados sem implementação, em vez de silenciosamente.
    """
    if use_fake is None:
        use_fake = os.environ.get("USE_FAKE_PROVIDERS", "true").lower() in {"1", "true", "yes"}
    if use_fake:
        return FakeLLMProvider(), FakeEmbeddingProvider(), FakeTracer()
    raise NotImplementedError(
        "Provedores reais (Anthropic/Voyage/Langfuse) ainda não ligados. "
        "Mantenha USE_FAKE_PROVIDERS=true ou implemente o adaptador real na slice correspondente."
    )
