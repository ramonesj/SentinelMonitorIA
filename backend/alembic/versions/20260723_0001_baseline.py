"""Create the baseline schema without touching existing data.

Revision ID: 20260723_0001
Revises:
"""

from alembic import op

from src.models.base import Base
from src.models import organization, telemetry, user  # noqa: F401

revision = "20260723_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create only tables that are missing from the target database."""
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    """Baseline downgrades are intentionally non-destructive."""
    pass
