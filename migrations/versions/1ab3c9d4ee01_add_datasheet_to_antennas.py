"""Add manufacturer and datasheet_path to antennas

Revision ID: 1ab3c9d4ee01
Revises: 9c2e5a1d7f10
Create Date: 2025-10-05 15:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "1ab3c9d4ee01"
down_revision = "9c2e5a1d7f10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("antennas") as batch_op:
        batch_op.add_column(sa.Column("manufacturer", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("datasheet_path", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("antennas") as batch_op:
        batch_op.drop_column("datasheet_path")
        batch_op.drop_column("manufacturer")

