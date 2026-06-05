"""Integração: outbox + registro de processados duráveis (Postgres).

Pula sem o banco (CHARUTEI_TEST_DATABASE_URL). Valida publicação transacional e idempotência.
"""

import os

import pytest
from charutei_events import Event, EventType, InMemoryEventBus

DB_URL = os.environ.get("CHARUTEI_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DB_URL, reason="defina CHARUTEI_TEST_DATABASE_URL para o teste de integração do outbox"
)


@pytest.fixture
async def conn():  # type: ignore[no-untyped-def]
    psycopg = pytest.importorskip("psycopg")
    from charutei_events.postgres import apply_events_schema

    c = await psycopg.AsyncConnection.connect(DB_URL)
    await apply_events_schema(c)
    await c.execute("TRUNCATE outbox, processed_events")
    await c.commit()
    yield c
    await c.close()


async def test_outbox_publish_and_idempotency(conn) -> None:  # type: ignore[no-untyped-def]
    from charutei_events.postgres import PostgresOutbox, PostgresProcessedRegistry

    outbox = PostgresOutbox(conn)
    bus = InMemoryEventBus()
    evt = Event(event_id="evt-1", type=EventType.SKU_DETECTADO, payload={"cigar_id": "cigar:x"})

    await outbox.add(evt)
    await outbox.add(evt)  # re-emissão → ON CONFLICT DO NOTHING
    assert await outbox.publish_pending(bus) == 1
    assert await outbox.publish_pending(bus) == 0  # já publicado
    assert bus.pending() == 1

    reg = PostgresProcessedRegistry(conn)
    assert not await reg.seen("evt-1")
    await reg.mark("evt-1")
    await reg.mark("evt-1")  # idempotente
    assert await reg.seen("evt-1")
