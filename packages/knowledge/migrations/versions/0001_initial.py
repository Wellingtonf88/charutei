"""fundação: OLTP + KG relacional + vetor (pgvector)

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-04
"""

from pathlib import Path

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

# DDL com fonte única em postgres/schema.sql.
_SCHEMA = (
    Path(__file__).resolve().parents[2] / "src" / "charutei_knowledge" / "postgres" / "schema.sql"
)


def upgrade() -> None:
    op.execute(_SCHEMA.read_text(encoding="utf-8"))


def downgrade() -> None:
    op.execute(
        "DROP TABLE IF EXISTS embeddings, collection_items, collections, bands, "
        "kg_edges, kg_nodes, kg_version, users CASCADE"
    )
