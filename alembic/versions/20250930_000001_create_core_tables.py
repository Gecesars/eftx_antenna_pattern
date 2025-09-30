"""create core tables"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20250930_000001"
down_revision = None
branch_labels = None
depends_on = None


sexenum = sa.Enum("M", "F", "X", name="sexenum")
pat_enum = sa.Enum("HRP", "VRP", name="patterntype")


def upgrade() -> None:
    sexenum.create(op.get_bind())
    pat_enum.create(op.get_bind())

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("sex", sexenum, nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("address_line", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("state", sa.String(length=64), nullable=True),
        sa.Column("postal_code", sa.String(length=16), nullable=True),
        sa.Column("country", sa.String(length=64), nullable=True),
        sa.Column("cpf", sa.String(length=14), nullable=True),
        sa.Column("cnpj", sa.String(length=18), nullable=True),
        sa.Column("cnpj_verified", sa.Boolean(), nullable=True),
        sa.Column("email_confirmed", sa.Boolean(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("role", sa.String(length=16), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("cpf"),
        sa.UniqueConstraint("cnpj"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)

    op.create_table(
        "antennas",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("model_number", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("nominal_gain_dbd", sa.Float(), nullable=True),
        sa.Column("polarization", sa.String(length=32), nullable=True),
        sa.Column("frequency_min_mhz", sa.Float(), nullable=True),
        sa.Column("frequency_max_mhz", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_number"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "antenna_patterns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("antenna_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pattern_type", pat_enum, nullable=False),
        sa.Column("angles_deg", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("amplitudes_linear", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["antenna_id"], ["antennas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("antenna_id", "pattern_type", name="uq_pattern_type"),
    )

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("antenna_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("frequency_mhz", sa.Float(), nullable=False),
        sa.Column("tx_power_w", sa.Float(), nullable=False),
        sa.Column("tower_height_m", sa.Float(), nullable=False),
        sa.Column("cable_type", sa.String(length=120), nullable=True),
        sa.Column("cable_length_m", sa.Float(), nullable=True),
        sa.Column("splitter_loss_db", sa.Float(), nullable=True),
        sa.Column("connector_loss_db", sa.Float(), nullable=True),
        sa.Column("vswr_target", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("v_count", sa.Integer(), nullable=True),
        sa.Column("v_spacing_m", sa.Float(), nullable=True),
        sa.Column("v_beta_deg", sa.Float(), nullable=True),
        sa.Column("v_level_amp", sa.Float(), nullable=True),
        sa.Column("v_norm_mode", sa.String(length=16), nullable=True),
        sa.Column("h_count", sa.Integer(), nullable=True),
        sa.Column("h_spacing_m", sa.Float(), nullable=True),
        sa.Column("h_beta_deg", sa.Float(), nullable=True),
        sa.Column("h_step_deg", sa.Float(), nullable=True),
        sa.Column("h_level_amp", sa.Float(), nullable=True),
        sa.Column("h_norm_mode", sa.String(length=16), nullable=True),
        sa.Column("feeder_loss_db", sa.Float(), nullable=True),
        sa.Column("composition_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["antenna_id"], ["antennas.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_owner_id"), "projects", ["owner_id"], unique=False)

    op.create_table(
        "project_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("erp_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("pat_path", sa.String(length=255), nullable=False),
        sa.Column("prn_path", sa.String(length=255), nullable=False),
        sa.Column("pdf_path", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("project_exports")
    op.drop_index(op.f("ix_projects_owner_id"), table_name="projects")
    op.drop_table("projects")
    op.drop_table("antenna_patterns")
    op.drop_table("antennas")
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    pat_enum.drop(op.get_bind())
    sexenum.drop(op.get_bind())
