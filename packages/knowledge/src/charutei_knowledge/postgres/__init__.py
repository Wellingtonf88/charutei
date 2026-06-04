"""Implementação Postgres dos repositórios (pgvector + KG relacional via SQL).

Importado sob demanda (requer o extra `postgres`: psycopg, pgvector). Mantido FORA do
`__init__` do pacote para que a importação padrão (in-memory/CI) não exija psycopg.
"""

from charutei_knowledge.postgres.repositories import (
    PostgresKnowledgeGraph,
    PostgresOltp,
    PostgresVectorRepository,
    apply_schema,
)

__all__ = [
    "PostgresKnowledgeGraph",
    "PostgresOltp",
    "PostgresVectorRepository",
    "apply_schema",
]
