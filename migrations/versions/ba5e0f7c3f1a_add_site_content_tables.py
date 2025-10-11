"""add site content tables

Revision ID: ba5e0f7c3f1a
Revises: 9c2e5a1d7f10
Create Date: 2025-10-10 21:20:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "ba5e0f7c3f1a"
down_revision = "6d11b0f5a7aa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_content_blocks",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.UniqueConstraint("slug", name="uq_site_content_blocks_slug"),
    )
    op.create_index("ix_site_content_blocks_slug", "site_content_blocks", ["slug"], unique=True)

    op.create_table(
        "site_documents",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("thumbnail_path", sa.String(length=255), nullable=True),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.UniqueConstraint("filename", name="uq_site_documents_filename"),
    )
    op.create_index("ix_site_documents_filename", "site_documents", ["filename"], unique=True)

    op.execute("ALTER TABLE site_documents ALTER COLUMN is_featured DROP DEFAULT")


def downgrade() -> None:
    op.drop_index("ix_site_documents_filename", table_name="site_documents")
    op.drop_table("site_documents")
    op.drop_index("ix_site_content_blocks_slug", table_name="site_content_blocks")
    op.drop_table("site_content_blocks")
