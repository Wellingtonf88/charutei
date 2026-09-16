"""Testes da camada de conhecimento (implementação in-memory) + seed real."""

from charutei_knowledge import (
    Band,
    Collection,
    CollectionItem,
    InMemoryKnowledgeGraph,
    InMemoryOltp,
    InMemoryVectorRepository,
    NodeType,
    User,
    node_id,
    seed_knowledge_graph,
)


async def test_seed_loads_real_cigars_and_builds_graph() -> None:
    kg = InMemoryKnowledgeGraph()
    stats = await seed_knowledge_graph(kg)

    # O seed curado tem >= 30 charutos reais e gera nós/arestas.
    assert stats.cigars >= 30
    assert stats.nodes > stats.cigars  # marcas/países/vitolas/forças/pairings também viram nós
    assert stats.edges >= stats.cigars * 3


async def test_harmonizations_resolved_deterministically() -> None:
    kg = InMemoryKnowledgeGraph()
    await seed_knowledge_graph(kg)

    # Pergunta-âncora do assistente: harmonizações de um charuto conhecido — degrau 2, sem LLM.
    cigar = node_id(NodeType.CIGAR, "partagas-serie-d-no-4")
    pairings = await kg.harmonizations(cigar)
    labels = {p.label for p in pairings}

    assert pairings, "deve retornar harmonizações via grafo"
    assert all(p.type == NodeType.PAIRING for p in pairings)
    assert "Rum envelhecido" in labels


async def test_neighbors_filter_by_relation() -> None:
    kg = InMemoryKnowledgeGraph()
    await seed_knowledge_graph(kg)
    cigar = node_id(NodeType.CIGAR, "cohiba-robustos")

    brands = await kg.neighbors(cigar, rel="made_by")
    assert [n.type for n in brands] == [NodeType.BRAND]
    assert brands[0].label == "Cohiba"


async def test_version_bumps_on_write() -> None:
    kg = InMemoryKnowledgeGraph()
    before = await kg.version()
    await seed_knowledge_graph(kg)
    after = await kg.version()
    assert after > before  # versão muda → invalidará o cache semântico (S2)


async def test_vector_ann_returns_nearest_first() -> None:
    vec = InMemoryVectorRepository()
    await vec.upsert("cigar_text", "a", [1.0, 0.0, 0.0])
    await vec.upsert("cigar_text", "b", [0.9, 0.1, 0.0])
    await vec.upsert("cigar_text", "c", [0.0, 1.0, 0.0])

    results = await vec.ann_search("cigar_text", [1.0, 0.0, 0.0], k=2)
    assert [item_id for item_id, _ in results] == ["a", "b"]
    assert results[0][1] >= results[1][1]


async def test_vector_filters_by_metadata() -> None:
    vec = InMemoryVectorRepository()
    await vec.upsert("band_image", "cuba", [1.0, 0.0], {"country": "Cuba"})
    await vec.upsert("band_image", "nica", [1.0, 0.0], {"country": "Nicaragua"})

    results = await vec.ann_search("band_image", [1.0, 0.0], k=5, filters={"country": "Cuba"})
    assert [item_id for item_id, _ in results] == ["cuba"]


async def test_oltp_collection_flow() -> None:
    oltp = InMemoryOltp()
    user = await oltp.create_user(User(id="u1", email="a@b.com"))
    await oltp.create_collection(Collection(id="col1", user_id=user.id))
    await oltp.add_collection_item(
        CollectionItem(id="it1", collection_id="col1", cigar_id="cigar:cohiba-robustos")
    )
    await oltp.save_band(
        Band(
            id="b1",
            user_id=user.id,
            image_ref="s3://img",
            cigar_id="cigar:cohiba-robustos",
            confidence=0.91,
        )
    )

    col = await oltp.get_collection("col1")
    assert col is not None
    assert len(col.items) == 1
    assert col.items[0].cigar_id == "cigar:cohiba-robustos"
    # aging (F2.5): a entrada no humidor é carimbada com created_at
    assert col.items[0].created_at is not None


async def test_oltp_tastings_flow() -> None:
    from charutei_knowledge import TastingNote

    oltp = InMemoryOltp()
    await oltp.create_user(User(id="u1", email="a@b.com"))
    saved = await oltp.add_tasting(
        TastingNote(
            id="t1",
            user_id="u1",
            cigar_id="cigar:cohiba-robustos",
            rating=5,
            flavors=["Amadeirado", "Café"],
            occasion="pós-jantar",
        )
    )
    assert saved.created_at is not None  # carimbado no add
    await oltp.add_tasting(
        TastingNote(id="t2", user_id="u1", cigar_id="cigar:montecristo-no-4", rating=3)
    )
    await oltp.add_tasting(
        TastingNote(id="t3", user_id="u2", cigar_id="cigar:cohiba-robustos", rating=4)
    )

    # isolado por usuário
    assert {t.id for t in await oltp.list_tastings("u1")} == {"t1", "t2"}
    # filtro por charuto
    only = await oltp.list_tastings("u1", cigar_id="cigar:cohiba-robustos")
    assert [t.id for t in only] == ["t1"]
    assert only[0].flavors == ["Amadeirado", "Café"]


async def test_oltp_list_collections() -> None:
    oltp = InMemoryOltp()
    await oltp.create_user(User(id="u1", email="a@b.com"))
    await oltp.create_user(User(id="u2", email="c@d.com"))
    await oltp.create_collection(Collection(id="col:u1", user_id="u1"))  # humidor padrão
    await oltp.create_collection(Collection(id="col-extra", user_id="u1", name="Viagem"))
    await oltp.create_collection(Collection(id="col:u2", user_id="u2"))

    u1_collections = await oltp.list_collections("u1")
    assert {c.id for c in u1_collections} == {"col:u1", "col-extra"}
    assert {c.id for c in await oltp.list_collections("u2")} == {"col:u2"}
    assert await oltp.list_collections("u3") == []


async def test_oltp_idempotency_keys() -> None:
    oltp = InMemoryOltp()
    assert await oltp.idempotency_seen("key-1") is False
    await oltp.idempotency_mark("key-1")
    assert await oltp.idempotency_seen("key-1") is True
    # marcar de novo não é erro (idempotente)
    await oltp.idempotency_mark("key-1")
    assert await oltp.idempotency_seen("key-2") is False
