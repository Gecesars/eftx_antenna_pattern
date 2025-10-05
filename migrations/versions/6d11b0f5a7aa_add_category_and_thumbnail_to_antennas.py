"""Add category and thumbnail_path to antennas

Revision ID: 6d11b0f5a7aa
Revises: 3cf2a7b8d912
Create Date: 2025-10-05 16:05:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "6d11b0f5a7aa"
down_revision = "3cf2a7b8d912"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("antennas") as batch_op:
        batch_op.add_column(sa.Column("category", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("thumbnail_path", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("antennas") as batch_op:
        batch_op.drop_column("thumbnail_path")
        batch_op.drop_column("category")

