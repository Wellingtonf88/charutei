"""Provedores de modelo atrás de interface + implementações Fake.

REGRA DE OURO: nenhum serviço fala com SDK de LLM/embedding diretamente. Tudo passa por
estes Protocols, e a cascata é a única a invocá-los. `USE_FAKE_PROVIDERS=true` (padrão)
usa os Fakes — determinísticos, custo/tokens contabilizados, zero chave, zero rede.
"""

from __future__ import annotations

import hashlib
import math
import os
from typing import Any, Protocol, runtime_checkable

from charutei_contracts import BandCandidate, BandImage
from pydantic import BaseModel, Field

# Preços de lista jun/2026, em USD por token (input, output). Revalidar antes de orçar.
LLM_PRICING: dict[str, tuple[float, float]] = {
    "haiku-4.5": (1.0 / 1_000_000, 5.0 / 1_000_000),
    "sonnet-4.6": (3.0 / 1_000_000, 15.0 / 1_000_000),
    "opus-4.8": (5.0 / 1_000_000, 25.0 / 1_000_000),
}
EMBED_PRICING: dict[str, float] = {  # input-only
    "voyage-4-lite": 0.02 / 1_000_000,
    "voyage-multimodal-4": 0.12 / 1_000_000,
}
EMBED_DIM = 64

# Visão barata (Gemini Flash) como fallback do reconhecimento de anilha. Opus de visão fica
# fora do MVP (só por necessidade comprovada). Custo modelado por "tokens de imagem".
VISION_PRICING: dict[str, float] = {  # USD por token de input
    "gemini-3-flash": 0.30 / 1_000_000,
}
IMAGE_TOKENS = 1024  # estimativa de tokens equivalentes de uma anilha


def vision_cost(model: str, image_tokens: int = IMAGE_TOKENS) -> float:
    return image_tokens * VISION_PRICING[model]


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
    """Uma etapa observada da cascata — alimenta o Langfuse (e os evals de eficiência).

    `trace_id` agrupa os passos de uma mesma requisição numa única trace no Langfuse;
    `capability` nomeia a feature (para FinOps por agente/feature)."""

    name: str
    tier: int
    model: str | None = None
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    trace_id: str = ""
    capability: str = ""
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


# ----------------------------------------------------- Visão / anilha (S3)


@runtime_checkable
class ImageEmbeddingProvider(Protocol):
    async def embed_image(
        self, image: BandImage, *, model: str = "voyage-multimodal-4"
    ) -> list[float]: ...


@runtime_checkable
class OCRProvider(Protocol):
    async def extract_text(self, image: BandImage) -> str: ...


class VisionResult(BaseModel):
    cigar_id: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    model: str
    cost_usd: float = Field(ge=0.0)


@runtime_checkable
class VisionProvider(Protocol):
    async def identify(
        self, image: BandImage, candidates: list[BandCandidate], *, model: str = "gemini-3-flash"
    ) -> VisionResult: ...


def _bow_embedding(text: str) -> list[float]:
    """Embedding determinístico por bag-of-words (compartilhado pelos fakes de texto/imagem)."""
    vec = [0.0] * EMBED_DIM
    for token in text.lower().split():
        h = int(hashlib.sha256(token.encode()).hexdigest(), 16) % EMBED_DIM
        vec[h] += 1.0
    norm = math.sqrt(sum(x * x for x in vec))
    return [x / norm for x in vec] if norm else vec


class FakeImageEmbeddingProvider:
    """Embeda o `visual_text` da anilha (fixtures). Mesmo espaço dos embeddings de catálogo."""

    async def embed_image(
        self, image: BandImage, *, model: str = "voyage-multimodal-4"
    ) -> list[float]:
        return _bow_embedding(image.visual_text or image.ref)


class FakeOCRProvider:
    """OCR fake: devolve o `ocr_text` da fixture (vazio quando ilegível)."""

    async def extract_text(self, image: BandImage) -> str:
        return image.ocr_text or ""


class FakeVisionProvider:
    """Visão fake: escolhe o candidato com maior sobreposição de tokens com a anilha.

    Determinístico e sem rede. Substituído pelo adaptador Gemini Flash real na produção.
    """

    async def identify(
        self, image: BandImage, candidates: list[BandCandidate], *, model: str = "gemini-3-flash"
    ) -> VisionResult:
        tokens = set((image.visual_text or "").lower().split())
        best: BandCandidate | None = None
        best_overlap = 0.0
        for cand in candidates:
            label_tokens = set((cand.label or cand.cigar_id).lower().split())
            if not label_tokens:
                continue
            overlap = len(tokens & label_tokens) / len(label_tokens)
            if overlap > best_overlap:
                best, best_overlap = cand, overlap
        return VisionResult(
            cigar_id=best.cigar_id if best else None,
            confidence=best_overlap,
            model=model,
            cost_usd=vision_cost(model),
        )


# --------------------------------------------------- Real providers


class AnthropicLLMProvider:
    """Adaptador real Anthropic — anthropic.AsyncAnthropic (lazy import)."""

    # Mapa entre IDs internos da cascata e IDs do SDK Anthropic.
    _MODEL_IDS: dict[str, str] = {
        "haiku-4.5": "claude-haiku-4-5",
        "sonnet-4.6": "claude-sonnet-4-6",
        "opus-4.8": "claude-opus-4-8",
    }

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    async def generate(
        self, *, model: str, system: str, prompt: str, max_tokens: int = 512
    ) -> LLMResponse:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self._api_key)
        api_model = self._MODEL_IDS.get(model, model)
        msg = await client.messages.create(
            model=api_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in msg.content if b.type == "text")
        in_tok = msg.usage.input_tokens
        out_tok = msg.usage.output_tokens
        return LLMResponse(
            text=text,
            model=model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            cost_usd=llm_cost(model, in_tok, out_tok),
        )


class VoyageEmbeddingProvider:
    """Adaptador real Voyage — texto, voyage-4-lite (lazy import voyageai)."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("VOYAGE_API_KEY")

    async def embed(self, texts: list[str], *, model: str = "voyage-4-lite") -> list[list[float]]:
        import voyageai

        client = voyageai.AsyncClient(api_key=self._api_key)
        result = await client.embed(texts, model=model)
        # Coerção explícita p/ list[list[float]] (a API pode tipar como float|int).
        return [[float(x) for x in vec] for vec in result.embeddings]


class VoyageImageEmbeddingProvider:
    """Adaptador real Voyage multimodal — voyage-multimodal-4 (lazy import voyageai)."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("VOYAGE_API_KEY")

    async def embed_image(
        self, image: BandImage, *, model: str = "voyage-multimodal-4"
    ) -> list[float]:
        import voyageai

        client = voyageai.AsyncClient(api_key=self._api_key)
        if image.data_b64:
            content = [{"type": "image_base64", "image_base64": image.data_b64}]
        elif image.url:
            content = [{"type": "image_url", "image_url": image.url}]
        else:
            content = [{"type": "text", "text": image.visual_text or image.ref}]
        result = await client.multimodal_embed([content], model=model)
        return [float(x) for x in result.embeddings[0]]


class GeminiVisionProvider:
    """Adaptador real Gemini Flash — identificação de anilha via visão (lazy google.genai)."""

    # Mapa entre ID interno e ID do modelo na API Google.
    _MODEL_IDS: dict[str, str] = {
        "gemini-3-flash": "gemini-2.0-flash",
    }

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY")

    async def identify(
        self, image: BandImage, candidates: list[BandCandidate], *, model: str = "gemini-3-flash"
    ) -> VisionResult:
        from google import genai

        client = genai.Client(api_key=self._api_key)
        api_model = self._MODEL_IDS.get(model, model)
        cand_lines = "\n".join(
            f"- {c.cigar_id}: {c.label or c.cigar_id}" for c in candidates
        )
        prompt_text = (
            "Você é um especialista em charutos. Analise a imagem desta anilha e identifique "
            "qual charuto da lista abaixo é o mais provável. Responda APENAS com o cigar_id "
            f"exato, sem explicação.\n\nCandidatos:\n{cand_lines}"
            "\n\nResponda apenas com o cigar_id do candidato mais provável."
        )
        parts: list[dict[str, Any]] = [{"text": prompt_text}]
        if image.data_b64:
            parts.append(
                {"inline_data": {"mime_type": "image/jpeg", "data": image.data_b64}}
            )
        response = await client.aio.models.generate_content(
            model=api_model,
            contents=[{"role": "user", "parts": parts}],
        )
        raw = (response.text or "").strip()
        matched = next((c for c in candidates if c.cigar_id == raw), None)
        return VisionResult(
            cigar_id=matched.cigar_id if matched else None,
            confidence=0.8 if matched else 0.0,
            model=model,
            cost_usd=vision_cost(model),
        )


def build_providers(
    use_fake: bool | None = None,
) -> tuple[LLMProvider, EmbeddingProvider, Tracer]:
    """Fábrica única. Lê USE_FAKE_PROVIDERS quando `use_fake` não é passado."""
    if use_fake is None:
        use_fake = os.environ.get("USE_FAKE_PROVIDERS", "true").lower() in {"1", "true", "yes"}
    if use_fake:
        return FakeLLMProvider(), FakeEmbeddingProvider(), FakeTracer()
    return AnthropicLLMProvider(), VoyageEmbeddingProvider(), build_tracer()


def build_tracer() -> Tracer:
    """Tracer real (Langfuse) quando há chaves no ambiente; caso contrário, FakeTracer.

    Independe de USE_FAKE_PROVIDERS: dá para tracear runs com providers fake para o Langfuse
    real — útil para validar a observabilidade sem custo de LLM.
    """
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    host = os.environ.get("LANGFUSE_HOST", "http://localhost:3000")
    if public_key and secret_key:
        from charutei_orchestrator.langfuse_tracer import LangfuseTracer

        return LangfuseTracer(public_key=public_key, secret_key=secret_key, host=host)
    return FakeTracer()


def build_band_providers(
    use_fake: bool | None = None,
) -> tuple[ImageEmbeddingProvider, OCRProvider, VisionProvider]:
    """Fábrica dos provedores de visão do Band Recognition (Voyage multimodal / OCR / Gemini)."""
    if use_fake is None:
        use_fake = os.environ.get("USE_FAKE_PROVIDERS", "true").lower() in {"1", "true", "yes"}
    if use_fake:
        return FakeImageEmbeddingProvider(), FakeOCRProvider(), FakeVisionProvider()
    return VoyageImageEmbeddingProvider(), FakeOCRProvider(), GeminiVisionProvider()
