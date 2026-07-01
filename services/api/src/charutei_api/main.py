"""Entrypoint ASGI: `uvicorn charutei_api.main:app`.

O contexto é montado no **lifespan** (boot do servidor), não no import — assim recursos ligados
ao event loop (conexão Postgres quando `DATABASE_URL` está setado) nascem no loop do uvicorn e
são fechados no shutdown. Sem `DATABASE_URL`, cai no modo in-memory (dev/demo).
"""

from __future__ import annotations

from charutei_api.app import create_app

app = create_app()
