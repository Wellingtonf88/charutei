"""Autenticação atrás de interface (Supabase Auth na produção; Fake em dev/CI).

Mantém o padrão do projeto: provedor externo atrás de Protocol, com `Fake*` determinístico
para testes — sem exigir chaves. O adaptador Supabase real valida o JWT e é ligado por env.
"""

from __future__ import annotations

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
    """Adaptador real (placeholder). Valida o JWT do Supabase — ligado quando houver chaves."""

    def __init__(self, jwt_secret: str) -> None:
        self._secret = jwt_secret

    async def verify(self, token: str) -> AuthUser | None:  # pragma: no cover - sem chaves no MVP
        raise NotImplementedError(
            "SupabaseAuthProvider ainda não implementado. Use FakeAuthProvider (dev) "
            "ou ligue a validação de JWT do Supabase quando as chaves estiverem disponíveis."
        )
