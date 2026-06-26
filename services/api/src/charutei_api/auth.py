"""Autenticação atrás de interface (Supabase Auth na produção; Fake em dev/CI).

Mantém o padrão do projeto: provedor externo atrás de Protocol, com `Fake*` determinístico
para testes — sem exigir chaves. O adaptador Supabase real valida o JWT e é ligado por env.
"""

from __future__ import annotations

import os
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class AuthUser(BaseModel):
    id: str
    email: str


@runtime_checkable
class AuthProvider(Protocol):
    async def verify(self, token: str) -> AuthUser | None:
        """Valida o token e retorna o usuário, ou None se inválido."""
        ...


class FakeAuthProvider:
    """Dev/CI: qualquer token não-vazio vira um usuário estável (id = token)."""

    async def verify(self, token: str) -> AuthUser | None:
        token = token.strip()
        if not token:
            return None
        return AuthUser(id=f"user:{token}", email=f"{token}@dev.charutei")


class SupabaseAuthProvider:
    """Adaptador real: valida o JWT do Supabase Auth (HS256, segredo do projeto).

    Supabase assina o access token em HS256 com o JWT secret do projeto; os claims trazem
    `sub` (id do usuário), `email` e `aud` (por padrão "authenticated"). `pyjwt` é lazy-import
    (mesmo padrão dos providers): o módulo importa sem a lib; ela só é exigida ao validar.
    """

    def __init__(self, jwt_secret: str, *, audience: str = "authenticated") -> None:
        self._secret = jwt_secret
        self._audience = audience

    async def verify(self, token: str) -> AuthUser | None:
        token = token.strip()
        if not token:
            return None
        import jwt  # pyjwt — lazy

        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=["HS256"],
                audience=self._audience,
                options={"require": ["sub", "exp"]},
            )
        except jwt.PyJWTError:
            return None  # assinatura inválida, expirado, aud divergente, claim ausente

        sub = claims.get("sub")
        if not sub:
            return None
        return AuthUser(id=str(sub), email=str(claims.get("email", "")))


def build_auth_provider() -> AuthProvider:
    """Fábrica: SupabaseAuthProvider quando há SUPABASE_JWT_SECRET no ambiente; senão Fake.

    Espelha `build_providers` — o real liga por env, sem exigir chave em dev/CI.
    """
    secret = os.environ.get("SUPABASE_JWT_SECRET")
    if secret:
        audience = os.environ.get("SUPABASE_JWT_AUD", "authenticated")
        return SupabaseAuthProvider(secret, audience=audience)
    return FakeAuthProvider()
