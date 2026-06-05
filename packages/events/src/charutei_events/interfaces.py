"""Interfaces do event bus (in-memory hoje → pgmq/Redis Streams/Kafka na escala)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from charutei_events.models import DeadLetter, Delivery, Event


@runtime_checkable
class EventBus(Protocol):
    """Fila com semântica de consumidor: poll → ack (sucesso) / nack (falha→retry/DLQ)."""

    async def publish(self, event: Event) -> None: ...

    async def poll(self, max_messages: int = 10) -> list[Delivery]: ...

    async def ack(self, delivery: Delivery) -> None: ...

    async def nack(self, delivery: Delivery, *, error: str) -> None: ...

    async def dead_letters(self) -> list[DeadLetter]: ...


@runtime_checkable
class Outbox(Protocol):
    """Outbox transacional: grava o evento junto com a escrita OLTP; publica depois."""

    async def add(self, event: Event) -> None: ...

    async def publish_pending(self, bus: EventBus, batch: int = 100) -> int:
        """Move pendentes para o bus, marca como publicados. Idempotente. Retorna nº publicado."""
        ...


@runtime_checkable
class ProcessedRegistry(Protocol):
    """Dedupe por `event_id` — garante efeito exactly-effectively-once nos workers."""

    async def seen(self, event_id: str) -> bool: ...

    async def mark(self, event_id: str) -> None: ...
