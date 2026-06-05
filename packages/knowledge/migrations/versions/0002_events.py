"""eventos: outbox transacional + registro de processados

Revision ID: 0002_events
Revises: 0001_initial
Create Date: 2026-06-04
"""

from alembic import op
from charutei_events.postgres import EVENTS_SCHEMA

revision = "0002_events"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(EVENTS_SCHEMA)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS processed_events, outbox CASCADE")
