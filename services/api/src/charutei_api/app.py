"""BFF/Gateway FastAPI do CHARUTEI.

Fluxo do app mobile: autentica → captura/upload de anilha → reconhecimento → adiciona à coleção.
Escritas publicam eventos via outbox (consumidos pelo Embedding Worker e demais agentes).
"""

from __future__ import annotations

import uuid

from charutei_contracts import BandImage, BandRecognitionResult
from charutei_events import EventType
from charutei_events.models import Event
from charutei_knowledge import Band, Collection, CollectionItem, NodeType, User
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from charutei_api.auth import AuthUser
from charutei_api.context import AppContext
from charutei_api.schemas import AddItemRequest, CatalogEntry, RecognizeRequest


def create_app(ctx: AppContext) -> FastAPI:
    app = FastAPI(title="CHARUTEI BFF", version="0.0.0")
    app.state.ctx = ctx
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # demo — restringir em produção
        allow_methods=["*"],
        allow_headers=["*"],
    )

    async def current_user(authorization: str = Header(default="")) -> AuthUser:
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
    async def catalog() -> list[CatalogEntry]:
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
        req: RecognizeRequest, user: AuthUser = Depends(current_user)
    ) -> BandRecognitionResult:
        result = await ctx.band_agent.recognize(
            BandImage(
                ref=req.ref,
                visual_text=req.visual_text,
                ocr_text=req.ocr_text,
                data_b64=req.data_b64,
            )
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

    @app.post("/collection/items")
    async def add_item(
        req: AddItemRequest,
        user: AuthUser = Depends(current_user),
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
    async def get_collection(user: AuthUser = Depends(current_user)) -> Collection:
        collection = await ctx.oltp.get_collection(f"col:{user.id}")
        if collection is None:
            return Collection(id=f"col:{user.id}", user_id=user.id)
        return collection

    return app
