"""Add one-time organization invitations.

Revision ID: 20260723_0003
Revises: 20260723_0002
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260723_0003"
down_revision = "20260723_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the invitation table without changing existing data."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "organizationinvitation" not in tables:
        op.create_table(
            "organizationinvitation",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("invited_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("accepted_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("role", sa.String(length=50), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["invited_by_user_id"], ["user.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["accepted_by_user_id"], ["user.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id", name="pk_organizationinvitation"),
            sa.UniqueConstraint("token_hash", name="uq_organizationinvitation_token_hash"),
        )
        op.create_index("ix_organizationinvitation_organization_id", "organizationinvitation", ["organization_id"])
        op.create_index("ix_organizationinvitation_invited_by_user_id", "organizationinvitation", ["invited_by_user_id"])
        op.create_index("ix_organizationinvitation_accepted_by_user_id", "organizationinvitation", ["accepted_by_user_id"])
        op.create_index("ix_organizationinvitation_email", "organizationinvitation", ["email"])
        op.create_index("ix_organizationinvitation_token_hash", "organizationinvitation", ["token_hash"])
        op.create_index("ix_organizationinvitation_status", "organizationinvitation", ["status"])
        op.create_index("ix_organizationinvitation_expires_at", "organizationinvitation", ["expires_at"])


def downgrade() -> None:
    """Keep invitation history during routine downgrades."""
    pass
