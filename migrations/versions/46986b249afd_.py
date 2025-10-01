"""Add vertical tilt column to projects

Revision ID: 46986b249afd
Revises: 20250930_000001
Create Date: 2025-09-30 15:59:18.677865

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '46986b249afd'
down_revision = '20250930_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('v_tilt_deg', sa.Float(), nullable=False, server_default='0'))
    op.execute("UPDATE projects SET v_tilt_deg = 0 WHERE v_tilt_deg IS NULL")
    op.alter_column('projects', 'v_tilt_deg', server_default=None)


def downgrade() -> None:
    op.drop_column('projects', 'v_tilt_deg')
