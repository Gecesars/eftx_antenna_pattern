"""empty message

Revision ID: 3e83237a9467
Revises: 46986b249afd
Create Date: 2025-10-01 09:28:25.309763
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = "3e83237a9467"
down_revision = "46986b249afd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("projects")}

    if "v_tilt_deg" not in columns:
        op.add_column("projects", sa.Column("v_tilt_deg", sa.Float(), nullable=True))

    op.execute(text("UPDATE projects SET v_tilt_deg = 0 WHERE v_tilt_deg IS NULL"))
    op.alter_column(
        "projects",
        "v_tilt_deg",
        existing_type=sa.Float(),
        nullable=False,
    )

    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.VARCHAR(length=255),
        type_=sa.String(length=512),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=512),
        type_=sa.VARCHAR(length=255),
        existing_nullable=False,
    )

    inspector = inspect(op.get_bind())
    if "v_tilt_deg" in {col["name"] for col in inspector.get_columns("projects")}:
        op.drop_column("projects", "v_tilt_deg")
