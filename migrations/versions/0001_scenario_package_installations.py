"""REQ-PKG-001: generic package installation metadata."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scenario_package_installations",
        sa.Column("installation_id", sa.Uuid(), primary_key=True),
        sa.Column("package_id", sa.String(64), nullable=False),
        sa.Column("package_version", sa.String(32), nullable=False),
        sa.Column("content_digest", sa.String(80), nullable=False),
        sa.Column("manifest", sa.JSON(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("granted_permissions", sa.JSON(), nullable=False),
        sa.Column("binding_refs", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("package_id", "package_version"),
    )
    op.create_index(
        "ix_scenario_package_installations_package_id",
        "scenario_package_installations",
        ["package_id"],
    )
    op.create_index(
        "ix_scenario_package_installations_state", "scenario_package_installations", ["state"]
    )


def downgrade() -> None:
    op.drop_index("ix_scenario_package_installations_state")
    op.drop_index("ix_scenario_package_installations_package_id")
    op.drop_table("scenario_package_installations")
