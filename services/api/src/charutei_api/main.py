"""Entrypoint ASGI para dev local: `uvicorn charutei_api.main:app`.

Monta o contexto padrão (in-memory + providers fake) no import. Em produção, construir o
contexto com implementações Postgres/Supabase e injetar via `create_app`.
"""

from __future__ import annotations

import asyncio

from charutei_api.app import create_app
from charutei_api.context import build_context

app = create_app(asyncio.run(build_context()))
