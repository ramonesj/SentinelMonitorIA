"""Add asynchronous intelligence, alerts, and notification delivery tables.

Revision ID: 20260723_0004
Revises: 20260723_0003
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260723_0004"
down_revision = "20260723_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add only new columns/tables; keep existing telemetry data intact."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    telemetry_columns = {column["name"] for column in inspector.get_columns("telemetrybatch")}
    if "analysis_enqueued_at" not in telemetry_columns:
        op.add_column("telemetrybatch", sa.Column("analysis_enqueued_at", sa.DateTime(timezone=True), nullable=True))

    if "aianalysis" not in tables:
        op.create_table(
            "aianalysis",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("telemetry_batch_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("analysis_key", sa.String(length=180), nullable=False),
            sa.Column("provider", sa.String(length=50), nullable=False),
            sa.Column("model_name", sa.String(length=255), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="completed"),
            sa.Column("severity", sa.String(length=20), nullable=False, server_default="info"),
            sa.Column("findings", sa.JSON(), nullable=False),
            sa.Column("explanation", sa.Text(), nullable=True),
            sa.Column("recommendations", sa.JSON(), nullable=False),
            sa.Column("context_metadata", sa.JSON(), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["telemetry_batch_id"], ["telemetrybatch.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id", name="pk_aianalysis"),
            sa.UniqueConstraint("analysis_key", name="uq_aianalysis_analysis_key"),
        )
        for name, column in (
            ("ix_aianalysis_organization_id", "organization_id"),
            ("ix_aianalysis_telemetry_batch_id", "telemetry_batch_id"),
            ("ix_aianalysis_analysis_key", "analysis_key"),
            ("ix_aianalysis_status", "status"),
            ("ix_aianalysis_severity", "severity"),
        ):
            op.create_index(name, "aianalysis", [column])

    if "alert" not in tables:
        op.create_table(
            "alert",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("dedupe_key", sa.String(length=255), nullable=False),
            sa.Column("rule_id", sa.String(length=100), nullable=False),
            sa.Column("source", sa.String(length=50), nullable=False, server_default="intelligence"),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("severity", sa.String(length=20), nullable=False, server_default="info"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="open"),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["analysis_id"], ["aianalysis.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id", name="pk_alert"),
            sa.UniqueConstraint("dedupe_key", name="uq_alert_dedupe_key"),
        )
        for name, column in (
            ("ix_alert_organization_id", "organization_id"),
            ("ix_alert_analysis_id", "analysis_id"),
            ("ix_alert_dedupe_key", "dedupe_key"),
            ("ix_alert_rule_id", "rule_id"),
            ("ix_alert_severity", "severity"),
            ("ix_alert_status", "status"),
        ):
            op.create_index(name, "alert", [column])

    if "notificationdelivery" not in tables:
        op.create_table(
            "notificationdelivery",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("channel", sa.String(length=50), nullable=False),
            sa.Column("destination", sa.String(length=255), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("external_id", sa.String(length=255), nullable=True),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["alert_id"], ["alert.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id", name="pk_notificationdelivery"),
        )
        for name, column in (
            ("ix_notificationdelivery_alert_id", "alert_id"),
            ("ix_notificationdelivery_channel", "channel"),
            ("ix_notificationdelivery_status", "status"),
        ):
            op.create_index(name, "notificationdelivery", [column])


def downgrade() -> None:
    """Preserve intelligence history during routine downgrades."""
    pass
