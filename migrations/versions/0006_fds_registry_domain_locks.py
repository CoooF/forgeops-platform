"""REQ-FDS-001: FDS Registry, Organization installation, and Project DomainLock."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fds_package_versions",
        sa.Column("package_version_id", sa.Uuid(), primary_key=True),
        sa.Column("package_id", sa.String(128), nullable=False),
        sa.Column("package_version", sa.String(32), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("component_kind", sa.String(32), nullable=True),
        sa.Column("manifest", sa.JSON(), nullable=False),
        sa.Column("normalized_manifest", sa.Text(), nullable=False),
        sa.Column("manifest_digest", sa.String(80), nullable=False),
        sa.Column("content_digest", sa.String(80), nullable=False),
        sa.Column("artifact_ref", sa.String(512), nullable=False),
        sa.Column("sbom_ref", sa.String(512), nullable=False),
        sa.Column("signature_ref", sa.String(128), nullable=False),
        sa.Column("publisher", sa.String(160), nullable=False),
        sa.Column("namespace_owner", sa.String(160), nullable=False),
        sa.Column("license_id", sa.String(120), nullable=False),
        sa.Column("license_verified", sa.Boolean(), nullable=False),
        sa.Column("provenance_ref", sa.String(512), nullable=False),
        sa.Column("provenance_digest", sa.String(80), nullable=False),
        sa.Column("visibility", sa.String(32), nullable=False),
        sa.Column("content_classification", sa.String(32), nullable=False),
        sa.Column("trust_tier", sa.String(32), nullable=False),
        sa.Column(
            "owner_organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.organization_id"),
            nullable=True,
        ),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("governance_reason", sa.String(500), nullable=True),
        sa.Column("governed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.UniqueConstraint("package_id", "package_version", name="uq_fds_package_version"),
        sa.CheckConstraint(
            "kind IN ('DOMAIN', 'ORGANIZATION_OVERLAY', 'SCENARIO', 'COMPONENT')",
            name="ck_fds_package_versions_kind",
        ),
        sa.CheckConstraint(
            "state IN ('REGISTERED_VALIDATED', 'QUARANTINED', 'WITHDRAWN', "
            "'LOGICALLY_UNINSTALLED')",
            name="ck_fds_package_versions_state",
        ),
        sa.CheckConstraint(
            "(visibility = 'ORGANIZATION_PRIVATE' AND owner_organization_id IS NOT NULL) OR "
            "(visibility <> 'ORGANIZATION_PRIVATE' AND owner_organization_id IS NULL)",
            name="ck_fds_package_versions_owner_scope",
        ),
    )
    for name, columns in (
        ("ix_fds_package_versions_package_id", ["package_id"]),
        ("ix_fds_package_versions_kind", ["kind"]),
        ("ix_fds_package_versions_manifest_digest", ["manifest_digest"]),
        ("ix_fds_package_versions_content_digest", ["content_digest"]),
        ("ix_fds_package_versions_visibility", ["visibility"]),
        ("ix_fds_package_versions_owner_organization_id", ["owner_organization_id"]),
        ("ix_fds_package_versions_state", ["state"]),
    ):
        op.create_index(name, "fds_package_versions", columns)

    op.create_table(
        "fds_installations",
        sa.Column("installation_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.organization_id"),
            nullable=False,
        ),
        sa.Column(
            "root_package_version_id",
            sa.Uuid(),
            sa.ForeignKey("fds_package_versions.package_version_id"),
            nullable=False,
        ),
        sa.Column("root_package_id", sa.String(128), nullable=False),
        sa.Column("root_package_version", sa.String(32), nullable=False),
        sa.Column("root_kind", sa.String(32), nullable=False),
        sa.Column("dependency_lock", sa.JSON(), nullable=False),
        sa.Column("lock_digest", sa.String(80), nullable=False),
        sa.Column("target_versions", sa.JSON(), nullable=False),
        sa.Column("include_optional", sa.Boolean(), nullable=False),
        sa.Column("requested_permissions", sa.JSON(), nullable=False),
        sa.Column("permission_delta", sa.JSON(), nullable=False),
        sa.Column("resource_budget", sa.JSON(), nullable=False),
        sa.Column("resource_budget_delta", sa.JSON(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("governance_reason", sa.String(500), nullable=True),
        sa.Column("created_by", sa.String(256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "organization_id",
            "root_package_version_id",
            "lock_digest",
            name="uq_fds_installation_lock",
        ),
        sa.CheckConstraint(
            "state IN ('INSTALLED_DISABLED', 'DISABLED', 'REVOKED', 'LOGICALLY_UNINSTALLED')",
            name="ck_fds_installations_state",
        ),
    )
    for name, columns in (
        ("ix_fds_installations_organization_id", ["organization_id"]),
        ("ix_fds_installations_root_package_version_id", ["root_package_version_id"]),
        ("ix_fds_installations_lock_digest", ["lock_digest"]),
        ("ix_fds_installations_state", ["state"]),
    ):
        op.create_index(name, "fds_installations", columns)

    op.create_table(
        "fds_installation_package_refs",
        sa.Column("ref_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "installation_id",
            sa.Uuid(),
            sa.ForeignKey("fds_installations.installation_id"),
            nullable=False,
        ),
        sa.Column(
            "package_version_id",
            sa.Uuid(),
            sa.ForeignKey("fds_package_versions.package_version_id"),
            nullable=False,
        ),
        sa.Column("package_id", sa.String(128), nullable=False),
        sa.Column("package_version", sa.String(32), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("component_kind", sa.String(32), nullable=True),
        sa.Column("manifest_digest", sa.String(80), nullable=False),
        sa.Column("content_digest", sa.String(80), nullable=False),
        sa.UniqueConstraint(
            "installation_id", "package_version_id", name="uq_fds_installation_package_ref"
        ),
    )
    op.create_index(
        "ix_fds_installation_package_refs_installation_id",
        "fds_installation_package_refs",
        ["installation_id"],
    )
    op.create_index(
        "ix_fds_installation_package_refs_package_version_id",
        "fds_installation_package_refs",
        ["package_version_id"],
    )

    op.create_table(
        "project_domain_locks",
        sa.Column("project_domain_lock_id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.project_id"), nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.organization_id"),
            nullable=False,
        ),
        sa.Column(
            "installation_id",
            sa.Uuid(),
            sa.ForeignKey("fds_installations.installation_id"),
            nullable=False,
        ),
        sa.Column("root_package_id", sa.String(128), nullable=False),
        sa.Column("root_package_version", sa.String(32), nullable=False),
        sa.Column("root_kind", sa.String(32), nullable=False),
        sa.Column("dependency_lock", sa.JSON(), nullable=False),
        sa.Column("lock_digest", sa.String(80), nullable=False),
        sa.Column("requested_permissions", sa.JSON(), nullable=False),
        sa.Column("permission_delta", sa.JSON(), nullable=False),
        sa.Column("resource_budget", sa.JSON(), nullable=False),
        sa.Column("resource_budget_delta", sa.JSON(), nullable=False),
        sa.Column("purpose", sa.String(500), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column(
            "previous_lock_id",
            sa.Uuid(),
            sa.ForeignKey("project_domain_locks.project_domain_lock_id"),
            nullable=True,
        ),
        sa.Column("created_by", sa.String(256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "status IN ('CURRENT', 'SUPERSEDED', 'REVOKED')",
            name="ck_project_domain_locks_status",
        ),
    )
    for name, columns in (
        ("ix_project_domain_locks_project_id", ["project_id"]),
        ("ix_project_domain_locks_organization_id", ["organization_id"]),
        ("ix_project_domain_locks_installation_id", ["installation_id"]),
        ("ix_project_domain_locks_lock_digest", ["lock_digest"]),
        ("ix_project_domain_locks_status", ["status"]),
    ):
        op.create_index(name, "project_domain_locks", columns)
    current_predicate = sa.text("status = 'CURRENT'")
    op.create_index(
        "uq_project_domain_locks_current",
        "project_domain_locks",
        ["project_id"],
        unique=True,
        sqlite_where=current_predicate,
        postgresql_where=current_predicate,
    )

    op.create_table(
        "project_domain_lock_package_refs",
        sa.Column("ref_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "project_domain_lock_id",
            sa.Uuid(),
            sa.ForeignKey("project_domain_locks.project_domain_lock_id"),
            nullable=False,
        ),
        sa.Column(
            "package_version_id",
            sa.Uuid(),
            sa.ForeignKey("fds_package_versions.package_version_id"),
            nullable=False,
        ),
        sa.Column("package_id", sa.String(128), nullable=False),
        sa.Column("package_version", sa.String(32), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("component_kind", sa.String(32), nullable=True),
        sa.Column("manifest_digest", sa.String(80), nullable=False),
        sa.Column("content_digest", sa.String(80), nullable=False),
        sa.UniqueConstraint(
            "project_domain_lock_id",
            "package_version_id",
            name="uq_project_domain_lock_package_ref",
        ),
    )
    op.create_index(
        "ix_project_domain_lock_package_refs_project_domain_lock_id",
        "project_domain_lock_package_refs",
        ["project_domain_lock_id"],
    )
    op.create_index(
        "ix_project_domain_lock_package_refs_package_version_id",
        "project_domain_lock_package_refs",
        ["package_version_id"],
    )

    op.create_table(
        "fds_idempotency_records",
        sa.Column("record_id", sa.Uuid(), primary_key=True),
        sa.Column("actor_ref", sa.String(256), nullable=False),
        sa.Column("action_key", sa.String(80), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_digest", sa.String(80), nullable=False),
        sa.Column("resource_type", sa.String(40), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "actor_ref", "action_key", "idempotency_key", name="uq_fds_idempotency_key"
        ),
    )


def downgrade() -> None:
    op.drop_table("fds_idempotency_records")
    op.drop_index("ix_project_domain_lock_package_refs_package_version_id")
    op.drop_index("ix_project_domain_lock_package_refs_project_domain_lock_id")
    op.drop_table("project_domain_lock_package_refs")
    op.drop_index("uq_project_domain_locks_current")
    op.drop_index("ix_project_domain_locks_status")
    op.drop_index("ix_project_domain_locks_lock_digest")
    op.drop_index("ix_project_domain_locks_installation_id")
    op.drop_index("ix_project_domain_locks_organization_id")
    op.drop_index("ix_project_domain_locks_project_id")
    op.drop_table("project_domain_locks")
    op.drop_index("ix_fds_installation_package_refs_package_version_id")
    op.drop_index("ix_fds_installation_package_refs_installation_id")
    op.drop_table("fds_installation_package_refs")
    op.drop_index("ix_fds_installations_state")
    op.drop_index("ix_fds_installations_lock_digest")
    op.drop_index("ix_fds_installations_root_package_version_id")
    op.drop_index("ix_fds_installations_organization_id")
    op.drop_table("fds_installations")
    op.drop_index("ix_fds_package_versions_state")
    op.drop_index("ix_fds_package_versions_owner_organization_id")
    op.drop_index("ix_fds_package_versions_visibility")
    op.drop_index("ix_fds_package_versions_content_digest")
    op.drop_index("ix_fds_package_versions_manifest_digest")
    op.drop_index("ix_fds_package_versions_kind")
    op.drop_index("ix_fds_package_versions_package_id")
    op.drop_table("fds_package_versions")
