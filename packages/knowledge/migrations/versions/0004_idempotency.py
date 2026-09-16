"""idempotency_keys durável: substitui o set em memória de POST /collection/items (upgrade Fase 1)

Revision ID: 0004_idempotency
Revises: 0003_tastings
Create Date: 2026-09-16
"""

from alembic import op

revision = "0004_idempotency"
down_revision = "0003_tastings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS idempotency_keys (
            key        TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS idempotency_keys CASCADE")
