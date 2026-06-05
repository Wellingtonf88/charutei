"""Adaptador Langfuse do `Tracer` — observabilidade de IA real, atrás da interface.

Mapeia cada `TraceRecord` (passo da cascata) para uma observação Langfuse, agrupada por
`trace_id` (requisição). Generations (com modelo) carregam tokens/custo; passos sem modelo
(cache/KG) viram spans. Tier vai em metadata/tags → alimenta os dashboards (FinOps, Cascata,
Operacional). Import do SDK é lazy (extra `providers`), para não acoplar quem usa o FakeTracer.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from charutei_contracts import Tier

from charutei_orchestrator.providers import TraceRecord


class LangfuseTracer:
    """Implementa `Tracer.log` enviando para um Langfuse (self-host ou cloud)."""

    def __init__(
        self,
        *,
        public_key: str = "",
        secret_key: str = "",
        host: str = "",
        client: Any = None,
    ) -> None:
        if client is not None:
            self._lf = client  # injeção para testes (sem SDK/rede)
        else:
            from langfuse import Langfuse  # lazy: requer o extra `providers`

            self._lf = Langfuse(public_key=public_key, secret_key=secret_key, host=host)
        self._traces: dict[str, Any] = {}

    def _trace_for(self, record: TraceRecord) -> Any:
        tid = record.trace_id or uuid.uuid4().hex
        trace = self._traces.get(tid)
        if trace is None:
            trace = self._lf.trace(
                id=tid,
                name=record.capability or "cascade",
                tags=[f"capability:{record.capability}"] if record.capability else None,
                metadata={"capability": record.capability},
            )
            self._traces[tid] = trace
        return trace

    async def log(self, record: TraceRecord) -> None:
        trace = self._trace_for(record)
        tier_name = Tier(record.tier).name
        metadata = {
            "tier": tier_name,
            "tier_num": record.tier,
            "cost_usd": record.cost_usd,
            "latency_ms": record.latency_ms,
            **record.extra,
        }
        # Janela temporal a partir da latência medida → popula a latência nos dashboards.
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(milliseconds=record.latency_ms)
        if record.model:
            trace.generation(
                name=record.name,
                model=record.model,
                start_time=start_time,
                end_time=end_time,
                usage={
                    "input": record.input_tokens,
                    "output": record.output_tokens,
                    "total": record.input_tokens + record.output_tokens,
                    "unit": "TOKENS",
                    "total_cost": record.cost_usd,
                },
                metadata=metadata,
            )
        else:
            trace.span(
                name=record.name, start_time=start_time, end_time=end_time, metadata=metadata
            )

    def score(self, *, trace_id: str, name: str, value: float, comment: str | None = None) -> None:
        """Score de qualidade (ex.: groundedness) ligado a uma trace — dashboard de Qualidade."""
        self._lf.score(trace_id=trace_id, name=name, value=value, comment=comment)

    def flush(self) -> None:
        """Força o envio do buffer (o SDK envia em lote). Chamar ao fim de um job/teste."""
        self._lf.flush()
