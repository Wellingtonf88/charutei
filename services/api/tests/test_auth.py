"""Testes do SupabaseAuthProvider (S11): validação real de JWT HS256."""

import time

import pytest
from charutei_api.auth import FakeAuthProvider, SupabaseAuthProvider, build_auth_provider

jwt = pytest.importorskip("jwt")  # pyjwt

_SECRET = "super-secret-jwt-key-for-tests-0123456789abcdef"  # ≥32 bytes (RFC 7518)


def _token(**overrides) -> str:  # type: ignore[no-untyped-def]
    claims = {
        "sub": "user-123",
        "email": "alice@example.com",
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
        **overrides,
    }
    return jwt.encode(claims, _SECRET, algorithm="HS256")


async def test_valid_token_returns_user() -> None:
    provider = SupabaseAuthProvider(_SECRET)
    user = await provider.verify(_token())
    assert user is not None
    assert user.id == "user-123"
    assert user.email == "alice@example.com"


async def test_empty_token_is_rejected() -> None:
    assert await SupabaseAuthProvider(_SECRET).verify("   ") is None


async def test_bad_signature_is_rejected() -> None:
    provider = SupabaseAuthProvider("outro-segredo-bem-diferente-0123456789abcdef")
    assert await provider.verify(_token()) is None


async def test_expired_token_is_rejected() -> None:
    provider = SupabaseAuthProvider(_SECRET)
    assert await provider.verify(_token(exp=int(time.time()) - 10)) is None


async def test_wrong_audience_is_rejected() -> None:
    provider = SupabaseAuthProvider(_SECRET)  # espera "authenticated"
    assert await provider.verify(_token(aud="outra")) is None


async def test_missing_sub_is_rejected() -> None:
    # token sem `sub` viola options={"require": ["sub", ...]} → PyJWTError → None
    token = jwt.encode(
        {"email": "x@y.z", "aud": "authenticated", "exp": int(time.time()) + 60},
        _SECRET,
        algorithm="HS256",
    )
    assert await SupabaseAuthProvider(_SECRET).verify(token) is None


def test_build_auth_provider_selects_by_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    assert isinstance(build_auth_provider(), FakeAuthProvider)
    monkeypatch.setenv("SUPABASE_JWT_SECRET", _SECRET)
    assert isinstance(build_auth_provider(), SupabaseAuthProvider)
