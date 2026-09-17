"""Testes de contrato do BFF: auth, reconhecimento, coleção e idempotência."""

import httpx
import pytest
from charutei_api import build_context, create_app, pump_events
from charutei_embedding_worker import CIGAR_TEXT_KIND
from charutei_location import FakeGeocodingProvider

_AUTH = {"Authorization": "Bearer alice"}

# São Paulo e Santos — mesmas coordenadas de referência de packages/location/tests, ~70km reais.
_SP = {"lat": -23.5505, "lng": -46.6333}
_SANTOS = {"lat": -23.9608, "lng": -46.3339}


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


async def test_create_named_collection_and_list(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    r = await client.post("/collections", json={"name": "Viagem SP"}, headers=_AUTH)
    assert r.status_code == 200
    created = r.json()
    assert created["name"] == "Viagem SP"

    r = await client.get("/collections", headers=_AUTH)
    ids = {c["id"] for c in r.json()}
    assert created["id"] in ids

    # o humidor padrão (/collection, singular) continua isolado da nova collection nomeada
    r = await client.get("/collection", headers=_AUTH)
    assert r.json()["id"] != created["id"]
    assert len(r.json()["items"]) == 0


async def test_add_item_to_specific_collection(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    created = (await client.post("/collections", json={"name": "Viagem SP"}, headers=_AUTH)).json()

    r = await client.post(
        "/collection/items",
        json={"cigar_id": "cigar:cohiba-robustos", "collection_id": created["id"]},
        headers=_AUTH,
    )
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]
    assert len(r.json()["items"]) == 1

    # o humidor padrão não foi afetado
    default = await client.get("/collection", headers=_AUTH)
    assert len(default.json()["items"]) == 0


async def test_add_item_rejects_foreign_collection_id(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    other_user_collection = (
        await client.post(
            "/collections", json={"name": "Bob"}, headers={"Authorization": "Bearer bob"}
        )
    ).json()

    r = await client.post(
        "/collection/items",
        json={"cigar_id": "cigar:cohiba-robustos", "collection_id": other_user_collection["id"]},
        headers=_AUTH,  # alice tentando escrever na collection do bob
    )
    assert r.status_code == 404


async def test_tasting_emits_experience_event(client_ctx) -> None:  # type: ignore[no-untyped-def]
    """POST /tasting não emitia nenhum evento antes da Fase 2 — sem sinal de "experiência
    registrada" para a Fase 6 (Recommendation Engine) consumir depois."""
    client, ctx = client_ctx
    r = await client.post(
        "/tasting",
        json={"cigar_id": "cigar:cohiba-robustos", "rating": 5},
        headers=_AUTH,
    )
    assert r.status_code == 200
    await pump_events(ctx)  # publica + processa (sem handler dedicado ainda) sem erro
    assert ctx.bus.pending() == 0


async def test_profile_aggregates_across_all_collections(client_ctx) -> None:  # type: ignore[no-untyped-def]
    """Fase 3: "km de fumaça" é a bagagem total do usuário — humidor_size soma itens de TODAS as
    collections (humidor padrão + nomeadas, Fase 2), não só uma lista."""
    client, _ = client_ctx
    extra = (await client.post("/collections", json={"name": "Viagem SP"}, headers=_AUTH)).json()

    await client.post(
        "/collection/items", json={"cigar_id": "cigar:cohiba-robustos"}, headers=_AUTH
    )
    await client.post(
        "/collection/items",
        json={"cigar_id": "cigar:davidoff-aniversario-no-3", "collection_id": extra["id"]},
        headers=_AUTH,
    )
    await client.post(
        "/tasting",
        json={
            "cigar_id": "cigar:cohiba-robustos",
            "rating": 5,
            "flavors": ["Amadeirado", "Café"],
            "note": "excelente, notas de madeira",
        },
        headers=_AUTH,
    )

    r = await client.get("/profile", headers=_AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["humidor_size"] == 2  # 1 no humidor padrão + 1 na collection nomeada
    assert body["distinct_countries"] == 2  # Cuba + República Dominicana
    assert body["total_tastings"] == 1
    assert body["avg_rating"] == 5.0
    assert "Amadeirado" in body["top_flavors"]
    assert body["experience_score"] > 0
    assert body["knowledge_score"] > 0  # a nota escrita conta
    assert body["consumer_status"]["name"] in {
        "Novato",
        "Aficionado",
        "Conhecedor",
        "Mestre Charuteiro",
    }
    badge_ids = {b["id"] for b in body["badges"]}
    assert "first" in badge_ids  # primeira degustação registrada → earned


async def test_profile_isolated_between_users(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    await client.post(
        "/collection/items", json={"cigar_id": "cigar:cohiba-robustos"}, headers=_AUTH
    )
    await client.post(
        "/tasting", json={"cigar_id": "cigar:cohiba-robustos", "rating": 5}, headers=_AUTH
    )

    bob = await client.get("/profile", headers={"Authorization": "Bearer bob"})
    assert bob.status_code == 200
    body = bob.json()
    assert body["total_tastings"] == 0
    assert body["humidor_size"] == 0
    assert not any(b["earned"] for b in body["badges"])


async def test_profile_empty_state(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    r = await client.get("/profile", headers=_AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["total_tastings"] == 0
    assert body["avg_rating"] == 0.0
    assert body["consumer_status"]["name"] == "Novato"


async def test_create_establishment_and_report_availability(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    r = await client.post(
        "/establishments",
        json={"name": "Tabacaria Teste", "city": "São Paulo", **_SP},
        headers=_AUTH,
    )
    assert r.status_code == 200
    est = r.json()
    assert est["source"] == "community:user:alice"  # proveniência, nunca oculta

    r = await client.post(
        f"/establishments/{est['id']}/availability",
        json={"cigar_id": "cigar:cohiba-robustos", "available": True},
        headers=_AUTH,
    )
    assert r.status_code == 200
    availability = r.json()
    assert availability["status"] == "community_reported"  # nunca "confirmed" p/ usuário comum


async def test_report_availability_unavailable_status(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    est = (
        await client.post("/establishments", json={"name": "Loja X", **_SP}, headers=_AUTH)
    ).json()
    r = await client.post(
        f"/establishments/{est['id']}/availability",
        json={"cigar_id": "cigar:cohiba-robustos", "available": False},
        headers=_AUTH,
    )
    assert r.json()["status"] == "unavailable"


async def test_report_availability_unknown_establishment_404(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    r = await client.post(
        "/establishments/nao-existe/availability",
        json={"cigar_id": "cigar:cohiba-robustos"},
        headers=_AUTH,
    )
    assert r.status_code == 404


async def test_nearby_filters_by_radius_and_ranks_by_distance(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    near = (
        await client.post("/establishments", json={"name": "Perto", **_SP}, headers=_AUTH)
    ).json()
    far = (
        await client.post("/establishments", json={"name": "Longe", **_SANTOS}, headers=_AUTH)
    ).json()
    for est in (near, far):
        await client.post(
            f"/establishments/{est['id']}/availability",
            json={"cigar_id": "cigar:cohiba-robustos", "available": True},
            headers=_AUTH,
        )

    small = await client.get(
        "/nearby", params={"cigar_id": "cigar:cohiba-robustos", "radius_km": 10, **_SP}
    )
    assert small.status_code == 200
    assert [r["establishment"]["id"] for r in small.json()] == [near["id"]]

    big = await client.get(
        "/nearby", params={"cigar_id": "cigar:cohiba-robustos", "radius_km": 200, **_SP}
    )
    ids = [r["establishment"]["id"] for r in big.json()]
    assert ids == [near["id"], far["id"]]  # mais perto primeiro


async def test_nearby_excludes_unavailable(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    est = (
        await client.post("/establishments", json={"name": "Loja Y", **_SP}, headers=_AUTH)
    ).json()
    await client.post(
        f"/establishments/{est['id']}/availability",
        json={"cigar_id": "cigar:cohiba-robustos", "available": False},
        headers=_AUTH,
    )
    r = await client.get(
        "/nearby", params={"cigar_id": "cigar:cohiba-robustos", "radius_km": 50, **_SP}
    )
    assert r.json() == []  # nunca apresenta como disponível o que é sabidamente indisponível


async def test_nearby_requires_lat_lng_or_address(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    r = await client.get("/nearby", params={"cigar_id": "cigar:cohiba-robustos"})
    assert r.status_code == 400


async def test_nearby_resolves_address_via_geocoding_provider(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    address = "Av. Paulista, São Paulo"
    lat, lng = await FakeGeocodingProvider().geocode(address)  # mesmo provider do ctx (fake)
    est = (
        await client.post(
            "/establishments", json={"name": "Na esquina", "lat": lat, "lng": lng}, headers=_AUTH
        )
    ).json()
    await client.post(
        f"/establishments/{est['id']}/availability",
        json={"cigar_id": "cigar:cohiba-robustos", "available": True},
        headers=_AUTH,
    )

    r = await client.get(
        "/nearby",
        params={"cigar_id": "cigar:cohiba-robustos", "address": address, "radius_km": 1},
    )
    assert r.status_code == 200
    assert [x["establishment"]["id"] for x in r.json()] == [est["id"]]


async def test_recommendations_empty_without_history(client_ctx) -> None:  # type: ignore[no-untyped-def]
    """Fase 6, v1: sem sinal (nenhuma degustação/coleção), sem fallback de popularidade — lista
    vazia é a resposta honesta, não fabricamos "popular agora" sem o dado que sustentaria isso."""
    client, _ = client_ctx
    r = await client.get("/recommendations", headers=_AUTH)
    assert r.status_code == 200
    assert r.json() == []


async def test_recommendations_suggests_same_brand_after_high_rating(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    await client.post(
        "/tasting",
        json={"cigar_id": "cigar:cohiba-robustos", "rating": 5},
        headers=_AUTH,
    )

    r = await client.get("/recommendations", headers=_AUTH)
    assert r.status_code == 200
    results = r.json()
    ids = [c["cigar_id"] for c in results]

    assert "cigar:cohiba-robustos" not in ids  # já avaliado — excluído
    assert "cigar:cohiba-siglo-vi" in ids  # mesma marca (Cohiba) — recomendado
    match = next(c for c in results if c["cigar_id"] == "cigar:cohiba-siglo-vi")
    assert any("Cohiba" in reason for reason in match["reasons"])


async def test_recommendations_low_rating_gives_no_signal(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    await client.post(
        "/tasting",
        json={"cigar_id": "cigar:cohiba-robustos", "rating": 2},  # não gostou
        headers=_AUTH,
    )
    r = await client.get("/recommendations", headers=_AUTH)
    assert r.json() == []  # rating < 4 não vira sinal de afinidade


async def test_recommendations_respects_limit(client_ctx) -> None:  # type: ignore[no-untyped-def]
    client, _ = client_ctx
    await client.post(
        "/collection/items", json={"cigar_id": "cigar:cohiba-robustos"}, headers=_AUTH
    )
    r = await client.get("/recommendations?limit=1", headers=_AUTH)
    assert len(r.json()) <= 1


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
