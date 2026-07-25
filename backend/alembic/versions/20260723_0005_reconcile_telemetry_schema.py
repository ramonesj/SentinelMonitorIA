"""Reconcile the telemetry batch schema with the ORM model.

Revision ID: 20260723_0005
Revises: 20260723_0004
"""

from alembic import op
import sqlalchemy as sa


revision = "20260723_0005"
down_revision = "20260723_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add telemetry columns that may be missing from an existing local database."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "telemetrybatch" not in tables:
        return

    columns = {column["name"] for column in inspector.get_columns("telemetrybatch")}
    if "analysis_enqueued_at" not in columns:
        op.add_column(
            "telemetrybatch",
            sa.Column("analysis_enqueued_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    """Remove only the reconciliation column when explicitly downgrading."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "telemetrybatch" not in tables:
        return

    columns = {column["name"] for column in inspector.get_columns("telemetrybatch")}
    if "analysis_enqueued_at" in columns:
        op.drop_column("telemetrybatch", "analysis_enqueued_at")
