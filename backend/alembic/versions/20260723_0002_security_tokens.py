"""Add persisted JWT sessions and API-key security metadata.

Revision ID: 20260723_0002
Revises: 20260723_0001
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260723_0002"
down_revision = "20260723_0001"
branch_labels = None
depends_on = None


def _column_exists(bind, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Apply additive, idempotent security changes."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "token" in tables:
        if not _column_exists(bind, "token", "scopes"):
            op.add_column("token", sa.Column("scopes", sa.Text(), nullable=True))
        if not _column_exists(bind, "token", "revoked_at"):
            op.add_column("token", sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))
        if not _column_exists(bind, "token", "replaced_by_id"):
            op.add_column(
                "token",
                sa.Column("replaced_by_id", postgresql.UUID(as_uuid=True), nullable=True),
            )
            op.create_foreign_key(
                "fk_token_replaced_by_id_token",
                "token",
                "token",
                ["replaced_by_id"],
                ["id"],
                ondelete="SET NULL",
            )

    if "jwtsession" not in tables:
        op.create_table(
            "jwtsession",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("jti", sa.String(length=36), nullable=False),
            sa.Column("token_type", sa.String(length=20), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("replaced_by_jti", sa.String(length=36), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id", name="pk_jwtsession"),
            sa.UniqueConstraint("jti", name="uq_jwtsession_jti"),
        )
        op.create_index("ix_jwtsession_user_id", "jwtsession", ["user_id"])
        op.create_index("ix_jwtsession_expires_at", "jwtsession", ["expires_at"])


def downgrade() -> None:
    """Do not remove security columns or session history automatically."""
    pass
