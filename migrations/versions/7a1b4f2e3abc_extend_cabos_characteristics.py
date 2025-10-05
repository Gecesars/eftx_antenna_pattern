"""Extend cabos with detailed characteristics

Revision ID: 7a1b4f2e3abc
Revises: 2d2f31cbb9d1
Create Date: 2025-10-05 00:30:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "7a1b4f2e3abc"
down_revision = "2d2f31cbb9d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cabos", sa.Column("datasheet_path", sa.String(length=255), nullable=True))
    op.add_column("cabos", sa.Column("frequency_min_mhz", sa.Float(), nullable=True))
    op.add_column("cabos", sa.Column("frequency_max_mhz", sa.Float(), nullable=True))
    op.add_column("cabos", sa.Column("velocity_factor", sa.Float(), nullable=True))
    op.add_column("cabos", sa.Column("max_power_w", sa.Float(), nullable=True))
    op.add_column("cabos", sa.Column("min_bend_radius_mm", sa.Float(), nullable=True))
    op.add_column("cabos", sa.Column("outer_diameter_mm", sa.Float(), nullable=True))
    op.add_column("cabos", sa.Column("weight_kg_per_km", sa.Float(), nullable=True))
    op.add_column("cabos", sa.Column("vswr_max", sa.Float(), nullable=True))
    op.add_column("cabos", sa.Column("shielding_db", sa.Float(), nullable=True))
    op.add_column("cabos", sa.Column("temperature_min_c", sa.Float(), nullable=True))
    op.add_column("cabos", sa.Column("temperature_max_c", sa.Float(), nullable=True))
    op.add_column("cabos", sa.Column("conductor_material", sa.String(length=80), nullable=True))
    op.add_column("cabos", sa.Column("dielectric_material", sa.String(length=80), nullable=True))
    op.add_column("cabos", sa.Column("jacket_material", sa.String(length=80), nullable=True))
    op.add_column("cabos", sa.Column("shielding_type", sa.String(length=80), nullable=True))
    op.add_column("cabos", sa.Column("conductor_diameter_mm", sa.Float(), nullable=True))
    op.add_column("cabos", sa.Column("dielectric_diameter_mm", sa.Float(), nullable=True))
    op.add_column("cabos", sa.Column("attenuation_db_per_100m_curve", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("cabos", "attenuation_db_per_100m_curve")
    op.drop_column("cabos", "dielectric_diameter_mm")
    op.drop_column("cabos", "conductor_diameter_mm")
    op.drop_column("cabos", "shielding_type")
    op.drop_column("cabos", "jacket_material")
    op.drop_column("cabos", "dielectric_material")
    op.drop_column("cabos", "conductor_material")
    op.drop_column("cabos", "temperature_max_c")
    op.drop_column("cabos", "temperature_min_c")
    op.drop_column("cabos", "shielding_db")
    op.drop_column("cabos", "vswr_max")
    op.drop_column("cabos", "weight_kg_per_km")
    op.drop_column("cabos", "outer_diameter_mm")
    op.drop_column("cabos", "min_bend_radius_mm")
    op.drop_column("cabos", "max_power_w")
    op.drop_column("cabos", "velocity_factor")
    op.drop_column("cabos", "frequency_max_mhz")
    op.drop_column("cabos", "frequency_min_mhz")
    op.drop_column("cabos", "datasheet_path")

