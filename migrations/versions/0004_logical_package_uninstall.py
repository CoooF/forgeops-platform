"""REQ-SDK-001: non-destructive package uninstall preserves historical evidence."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scenario_package_installations",
        sa.Column("uninstalled_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scenario_package_installations", "uninstalled_at")
