"""Add gain_table to antennas

Revision ID: 3cf2a7b8d912
Revises: 1ab3c9d4ee01
Create Date: 2025-10-05 15:20:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "3cf2a7b8d912"
down_revision = "1ab3c9d4ee01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("antennas", sa.Column("gain_table", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("antennas", "gain_table")

