"""Outbox e registro de processados duráveis (Postgres).

Importado sob demanda (extra `postgres`). O outbox grava o evento na MESMA transação da
escrita OLTP (publicação transacional); um publicador move pendentes para o bus depois.
"""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg.types.json import Json

from charutei_events.interfaces import EventBus
from charutei_events.models import Event, EventType

EVENTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS outbox (
    id           BIGSERIAL PRIMARY KEY,
    event_id     TEXT NOT NULL UNIQUE,
    type         TEXT NOT NULL,
    payload      JSONB NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    published    BOOLEAN NOT NULL DEFAULT FALSE,
    published_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_outbox_unpublished ON outbox (published) WHERE published = FALSE;

CREATE TABLE IF NOT EXISTS processed_events (
    event_id     TEXT PRIMARY KEY,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


async def apply_events_schema(conn: psycopg.AsyncConnection[Any]) -> None:
    await conn.execute(EVENTS_SCHEMA)
    await conn.commit()


class PostgresOutbox:
    def __init__(self, conn: psycopg.AsyncConnection[Any]) -> None:
        self._conn = conn

    async def add(self, event: Event) -> None:
        # ON CONFLICT torna a gravação idempotente (evento pode ser re-emitido).
        await self._conn.execute(
            "INSERT INTO outbox (event_id, type, payload) VALUES (%s, %s, %s::jsonb) "
            "ON CONFLICT (event_id) DO NOTHING",
            (event.event_id, str(event.type), Json(event.payload)),
        )
        await self._conn.commit()

    async def publish_pending(self, bus: EventBus, batch: int = 100) -> int:
        cur = await self._conn.execute(
            "SELECT event_id, type, payload FROM outbox WHERE published = FALSE "
            "ORDER BY id LIMIT %s",
            (batch,),
        )
        rows = await cur.fetchall()
        for event_id, type_, payload in rows:
            await bus.publish(
                Event(event_id=event_id, type=EventType(type_), payload=payload or {})
            )
            await self._conn.execute(
                "UPDATE outbox SET published = TRUE, published_at = now() WHERE event_id = %s",
                (event_id,),
            )
        await self._conn.commit()
        return len(rows)


class PostgresProcessedRegistry:
    def __init__(self, conn: psycopg.AsyncConnection[Any]) -> None:
        self._conn = conn

    async def seen(self, event_id: str) -> bool:
        cur = await self._conn.execute(
            "SELECT 1 FROM processed_events WHERE event_id = %s", (event_id,)
        )
        return await cur.fetchone() is not None

    async def mark(self, event_id: str) -> None:
        await self._conn.execute(
            "INSERT INTO processed_events (event_id) VALUES (%s) ON CONFLICT DO NOTHING",
            (event_id,),
        )
        await self._conn.commit()
