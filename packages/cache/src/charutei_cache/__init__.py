"""Cache do CHARUTEI: exato + semântico (degrau 1 da cascata)."""

from charutei_cache.backends import InMemoryKV, RedisKV
from charutei_cache.exact import ExactCache, normalize_query
from charutei_cache.interfaces import KVBackend, VectorIndex
from charutei_cache.semantic import SemanticCache

__all__ = [
    "InMemoryKV",
    "RedisKV",
    "ExactCache",
    "normalize_query",
    "KVBackend",
    "VectorIndex",
    "SemanticCache",
]
