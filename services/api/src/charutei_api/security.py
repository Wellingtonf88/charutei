"""Endurecimento de segurança do BFF — configurável por env, seguro por padrão.

- CORS: origens explícitas (nunca `*` em produção) via `CHARUTEI_CORS_ORIGINS`.
- Rate limiting: janela deslizante em memória por cliente (1ª camada anti-abuso; num deploy
  multi-réplica, o passo de escala é um store compartilhado — Redis).
- `CHARUTEI_ENV=production` habilita os padrões estritos e o fail-fast de auth (ver `auth.py`).
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque

# Origens de dev por padrão (Next.js local). Em produção, defina CHARUTEI_CORS_ORIGINS.
_DEV_ORIGINS = ["http://localhost:3000", "http://localhost:3001"]


def is_production() -> bool:
    return os.environ.get("CHARUTEI_ENV", "").lower() == "production"


def cors_origins() -> list[str]:
    """Lista de origens permitidas. `CHARUTEI_CORS_ORIGINS` (CSV) tem precedência.

    Sem configuração: em produção retorna `[]` (bloqueia — força configuração explícita);
    em dev, os hosts locais do Next.js. Nunca retorna `*`.
    """
    raw = os.environ.get("CHARUTEI_CORS_ORIGINS", "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return [] if is_production() else list(_DEV_ORIGINS)


def rate_limit_config() -> tuple[int, float]:
    """(máximo de requisições, janela em segundos). Default 300/60s; 0 desabilita."""
    limit = int(os.environ.get("CHARUTEI_RATE_LIMIT", "300"))
    window = float(os.environ.get("CHARUTEI_RATE_WINDOW_S", "60"))
    return limit, window


class SlidingWindowRateLimiter:
    """Rate limiter por chave (cliente) com janela deslizante em memória. `limit<=0` = desligado."""

    def __init__(self, limit: int, window_s: float) -> None:
        self._limit = limit
        self._window = window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    @property
    def enabled(self) -> bool:
        return self._limit > 0

    def allow(self, key: str, now: float | None = None) -> bool:
        """True se a requisição está dentro do limite; registra o hit quando permitido."""
        if not self.enabled:
            return True
        now = time.monotonic() if now is None else now
        hits = self._hits[key]
        horizon = now - self._window
        while hits and hits[0] <= horizon:
            hits.popleft()
        if len(hits) >= self._limit:
            return False
        hits.append(now)
        return True

    def retry_after(self, key: str, now: float | None = None) -> int:
        """Segundos até liberar um slot (para o header Retry-After)."""
        hits = self._hits.get(key)
        if not hits:
            return 0
        now = time.monotonic() if now is None else now
        return max(1, int(self._window - (now - hits[0])))
