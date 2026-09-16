"""Testes de contrato do BFF: auth, reconhecimento, coleção e idempotência."""

import httpx
import pytest
from charutei_api import build_context, create_app, pump_events
from charutei_embedding_worker import CIGAR_TEXT_KIND

_AUTH = {"Authorization": "Bearer alice"}


@pytest.fixture
async def client_ctx():  # type: ignore[no-untyped-def]
    ctx = await build_context()
    app = create_app(ctx)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, ctx


async def test_healthz(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_requires_auth(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    r = await client.post(
        "/bands/recognize", json={"ref": "img-1", "visual_text": "Cohiba Robustos"}
    )
    assert r.status_code == 401


async def test_recognize_returns_cigar(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, ctx = client_ctx
    r = await client.post(
        "/bands/recognize",
        json={"ref": "img-1", "visual_text": "Cohiba Robustos"},
        headers=_AUTH,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["cigar_id"] == "cigar:cohiba-robustos"
    assert body["needs_human"] is False
    # publicou evento anilha.cadastrada via outbox
    assert ctx.outbox._pending  # noqa: SLF001 — inspeção de teste


async def test_ask_requires_auth(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    r = await client.post("/ask", json={"q": "Com o que harmoniza o Cohiba Robustos?"})
    assert r.status_code == 401


async def test_ask_returns_grounded_answer(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    r = await client.post(
        "/ask", json={"q": "Com o que harmoniza o Cohiba Robustos?"}, headers=_AUTH
    )
    assert r.status_code == 200
    body = r.json()
    assert body["answer"]
    assert body["citations"]  # resposta ancorada (KG, degrau determinístico)


async def test_add_to_collection_and_list(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    r = await client.post(
        "/collection/items", json={"cigar_id": "cigar:cohiba-robustos"}, headers=_AUTH
    )
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1

    r = await client.get("/collection", headers=_AUTH)
    body = r.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["created_at"]  # aging (F2.5): item carimbado


async def test_tasting_requires_auth(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    r = await client.post("/tasting", json={"cigar_id": "cigar:cohiba-robustos", "rating": 5})
    assert r.status_code == 401


async def test_tasting_create_and_list(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    r = await client.post(
        "/tasting",
        json={
            "cigar_id": "cigar:cohiba-robustos",
            "rating": 5,
            "flavors": ["Amadeirado", "Café"],
            "occasion": "pós-jantar",
            "note": "excelente",
        },
        headers=_AUTH,
    )
    assert r.status_code == 200
    assert r.json()["created_at"]

    r = await client.get("/tasting?cigar_id=cigar:cohiba-robustos", headers=_AUTH)
    items = r.json()
    assert len(items) == 1
    assert items[0]["rating"] == 5
    assert items[0]["flavors"] == ["Amadeirado", "Café"]


async def test_collection_idempotency(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    headers = {**_AUTH, "Idempotency-Key": "key-123"}
    body = {"cigar_id": "cigar:cohiba-robustos", "quantity": 1}
    first = await client.post("/collection/items", json=body, headers=headers)
    second = await client.post("/collection/items", json=body, headers=headers)
    assert first.status_code == second.status_code == 200
    assert len(second.json()["items"]) == 1  # não duplicou


async def test_pump_events_materializes_catalog_embeddings(client_ctx) -> None:  # type: ignore[no-untyped-def]
    """Fase 1: o pipeline outbox→bus→worker estava desconectado (achado do audit) — a ingestão
    do catálogo no boot já enfileira `sku.detectado`; pump_events publica e materializa os
    embeddings de texto. Sem esse fix, `ctx.vector_repo` nunca teria entradas `cigar_text`."""
    _, ctx = client_ctx
    await pump_events(ctx)
    hits = await ctx.vector_repo.ann_search(CIGAR_TEXT_KIND, [1.0] * 64, k=1)
    assert len(hits) == 1


async def test_pump_events_ignores_unhandled_event_types(client_ctx) -> None:  # type: ignore[no-untyped-def]
    """anilha.cadastrada/colecao.alterada (emitidos pela API) não são tipos que o
    EmbeddingWorker trata — pump_events deve publicá-los e reconhecê-los sem erro (ack, sem
    efeito), nunca travar o loop de fundo por causa de um evento que ninguém consome ainda."""
    client, ctx = client_ctx
    r = await client.post(
        "/collection/items",
        json={"cigar_id": "cigar:cohiba-robustos", "quantity": 1},
        headers=_AUTH,
    )
    assert r.status_code == 200
    await pump_events(ctx)  # não deve levantar exceção
