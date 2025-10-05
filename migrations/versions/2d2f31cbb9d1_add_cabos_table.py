"""Add cabos table and link to projects

Revision ID: 2d2f31cbb9d1
Revises: 8b4e91acba2d
Create Date: 2025-10-05 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "2d2f31cbb9d1"
down_revision = "730014782f4e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cabos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("model_code", sa.String(length=120), nullable=False),
        sa.Column("size_inch", sa.String(length=32), nullable=True),
        sa.Column("attenuation_db_per_100m", sa.Float(), nullable=False, server_default=sa.text("5.0")),
        sa.Column("impedance_ohms", sa.Float(), nullable=True),
        sa.Column("manufacturer", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("display_name", name="uq_cabos_display_name"),
        sa.UniqueConstraint("model_code", name="uq_cabos_model_code"),
    )

    op.add_column("projects", sa.Column("cable_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_projects_cable_id", "projects", ["cable_id"], unique=False)
    op.create_foreign_key(
        "fk_projects_cable_id_cabos",
        "projects",
        "cabos",
        ["cable_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_projects_cable_id_cabos", "projects", type_="foreignkey")
    op.drop_index("ix_projects_cable_id", table_name="projects")
    op.drop_column("projects", "cable_id")
    op.drop_table("cabos")
