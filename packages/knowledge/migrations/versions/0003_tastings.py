"""degustações + aging: tasting_notes + collection_items.created_at (F2.5)

Revision ID: 0003_tastings
Revises: 0002_events
Create Date: 2026-07-11
"""

from alembic import op

revision = "0003_tastings"
down_revision = "0002_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE collection_items "
        "ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now()"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tasting_notes (
            id         TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            cigar_id   TEXT NOT NULL,
            rating     INTEGER NOT NULL,
            flavors    JSONB NOT NULL DEFAULT '[]',
            occasion   TEXT NOT NULL DEFAULT '',
            note       TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasting_notes_user_cigar "
        "ON tasting_notes (user_id, cigar_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tasting_notes CASCADE")
    op.execute("ALTER TABLE collection_items DROP COLUMN IF EXISTS created_at")
