"""Testes de endurecimento de segurança (S19): CORS por env, guard de produção, rate limit."""

import httpx
import pytest
from charutei_api import build_context, create_app
from charutei_api.auth import FakeAuthProvider, SupabaseAuthProvider, build_auth_provider
from charutei_api.security import (
    SlidingWindowRateLimiter,
    cors_origins,
    is_production,
)

_AUTH = {"Authorization": "Bearer alice"}


# --- CORS / ambiente ---------------------------------------------------------


def test_cors_dev_defaults_localhost(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CHARUTEI_CORS_ORIGINS", raising=False)
    monkeypatch.delenv("CHARUTEI_ENV", raising=False)
    origins = cors_origins()
    assert "http://localhost:3001" in origins
    assert "*" not in origins


def test_cors_from_env_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHARUTEI_CORS_ORIGINS", "https://a.com, https://b.com")
    assert cors_origins() == ["https://a.com", "https://b.com"]


def test_cors_production_without_config_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CHARUTEI_CORS_ORIGINS", raising=False)
    monkeypatch.setenv("CHARUTEI_ENV", "production")
    assert is_production() is True
    assert cors_origins() == []  # força configuração explícita; nunca `*`


# --- Guard de produção na auth ----------------------------------------------


def test_prod_guard_refuses_fake_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.setenv("CHARUTEI_ENV", "production")
    with pytest.raises(RuntimeError, match="SUPABASE_JWT_SECRET"):
        build_auth_provider()


def test_prod_with_secret_uses_supabase(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHARUTEI_ENV", "production")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "x" * 40)
    assert isinstance(build_auth_provider(), SupabaseAuthProvider)


def test_dev_defaults_to_fake(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.delenv("CHARUTEI_ENV", raising=False)
    assert isinstance(build_auth_provider(), FakeAuthProvider)


# --- Rate limiter (unidade) --------------------------------------------------


def test_rate_limiter_allows_then_blocks() -> None:
    rl = SlidingWindowRateLimiter(limit=2, window_s=60)
    assert rl.allow("k", now=0.0) is True
    assert rl.allow("k", now=0.0) is True
    assert rl.allow("k", now=0.0) is False  # 3ª na janela → bloqueia
    assert rl.retry_after("k", now=0.0) >= 1


def test_rate_limiter_window_slides() -> None:
    rl = SlidingWindowRateLimiter(limit=1, window_s=10)
    assert rl.allow("k", now=0.0) is True
    assert rl.allow("k", now=5.0) is False  # dentro da janela
    assert rl.allow("k", now=11.0) is True  # janela passou → libera


def test_rate_limiter_disabled_when_limit_zero() -> None:
    rl = SlidingWindowRateLimiter(limit=0, window_s=60)
    assert rl.enabled is False
    assert all(rl.allow("k", now=0.0) for _ in range(100))


# --- Rate limit end-to-end (API) --------------------------------------------


async def test_rate_limit_returns_429(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHARUTEI_RATE_LIMIT", "2")  # lido no create_app
    ctx = await build_context()
    app = create_app(ctx)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/healthz")).status_code == 200  # isento do limite
        assert (await client.get("/catalog", headers=_AUTH)).status_code == 200
        assert (await client.get("/catalog", headers=_AUTH)).status_code == 200
        blocked = await client.get("/catalog", headers=_AUTH)
        assert blocked.status_code == 429
        assert "Retry-After" in blocked.headers
