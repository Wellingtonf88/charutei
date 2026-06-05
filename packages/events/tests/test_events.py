"""Testes do event bus in-memory: publish/poll/ack, retry→DLQ, outbox e idempotência."""

from charutei_events import (
    Event,
    EventType,
    InMemoryEventBus,
    InMemoryOutbox,
    InMemoryProcessedRegistry,
    RetryPolicy,
)


async def test_publish_poll_ack() -> None:
    bus = InMemoryEventBus()
    await bus.publish(Event(type=EventType.IMAGEM_ENVIADA, payload={"ref": "img-1"}))
    deliveries = await bus.poll()
    assert len(deliveries) == 1
    await bus.ack(deliveries[0])
    assert bus.pending() == 0


async def test_nack_retries_then_dead_letters() -> None:
    bus = InMemoryEventBus(RetryPolicy(max_attempts=2))
    await bus.publish(Event(event_id="e1", type=EventType.SKU_DETECTADO))

    d = (await bus.poll())[0]
    await bus.nack(d, error="boom")  # tentativa 1 → reenfileira
    assert bus.pending() == 1
    assert not await bus.dead_letters()

    d = (await bus.poll())[0]
    await bus.nack(d, error="boom")  # tentativa 2 → DLQ
    dlq = await bus.dead_letters()
    assert len(dlq) == 1
    assert dlq[0].event.event_id == "e1"
    assert dlq[0].attempts == 2


async def test_outbox_publishes_pending_then_idempotent() -> None:
    bus = InMemoryEventBus()
    outbox = InMemoryOutbox()
    await outbox.add(Event(type=EventType.ANILHA_CADASTRADA))
    await outbox.add(Event(type=EventType.ANILHA_CADASTRADA))

    assert await outbox.publish_pending(bus) == 2
    assert await outbox.publish_pending(bus) == 0  # nada pendente → idempotente
    assert bus.pending() == 2


async def test_processed_registry_dedupe() -> None:
    reg = InMemoryProcessedRegistry()
    assert not await reg.seen("e1")
    await reg.mark("e1")
    assert await reg.seen("e1")


def test_retry_policy_backoff_grows_and_caps() -> None:
    policy = RetryPolicy(base_delay_seconds=1.0, max_delay_seconds=5.0, jitter_ratio=0.0)
    assert policy.delay_for(1) == 1.0
    assert policy.delay_for(2) == 2.0
    assert policy.delay_for(10) == 5.0  # teto
    assert policy.should_retry(2) is True
    assert policy.should_retry(3) is False
