"""Modelos do event bus.

Eventos do domínio são append-only e **idempotentes** (podem chegar 2×; dedupe por `event_id`).
O `Outbox` garante publicação transacional com a escrita OLTP (escreve evento na mesma transação
do dado; um publicador move para o bus depois).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EventType(StrEnum):
    ANILHA_CADASTRADA = "anilha.cadastrada"
    IMAGEM_ENVIADA = "imagem.enviada"
    SKU_DETECTADO = "sku.detectado"
    COLECAO_ALTERADA = "colecao.alterada"


def _new_id() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(UTC)


class Event(BaseModel):
    event_id: str = Field(default_factory=_new_id)  # chave de idempotência
    type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)


class Delivery(BaseModel):
    """Uma entrega de evento a um consumidor, com contador de tentativas."""

    event: Event
    attempts: int = 0  # nº de tentativas já feitas (cresce a cada nack)


class DeadLetter(BaseModel):
    event: Event
    error: str
    attempts: int
    failed_at: datetime = Field(default_factory=_now)
