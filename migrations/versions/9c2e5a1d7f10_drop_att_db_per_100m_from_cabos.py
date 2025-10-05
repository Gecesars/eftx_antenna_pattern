"""Drop attenuation_db_per_100m from cabos

Revision ID: 9c2e5a1d7f10
Revises: 7a1b4f2e3abc
Create Date: 2025-10-05 14:50:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "9c2e5a1d7f10"
down_revision = "7a1b4f2e3abc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("cabos") as batch_op:
        try:
            batch_op.drop_column("attenuation_db_per_100m")
        except Exception:
            # coluna pode ja ter sido removida em algum ambiente; ignore
            pass


def downgrade() -> None:
    with op.batch_alter_table("cabos") as batch_op:
        batch_op.add_column(sa.Column("attenuation_db_per_100m", sa.Float(), nullable=True))
