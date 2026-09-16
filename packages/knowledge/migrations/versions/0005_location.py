"""location intelligence: establishments + product_availability (Fase 4 do upgrade)

Revision ID: 0005_location
Revises: 0004_idempotency
Create Date: 2026-09-16
"""

from alembic import op

revision = "0005_location"
down_revision = "0004_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS establishments (
            id         TEXT PRIMARY KEY,
            name       TEXT NOT NULL,
            lat        DOUBLE PRECISION NOT NULL,
            lng        DOUBLE PRECISION NOT NULL,
            address    TEXT NOT NULL DEFAULT '',
            city       TEXT NOT NULL DEFAULT '',
            state      TEXT NOT NULL DEFAULT '',
            country    TEXT NOT NULL DEFAULT '',
            est_type   TEXT NOT NULL DEFAULT 'tabacaria',
            source     TEXT NOT NULL DEFAULT '',
            confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS product_availability (
            id               TEXT PRIMARY KEY,
            establishment_id TEXT NOT NULL REFERENCES establishments(id) ON DELETE CASCADE,
            cigar_id         TEXT NOT NULL,
            status           TEXT NOT NULL DEFAULT 'unknown',
            source           TEXT NOT NULL DEFAULT '',
            confidence       DOUBLE PRECISION NOT NULL DEFAULT 1.0,
            price            DOUBLE PRECISION,
            quantity         INTEGER,
            observed_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_product_availability_cigar "
        "ON product_availability (cigar_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS product_availability CASCADE")
    op.execute("DROP TABLE IF EXISTS establishments CASCADE")
