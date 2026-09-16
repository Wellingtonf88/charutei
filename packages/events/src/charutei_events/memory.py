"""Implementações in-memory do event bus, outbox e registro de processados.

Para testes/CI e dev local. Mesmas interfaces que as versões duráveis (pgmq/Redis/Postgres),
então o worker não muda ao trocar a infra.
"""

from __future__ import annotations

from collections import deque

from charutei_events.interfaces import EventBus
from charutei_events.models import DeadLetter, Delivery, Event
from charutei_events.retry import RetryPolicy


class InMemoryEventBus:
    """Fila FIFO com retry e DLQ. `nack` reenfileira até o teto da RetryPolicy."""

    def __init__(self, policy: RetryPolicy | None = None) -> None:
        self._ready: deque[Delivery] = deque()
        self._dlq: list[DeadLetter] = []
        self._policy = policy or RetryPolicy()

    async def publish(self, event: Event) -> None:
        self._ready.append(Delivery(event=event, attempts=0))

    async def poll(self, max_messages: int = 10) -> list[Delivery]:
        out: list[Delivery] = []
        while self._ready and len(out) < max_messages:
            out.append(self._ready.popleft())
        return out

    async def ack(self, delivery: Delivery) -> None:
        # Sucesso: nada a fazer (já saiu da fila no poll).
        return None

    async def nack(self, delivery: Delivery, *, error: str) -> None:
        attempts = delivery.attempts + 1
        if self._policy.should_retry(attempts):
            self._ready.append(Delivery(event=delivery.event, attempts=attempts))
        else:
            self._dlq.append(DeadLetter(event=delivery.event, error=error, attempts=attempts))

    async def dead_letters(self) -> list[DeadLetter]:
        return list(self._dlq)

    def pending(self) -> int:
        return len(self._ready)


class InMemoryOutbox:
    """Outbox em memória. `add` simula a escrita transacional com o OLTP."""

    def __init__(self) -> None:
        self._pending: list[Event] = []

    async def add(self, event: Event) -> None:
        self._pending.append(event)

    async def publish_pending(self, bus: EventBus, batch: int = 100) -> int:
        to_publish = self._pending[:batch]
        for event in to_publish:
            await bus.publish(event)
        self._pending = self._pending[len(to_publish) :]
        return len(to_publish)


class InMemoryProcessedRegistry:
    def __init__(self) -> None:
        self._seen: set[str] = set()

    async def seen(self, event_id: str) -> bool:
        return event_id in self._seen

    async def mark(self, event_id: str) -> None:
        self._seen.add(event_id)
