"""BFF/Gateway FastAPI do CHARUTEI.

Fluxo do app mobile: autentica → captura/upload de anilha → reconhecimento → adiciona à coleção.
Escritas publicam eventos via outbox (consumidos pelo Embedding Worker e demais agentes).

O contexto (repos/agentes) é injetado. Em teste, passa-se um `AppContext` pronto; em produção
(`main.py`), `create_app()` sem contexto o monta no **lifespan** — necessário para recursos
ligados ao event loop do servidor (ex.: conexão Postgres), fechados no shutdown.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from charutei_contracts import BandImage, BandRecognitionResult, CascadeResult
from charutei_events import EventType
from charutei_events.models import Event
from charutei_knowledge import Band, Collection, CollectionItem, NodeType, TastingNote, User
from charutei_orchestrator import RequestKind
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint

from charutei_api.auth import AuthUser
from charutei_api.context import AppContext, build_context
from charutei_api.schemas import (
    AddItemRequest,
    AskRequest,
    CatalogEntry,
    RecognizeRequest,
    TastingRequest,
)
from charutei_api.security import SlidingWindowRateLimiter, cors_origins, rate_limit_config


def create_app(ctx: AppContext | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
        # Monta o contexto no boot do servidor quando não injetado (produção/main.py) — assim a
        # conexão Postgres nasce no loop do uvicorn. Fecha no shutdown.
        owns = app.state.ctx is None
        if owns:
            app.state.ctx = await build_context()
        try:
            yield
        finally:
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
        return await ctx.oltp.add_tasting(
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

    @app.get("/tasting")
    async def list_tastings(
        user: AuthUser = Depends(current_user),
        ctx: AppContext = Depends(get_ctx),
        cigar_id: str | None = None,
    ) -> list[TastingNote]:
        return await ctx.oltp.list_tastings(user.id, cigar_id)

    @app.post("/collection/items")
    async def add_item(
        req: AddItemRequest,
        user: AuthUser = Depends(current_user),
        ctx: AppContext = Depends(get_ctx),
        idempotency_key: str | None = Header(default=None),
    ) -> Collection:
        col_id = f"col:{user.id}"
        if await ctx.oltp.get_collection(col_id) is None:
            await ctx.oltp.create_collection(Collection(id=col_id, user_id=user.id))

        # Idempotência: a mesma Idempotency-Key não adiciona o item duas vezes.
        if idempotency_key is None or idempotency_key not in ctx.idempotency_keys:
            await ctx.oltp.add_collection_item(
                CollectionItem(
                    id=uuid.uuid4().hex,
                    collection_id=col_id,
                    cigar_id=req.cigar_id,
                    quantity=req.quantity,
                )
            )
            if idempotency_key is not None:
                ctx.idempotency_keys.add(idempotency_key)
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

    return app
