"""BFF/Gateway FastAPI do CHARUTEI.

Fluxo do app mobile: autentica → captura/upload de anilha → reconhecimento → adiciona à coleção.
Escritas publicam eventos via outbox (consumidos pelo Embedding Worker e demais agentes).

O contexto (repos/agentes) é injetado. Em teste, passa-se um `AppContext` pronto; em produção
(`main.py`), `create_app()` sem contexto o monta no **lifespan** — necessário para recursos
ligados ao event loop do servidor (ex.: conexão Postgres), fechados no shutdown.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import uuid
from collections import Counter
from contextlib import asynccontextmanager

from charutei_contracts import BandImage, BandRecognitionResult, CascadeResult
from charutei_events import EventType
from charutei_events.models import Event
from charutei_knowledge import (
    AvailabilityStatus,
    Band,
    Collection,
    CollectionItem,
    Establishment,
    NodeType,
    ProductAvailability,
    TastingNote,
    User,
)
from charutei_location import NearbyResult, find_nearby
from charutei_orchestrator import RequestKind
from charutei_scoring import (
    compute_badges,
    compute_consumer_status,
    compute_experience_score,
    compute_knowledge_score,
    compute_streak,
)
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint

from charutei_api.auth import AuthUser
from charutei_api.context import AppContext, build_context, pump_events
from charutei_api.schemas import (
    AddItemRequest,
    AskRequest,
    CatalogEntry,
    CreateCollectionRequest,
    CreateEstablishmentRequest,
    ProfileOut,
    RecognizeRequest,
    ReportAvailabilityRequest,
    TastingRequest,
)
from charutei_api.security import SlidingWindowRateLimiter, cors_origins, rate_limit_config

# Intervalo do loop de fundo que publica o outbox e materializa embeddings (pump_events).
# Só o BFF é implantado hoje (sem worker separado) — ver PROJECT_UPGRADE_AUDIT.md.
_EVENT_PUMP_INTERVAL_S = float(os.environ.get("CHARUTEI_EVENT_PUMP_INTERVAL_S", "5"))


async def _event_pump_loop(ctx: AppContext, interval_s: float) -> None:
    while True:
        # Falha não derruba o servidor — a próxima iteração tenta de novo.
        with contextlib.suppress(Exception):
            await pump_events(ctx)
        await asyncio.sleep(interval_s)


def create_app(ctx: AppContext | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
        # Monta o contexto no boot do servidor quando não injetado (produção/main.py) — assim a
        # conexão Postgres nasce no loop do uvicorn. Fecha no shutdown.
        owns = app.state.ctx is None
        if owns:
            app.state.ctx = await build_context()
        # Loop de fundo: publica o outbox pendente e materializa embeddings (pump_events).
        # Não roda sob ASGITransport (testes não executam lifespan) — mesmo padrão do `owns` acima.
        pump_task = asyncio.create_task(_event_pump_loop(app.state.ctx, _EVENT_PUMP_INTERVAL_S))
        try:
            yield
        finally:
            pump_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await pump_task
            if owns:
                await app.state.ctx.aclose()

    app = FastAPI(title="CHARUTEI BFF", version="0.0.0", lifespan=lifespan)
    app.state.ctx = ctx  # síncrono: testes passam contexto pronto (ASGITransport não roda lifespan)

    # Rate limiting (janela deslizante por cliente) — 1ª camada anti-abuso; /healthz isento.
    limiter = SlidingWindowRateLimiter(*rate_limit_config())

    @app.middleware("http")
    async def rate_limit(request: Request, call_next: RequestResponseEndpoint):  # type: ignore[no-untyped-def]
        if limiter.enabled and request.url.path != "/healthz":
            # Chave por token (se autenticado) ou IP do cliente.
            auth = request.headers.get("authorization", "")
            key = auth or (request.client.host if request.client else "anon")
            if not limiter.allow(key):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "rate limit excedido"},
                    headers={"Retry-After": str(limiter.retry_after(key))},
                )
        return await call_next(request)

    # CORS: origens explícitas por env (nunca `*`) — ver security.cors_origins().
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_ctx(request: Request) -> AppContext:
        ctx = request.app.state.ctx
        assert isinstance(ctx, AppContext)  # garantido pelo lifespan/injeção
        return ctx

    async def current_user(
        authorization: str = Header(default=""), ctx: AppContext = Depends(get_ctx)
    ) -> AuthUser:
        token = authorization.removeprefix("Bearer ").strip()
        user = await ctx.auth.verify(token)
        if user is None:
            raise HTTPException(status_code=401, detail="token inválido ou ausente")
        if await ctx.oltp.get_user(user.id) is None:
            await ctx.oltp.create_user(User(id=user.id, email=user.email))
        return user

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/catalog")
    async def catalog(ctx: AppContext = Depends(get_ctx)) -> list[CatalogEntry]:
        cigars = await ctx.kg.nodes_by_type(NodeType.CIGAR)
        entries: list[CatalogEntry] = []
        for c in cigars:
            brand_nodes = await ctx.kg.neighbors(c.id, rel="made_by")
            country_nodes = await ctx.kg.neighbors(c.id, rel="from_country")
            strength_nodes = await ctx.kg.neighbors(c.id, rel="has_strength")
            pairing_nodes = await ctx.kg.harmonizations(c.id)
            entries.append(
                CatalogEntry(
                    id=c.id,
                    label=c.label,
                    strength=strength_nodes[0].label if strength_nodes else None,
                    brand=brand_nodes[0].label if brand_nodes else None,
                    country=country_nodes[0].label if country_nodes else None,
                    pairings=[p.label for p in pairing_nodes],
                )
            )
        return entries

    @app.post("/bands/recognize")
    async def recognize(
        req: RecognizeRequest,
        user: AuthUser = Depends(current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> BandRecognitionResult:
        result: BandRecognitionResult = await ctx.supervisor.dispatch(
            RequestKind.BAND_IMAGE,
            BandImage(
                ref=req.ref,
                visual_text=req.visual_text,
                ocr_text=req.ocr_text,
                data_b64=req.data_b64,
            ),
        )
        await ctx.oltp.save_band(
            Band(
                id=uuid.uuid4().hex,
                user_id=user.id,
                image_ref=req.ref,
                cigar_id=result.cigar_id,
                confidence=result.confidence,
                needs_human=result.needs_human,
            )
        )
        await ctx.outbox.add(
            Event(
                type=EventType.ANILHA_CADASTRADA,
                payload={"user_id": user.id, "ref": req.ref, "cigar_id": result.cigar_id or ""},
            )
        )
        return result

    @app.post("/ask")
    async def ask(
        req: AskRequest,
        user: AuthUser = Depends(current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> CascadeResult:
        result: CascadeResult = await ctx.supervisor.dispatch(RequestKind.ASSISTANT_TEXT, req.q)
        return result

    @app.post("/tasting")
    async def add_tasting(
        req: TastingRequest,
        user: AuthUser = Depends(current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> TastingNote:
        saved = await ctx.oltp.add_tasting(
            TastingNote(
                id=uuid.uuid4().hex,
                user_id=user.id,
                cigar_id=req.cigar_id,
                rating=req.rating,
                flavors=req.flavors,
                occasion=req.occasion,
                note=req.note,
            )
        )
        await ctx.outbox.add(
            Event(
                type=EventType.DEGUSTACAO_REGISTRADA,
                payload={"user_id": user.id, "cigar_id": req.cigar_id, "tasting_id": saved.id},
            )
        )
        return saved

    @app.get("/tasting")
    async def list_tastings(
        user: AuthUser = Depends(current_user),
        ctx: AppContext = Depends(get_ctx),
        cigar_id: str | None = None,
    ) -> list[TastingNote]:
        return await ctx.oltp.list_tastings(user.id, cigar_id)

    @app.get("/profile")
    async def profile(
        user: AuthUser = Depends(current_user), ctx: AppContext = Depends(get_ctx)
    ) -> ProfileOut:
        tastings = await ctx.oltp.list_tastings(user.id)
        collections = await ctx.oltp.list_collections(user.id)
        # "km de fumaça" é a bagagem total do usuário — soma itens de TODAS as collections dele
        # (Fase 2), não só o humidor padrão.
        items = [item for col in collections for item in col.items]

        total_tastings = len(tastings)
        tastings_with_notes = sum(1 for t in tastings if t.note.strip())
        avg_rating = sum(t.rating for t in tastings) / total_tastings if total_tastings else 0.0
        flavor_counts = Counter(f for t in tastings for f in t.flavors)
        top_flavors = [f for f, _ in flavor_counts.most_common(6)]
        streak_days = compute_streak([t.created_at.date() for t in tastings if t.created_at])

        distinct_cigar_ids = {item.cigar_id for item in items}
        countries: set[str] = set()
        brands: set[str] = set()
        for cigar_id in distinct_cigar_ids:
            country_nodes = await ctx.kg.neighbors(cigar_id, rel="from_country")
            brand_nodes = await ctx.kg.neighbors(cigar_id, rel="made_by")
            countries.update(n.label for n in country_nodes)
            brands.update(n.label for n in brand_nodes)

        experience_score = compute_experience_score(
            humidor_size=len(items),
            total_tastings=total_tastings,
            distinct_countries=len(countries),
            distinct_brands=len(brands),
            streak_days=streak_days,
        )
        knowledge_score = compute_knowledge_score(
            tastings_with_notes=tastings_with_notes,
            distinct_flavors=len(flavor_counts),
        )
        consumer_status = compute_consumer_status(
            experience_score=experience_score, knowledge_score=knowledge_score
        )
        badges = compute_badges(
            total_tastings=total_tastings,
            humidor_size=len(items),
            distinct_countries=len(countries),
            distinct_flavors=len(flavor_counts),
            streak_days=streak_days,
        )

        return ProfileOut(
            total_tastings=total_tastings,
            humidor_size=len(items),
            avg_rating=avg_rating,
            top_flavors=top_flavors,
            distinct_flavors=len(flavor_counts),
            distinct_countries=len(countries),
            streak_days=streak_days,
            experience_score=experience_score,
            knowledge_score=knowledge_score,
            consumer_status=consumer_status,
            badges=badges,
        )

    @app.post("/collections")
    async def create_collection(
        req: CreateCollectionRequest,
        user: AuthUser = Depends(current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> Collection:
        collection = await ctx.oltp.create_collection(
            Collection(id=uuid.uuid4().hex, user_id=user.id, name=req.name)
        )
        await ctx.outbox.add(
            Event(
                type=EventType.COLECAO_CRIADA,
                payload={"user_id": user.id, "collection_id": collection.id, "name": req.name},
            )
        )
        return collection

    @app.get("/collections")
    async def list_collections(
        user: AuthUser = Depends(current_user), ctx: AppContext = Depends(get_ctx)
    ) -> list[Collection]:
        return await ctx.oltp.list_collections(user.id)

    @app.post("/collection/items")
    async def add_item(
        req: AddItemRequest,
        user: AuthUser = Depends(current_user),
        ctx: AppContext = Depends(get_ctx),
        idempotency_key: str | None = Header(default=None),
    ) -> Collection:
        if req.collection_id is not None:
            # Escrita numa collection específica: precisa existir e pertencer ao usuário
            # autenticado. 404 tanto se não existe quanto se é de outro usuário — não confirma
            # a existência de dados alheios para quem não é dono.
            target = await ctx.oltp.get_collection(req.collection_id)
            if target is None or target.user_id != user.id:
                raise HTTPException(status_code=404, detail="coleção não encontrada")
            col_id = req.collection_id
        else:
            col_id = f"col:{user.id}"
            if await ctx.oltp.get_collection(col_id) is None:
                await ctx.oltp.create_collection(Collection(id=col_id, user_id=user.id))

        # Idempotência: a mesma Idempotency-Key não adiciona o item duas vezes. Durável
        # (Postgres) e multi-réplica — não usa mais um `set` em memória do processo.
        already_seen = idempotency_key is not None and await ctx.oltp.idempotency_seen(
            idempotency_key
        )
        if not already_seen:
            await ctx.oltp.add_collection_item(
                CollectionItem(
                    id=uuid.uuid4().hex,
                    collection_id=col_id,
                    cigar_id=req.cigar_id,
                    quantity=req.quantity,
                )
            )
            if idempotency_key is not None:
                await ctx.oltp.idempotency_mark(idempotency_key)
            await ctx.outbox.add(
                Event(
                    type=EventType.COLECAO_ALTERADA,
                    payload={"user_id": user.id, "cigar_id": req.cigar_id},
                )
            )

        collection = await ctx.oltp.get_collection(col_id)
        assert collection is not None  # acabou de ser criada/garantida acima
        return collection

    @app.get("/collection")
    async def get_collection(
        user: AuthUser = Depends(current_user), ctx: AppContext = Depends(get_ctx)
    ) -> Collection:
        collection = await ctx.oltp.get_collection(f"col:{user.id}")
        if collection is None:
            return Collection(id=f"col:{user.id}", user_id=user.id)
        return collection

    @app.post("/establishments")
    async def create_establishment(
        req: CreateEstablishmentRequest,
        user: AuthUser = Depends(current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> Establishment:
        # Proveniência comunitária — nunca marcado como fonte oficial/parceiro nesta fase.
        est = await ctx.location.create_establishment(
            Establishment(
                id=uuid.uuid4().hex,
                name=req.name,
                lat=req.lat,
                lng=req.lng,
                address=req.address,
                city=req.city,
                state=req.state,
                country=req.country,
                est_type=req.est_type,
                source=f"community:{user.id}",
            )
        )
        await ctx.outbox.add(
            Event(
                type=EventType.ESTABELECIMENTO_CADASTRADO,
                payload={"user_id": user.id, "establishment_id": est.id},
            )
        )
        return est

    @app.post("/establishments/{establishment_id}/availability")
    async def report_availability(
        establishment_id: str,
        req: ReportAvailabilityRequest,
        user: AuthUser = Depends(current_user),
        ctx: AppContext = Depends(get_ctx),
    ) -> ProductAvailability:
        if await ctx.location.get_establishment(establishment_id) is None:
            raise HTTPException(status_code=404, detail="estabelecimento não encontrado")
        # Usuário comum só reporta o que observou: "vi lá" ou "conferi e não tinha" — nunca
        # CONFIRMED, reservado para uma fonte de maior confiança que ainda não existe.
        status = (
            AvailabilityStatus.COMMUNITY_REPORTED
            if req.available
            else AvailabilityStatus.UNAVAILABLE
        )
        availability = await ctx.location.set_availability(
            ProductAvailability(
                id=uuid.uuid4().hex,
                establishment_id=establishment_id,
                cigar_id=req.cigar_id,
                status=status,
                source=f"community:{user.id}",
                price=req.price,
                quantity=req.quantity,
            )
        )
        await ctx.outbox.add(
            Event(
                type=EventType.DISPONIBILIDADE_REPORTADA,
                payload={
                    "user_id": user.id,
                    "establishment_id": establishment_id,
                    "cigar_id": req.cigar_id,
                    "status": str(status),
                },
            )
        )
        return availability

    @app.get("/nearby")
    async def nearby(
        ctx: AppContext = Depends(get_ctx),
        cigar_id: str = Query(...),
        lat: float | None = Query(default=None, ge=-90, le=90),
        lng: float | None = Query(default=None, ge=-180, le=180),
        address: str | None = Query(default=None),
        radius_km: float = Query(default=25.0, gt=0, le=200),
    ) -> list[NearbyResult]:
        # Sem localização persistida (Fase 4, decisão de escopo): lat/lng por requisição, ou
        # address resolvido via GeocodingProvider — nunca gravamos onde o usuário está.
        if lat is None or lng is None:
            if not address:
                raise HTTPException(status_code=400, detail="informe lat+lng ou address")
            resolved = await ctx.geocoding.geocode(address)
            if resolved is None:
                raise HTTPException(
                    status_code=422, detail="não foi possível geocodificar o endereço"
                )
            lat, lng = resolved

        establishments = await ctx.location.list_establishments()
        availability = await ctx.location.list_availability(cigar_id)
        return find_nearby(establishments, availability, lat=lat, lng=lng, radius_km=radius_km)

    return app
