"""REQ-PKG-001: environment release and enablement are separate."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scenario_package_environment_releases",
        sa.Column("release_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "installation_id",
            sa.Uuid(),
            sa.ForeignKey("scenario_package_installations.installation_id"),
            nullable=False,
        ),
        sa.Column("environment", sa.String(16), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("action_adapter", sa.String(32), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("installation_id", "environment"),
    )
    op.create_index(
        "ix_scenario_package_environment_releases_installation_id",
        "scenario_package_environment_releases",
        ["installation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_scenario_package_environment_releases_installation_id")
    op.drop_table("scenario_package_environment_releases")
