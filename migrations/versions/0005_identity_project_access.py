"""REQ-IAM-001/REQ-POL-001: tenant, project, identity and scoped authorization."""

from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audit_events",
        sa.Column("scope_ref", sa.String(256), nullable=False, server_default="platform://local"),
    )
    op.add_column(
        "audit_events",
        sa.Column(
            "policy_version",
            sa.String(64),
            nullable=False,
            server_default="package-lifecycle-v1",
        ),
    )
    op.create_table(
        "principals",
        sa.Column("principal_id", sa.Uuid(), primary_key=True),
        sa.Column("subject_ref", sa.String(256), nullable=False, unique=True),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(256), nullable=False),
        sa.Column("updated_by", sa.String(256), nullable=False),
        sa.CheckConstraint("kind IN ('USER', 'SERVICE')", name="ck_principals_kind"),
        sa.CheckConstraint("state IN ('ACTIVE', 'DISABLED')", name="ck_principals_state"),
    )
    op.create_index("ix_principals_subject_ref", "principals", ["subject_ref"])
    op.create_index("ix_principals_state", "principals", ["state"])

    op.create_table(
        "organizations",
        sa.Column("organization_id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(256), nullable=False),
        sa.Column("updated_by", sa.String(256), nullable=False),
        sa.CheckConstraint(
            "state IN ('ACTIVE', 'SUSPENDED', 'ARCHIVED')", name="ck_organizations_state"
        ),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"])
    op.create_index("ix_organizations_state", "organizations", ["state"])

    op.create_table(
        "workspaces",
        sa.Column("workspace_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.organization_id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(256), nullable=False),
        sa.Column("updated_by", sa.String(256), nullable=False),
        sa.UniqueConstraint("organization_id", "slug", name="uq_workspaces_parent_slug"),
        sa.CheckConstraint("state IN ('ACTIVE', 'ARCHIVED')", name="ck_workspaces_state"),
    )
    op.create_index("ix_workspaces_organization_id", "workspaces", ["organization_id"])
    op.create_index("ix_workspaces_state", "workspaces", ["state"])

    op.create_table(
        "projects",
        sa.Column("project_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.workspace_id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False, server_default=""),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(256), nullable=False),
        sa.Column("updated_by", sa.String(256), nullable=False),
        sa.UniqueConstraint("workspace_id", "slug", name="uq_projects_parent_slug"),
        sa.CheckConstraint("state IN ('DRAFT', 'ACTIVE', 'ARCHIVED')", name="ck_projects_state"),
    )
    op.create_index("ix_projects_workspace_id", "projects", ["workspace_id"])
    op.create_index("ix_projects_state", "projects", ["state"])

    op.create_table(
        "memberships",
        sa.Column("membership_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "principal_id",
            sa.Uuid(),
            sa.ForeignKey("principals.principal_id"),
            nullable=False,
        ),
        sa.Column("scope_type", sa.String(16), nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.organization_id"),
            nullable=True,
        ),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.workspace_id"),
            nullable=True,
        ),
        sa.Column(
            "project_id", sa.Uuid(), sa.ForeignKey("projects.project_id"), nullable=True
        ),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("granted_by", sa.String(256), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "principal_id",
            "scope_type",
            "organization_id",
            "workspace_id",
            "project_id",
            "role",
            name="uq_memberships_grant",
        ),
        sa.CheckConstraint(
            "scope_type IN ('PLATFORM', 'ORGANIZATION', 'WORKSPACE', 'PROJECT')",
            name="ck_memberships_scope_type",
        ),
        sa.CheckConstraint(
            "role IN ('ORG_OWNER', 'ORG_ADMIN', 'WORKSPACE_ADMIN', 'PROJECT_OWNER', "
            "'PROJECT_EDITOR', 'PROJECT_VIEWER', 'PACKAGE_OPERATOR', 'AUDITOR')",
            name="ck_memberships_role",
        ),
        sa.CheckConstraint(
            "state IN ('ACTIVE', 'SUSPENDED', 'REVOKED')", name="ck_memberships_state"
        ),
        sa.CheckConstraint(
            "(scope_type = 'PLATFORM' AND organization_id IS NULL AND workspace_id IS NULL "
            "AND project_id IS NULL) OR "
            "(scope_type = 'ORGANIZATION' AND organization_id IS NOT NULL AND workspace_id IS NULL "
            "AND project_id IS NULL) OR "
            "(scope_type = 'WORKSPACE' AND organization_id IS NULL AND workspace_id IS NOT NULL "
            "AND project_id IS NULL) OR "
            "(scope_type = 'PROJECT' AND organization_id IS NULL AND workspace_id IS NULL "
            "AND project_id IS NOT NULL)",
            name="ck_memberships_exact_scope",
        ),
    )
    op.create_index("ix_memberships_principal_id", "memberships", ["principal_id"])
    op.create_index("ix_memberships_organization_id", "memberships", ["organization_id"])
    op.create_index("ix_memberships_workspace_id", "memberships", ["workspace_id"])
    op.create_index("ix_memberships_project_id", "memberships", ["project_id"])
    op.create_index(
        "ix_memberships_principal_state", "memberships", ["principal_id", "state"]
    )
    for scope_name, scope_column in (
        ("platform", None),
        ("organization", "organization_id"),
        ("workspace", "workspace_id"),
        ("project", "project_id"),
    ):
        columns = ["principal_id", "role"]
        if scope_column is not None:
            columns.insert(1, scope_column)
        predicate = sa.text(f"scope_type = '{scope_name.upper()}'")
        op.create_index(
            f"uq_memberships_{scope_name}_grant",
            "memberships",
            columns,
            unique=True,
            sqlite_where=predicate,
            postgresql_where=predicate,
        )

    op.create_table(
        "project_package_bindings",
        sa.Column("binding_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "project_id", sa.Uuid(), sa.ForeignKey("projects.project_id"), nullable=False
        ),
        sa.Column(
            "installation_id",
            sa.Uuid(),
            sa.ForeignKey("scenario_package_installations.installation_id"),
            nullable=False,
        ),
        sa.Column("package_kind", sa.String(24), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(256), nullable=False),
        sa.Column("updated_by", sa.String(256), nullable=False),
        sa.UniqueConstraint("project_id", "installation_id", name="uq_project_package_binding"),
        sa.CheckConstraint("package_kind IN ('SCENARIO')", name="ck_binding_package_kind"),
        sa.CheckConstraint(
            "state IN ('ACTIVE', 'DISABLED', 'REVOKED')", name="ck_binding_state"
        ),
    )
    op.create_index(
        "ix_project_package_bindings_project_id", "project_package_bindings", ["project_id"]
    )
    op.create_index(
        "ix_project_package_bindings_installation_id",
        "project_package_bindings",
        ["installation_id"],
    )
    op.create_index(
        "ix_project_package_bindings_state", "project_package_bindings", ["state"]
    )

    op.create_table(
        "idempotency_records",
        sa.Column("record_id", sa.Uuid(), primary_key=True),
        sa.Column("actor_ref", sa.String(256), nullable=False),
        sa.Column("action_name", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(32), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("actor_ref", "action_name", "idempotency_key"),
        sa.CheckConstraint(
            "resource_type IN ('ORGANIZATION', 'WORKSPACE', 'PROJECT', 'MEMBERSHIP', "
            "'PROJECT_PACKAGE_BINDING')",
            name="ck_idempotency_resource_type",
        ),
    )

    _seed_local_synthetic_principals()


def _seed_local_synthetic_principals() -> None:
    now = datetime.now(UTC)
    principals = sa.table(
        "principals",
        sa.column("principal_id", sa.Uuid()),
        sa.column("subject_ref", sa.String()),
        sa.column("display_name", sa.String()),
        sa.column("kind", sa.String()),
        sa.column("state", sa.String()),
        sa.column("version", sa.Integer()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
        sa.column("created_by", sa.String()),
        sa.column("updated_by", sa.String()),
    )
    subjects = (
        ("00000000-0000-4000-8000-000000000001", "local-owner", "Local Owner", "ACTIVE"),
        ("00000000-0000-4000-8000-000000000002", "local-editor", "Local Editor", "ACTIVE"),
        ("00000000-0000-4000-8000-000000000003", "local-viewer", "Local Viewer", "ACTIVE"),
        ("00000000-0000-4000-8000-000000000004", "local-outsider", "Local Outsider", "ACTIVE"),
        ("00000000-0000-4000-8000-000000000005", "local-disabled", "Disabled Local User", "DISABLED"),
        (
            "00000000-0000-4000-8000-000000000006",
            "local-integration-owner",
            "Integration Owner",
            "ACTIVE",
        ),
        ("00000000-0000-4000-8000-000000000007", "standalone-smoke", "Smoke Service", "ACTIVE"),
        ("00000000-0000-4000-8000-000000000008", "local-web-shell", "Web Shell", "ACTIVE"),
        ("00000000-0000-4000-8000-000000000009", "local-web-smoke", "Web Smoke", "ACTIVE"),
    )
    op.bulk_insert(
        principals,
        [
            {
                "principal_id": UUID(identifier),
                "subject_ref": subject,
                "display_name": display,
                "kind": "SERVICE" if subject in {"standalone-smoke", "local-web-smoke"} else "USER",
                "state": state,
                "version": 1,
                "created_at": now,
                "updated_at": now,
                "created_by": "migration-0005",
                "updated_by": "migration-0005",
            }
            for identifier, subject, display, state in subjects
        ],
    )
    memberships = sa.table(
        "memberships",
        sa.column("membership_id", sa.Uuid()),
        sa.column("principal_id", sa.Uuid()),
        sa.column("scope_type", sa.String()),
        sa.column("organization_id", sa.Uuid()),
        sa.column("workspace_id", sa.Uuid()),
        sa.column("project_id", sa.Uuid()),
        sa.column("role", sa.String()),
        sa.column("state", sa.String()),
        sa.column("version", sa.Integer()),
        sa.column("granted_by", sa.String()),
        sa.column("granted_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    grants = (
        ("10000000-0000-4000-8000-000000000001", subjects[0][0], "ORG_OWNER"),
        ("10000000-0000-4000-8000-000000000002", subjects[5][0], "PACKAGE_OPERATOR"),
        ("10000000-0000-4000-8000-000000000003", subjects[6][0], "PACKAGE_OPERATOR"),
        ("10000000-0000-4000-8000-000000000004", subjects[7][0], "AUDITOR"),
        ("10000000-0000-4000-8000-000000000005", subjects[8][0], "AUDITOR"),
    )
    op.bulk_insert(
        memberships,
        [
            {
                "membership_id": UUID(membership_id),
                "principal_id": UUID(principal_id),
                "scope_type": "PLATFORM",
                "organization_id": None,
                "workspace_id": None,
                "project_id": None,
                "role": role,
                "state": "ACTIVE",
                "version": 1,
                "granted_by": "migration-0005",
                "granted_at": now,
                "updated_at": now,
            }
            for membership_id, principal_id, role in grants
        ],
    )


def downgrade() -> None:
    op.drop_table("idempotency_records", if_exists=True)
    op.drop_index("ix_project_package_bindings_state", if_exists=True)
    op.drop_index("ix_project_package_bindings_installation_id", if_exists=True)
    op.drop_index("ix_project_package_bindings_project_id", if_exists=True)
    op.drop_table("project_package_bindings", if_exists=True)
    op.drop_index("uq_memberships_project_grant", if_exists=True)
    op.drop_index("uq_memberships_workspace_grant", if_exists=True)
    op.drop_index("uq_memberships_organization_grant", if_exists=True)
    op.drop_index("uq_memberships_platform_grant", if_exists=True)
    op.drop_index("ix_memberships_principal_state")
    op.drop_index("ix_memberships_project_id")
    op.drop_index("ix_memberships_workspace_id")
    op.drop_index("ix_memberships_organization_id")
    op.drop_index("ix_memberships_principal_id")
    op.drop_table("memberships")
    op.drop_index("ix_projects_state")
    op.drop_index("ix_projects_workspace_id")
    op.drop_table("projects")
    op.drop_index("ix_workspaces_state")
    op.drop_index("ix_workspaces_organization_id")
    op.drop_table("workspaces")
    op.drop_index("ix_organizations_state")
    op.drop_index("ix_organizations_slug")
    op.drop_table("organizations")
    op.drop_index("ix_principals_state")
    op.drop_index("ix_principals_subject_ref")
    op.drop_table("principals")
    op.drop_column("audit_events", "policy_version")
    op.drop_column("audit_events", "scope_ref")
