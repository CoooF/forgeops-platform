from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class InstallationRow(Base):
    __tablename__ = "scenario_package_installations"
    __table_args__ = (UniqueConstraint("package_id", "package_version"),)

    installation_id: Mapped[UUID] = mapped_column(primary_key=True)
    package_id: Mapped[str] = mapped_column(String(64), index=True)
    package_version: Mapped[str] = mapped_column(String(32))
    content_digest: Mapped[str] = mapped_column(String(80))
    manifest: Mapped[dict[str, object]] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(32), index=True)
    granted_permissions: Mapped[list[str]] = mapped_column(JSON, default=list)
    binding_refs: Mapped[list[str]] = mapped_column(JSON, default=list)
    uninstalled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EnvironmentReleaseRow(Base):
    __tablename__ = "scenario_package_environment_releases"
    __table_args__ = (UniqueConstraint("installation_id", "environment"),)

    release_id: Mapped[UUID] = mapped_column(primary_key=True)
    installation_id: Mapped[UUID] = mapped_column(
        ForeignKey("scenario_package_installations.installation_id"), index=True
    )
    environment: Mapped[str] = mapped_column(String(16))
    state: Mapped[str] = mapped_column(String(32))
    action_adapter: Mapped[str] = mapped_column(String(32))
    released_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    event_id: Mapped[UUID] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    actor_ref: Mapped[str] = mapped_column(String(256))
    resource_ref: Mapped[str] = mapped_column(String(256), index=True)
    result: Mapped[str] = mapped_column(String(32))
    reason_code: Mapped[str] = mapped_column(String(128))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    requirement_ids: Mapped[list[str]] = mapped_column(JSON)
    test_ids: Mapped[list[str]] = mapped_column(JSON)
    details: Mapped[dict[str, object]] = mapped_column(JSON)
    scope_ref: Mapped[str] = mapped_column(String(256), default="platform://local")
    policy_version: Mapped[str] = mapped_column(String(64), default="package-lifecycle-v1")


class PrincipalRow(Base):
    __tablename__ = "principals"
    __table_args__ = (
        CheckConstraint("kind IN ('USER', 'SERVICE')", name="ck_principals_kind"),
        CheckConstraint("state IN ('ACTIVE', 'DISABLED')", name="ck_principals_state"),
    )

    principal_id: Mapped[UUID] = mapped_column(primary_key=True)
    subject_ref: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(16))
    state: Mapped[str] = mapped_column(String(16), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(256))
    updated_by: Mapped[str] = mapped_column(String(256))


class OrganizationRow(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "state IN ('ACTIVE', 'SUSPENDED', 'ARCHIVED')", name="ck_organizations_state"
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    state: Mapped[str] = mapped_column(String(16), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(256))
    updated_by: Mapped[str] = mapped_column(String(256))


class WorkspaceRow(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_workspaces_parent_slug"),
        CheckConstraint("state IN ('ACTIVE', 'ARCHIVED')", name="ck_workspaces_state"),
    )

    workspace_id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.organization_id"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(16), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(256))
    updated_by: Mapped[str] = mapped_column(String(256))


class ProjectRow(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_projects_parent_slug"),
        CheckConstraint("state IN ('DRAFT', 'ACTIVE', 'ARCHIVED')", name="ck_projects_state"),
    )

    project_id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.workspace_id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(String(1000), default="")
    state: Mapped[str] = mapped_column(String(16), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(256))
    updated_by: Mapped[str] = mapped_column(String(256))


class MembershipRow(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint(
            "principal_id",
            "scope_type",
            "organization_id",
            "workspace_id",
            "project_id",
            "role",
            name="uq_memberships_grant",
        ),
        CheckConstraint(
            "scope_type IN ('PLATFORM', 'ORGANIZATION', 'WORKSPACE', 'PROJECT')",
            name="ck_memberships_scope_type",
        ),
        CheckConstraint(
            "role IN ('ORG_OWNER', 'ORG_ADMIN', 'WORKSPACE_ADMIN', 'PROJECT_OWNER', "
            "'PROJECT_EDITOR', 'PROJECT_VIEWER', 'PACKAGE_OPERATOR', 'AUDITOR')",
            name="ck_memberships_role",
        ),
        CheckConstraint("state IN ('ACTIVE', 'SUSPENDED', 'REVOKED')", name="ck_memberships_state"),
        CheckConstraint(
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
        Index("ix_memberships_principal_state", "principal_id", "state"),
        Index(
            "uq_memberships_platform_grant",
            "principal_id",
            "role",
            unique=True,
            sqlite_where=text("scope_type = 'PLATFORM'"),
            postgresql_where=text("scope_type = 'PLATFORM'"),
        ),
        Index(
            "uq_memberships_organization_grant",
            "principal_id",
            "organization_id",
            "role",
            unique=True,
            sqlite_where=text("scope_type = 'ORGANIZATION'"),
            postgresql_where=text("scope_type = 'ORGANIZATION'"),
        ),
        Index(
            "uq_memberships_workspace_grant",
            "principal_id",
            "workspace_id",
            "role",
            unique=True,
            sqlite_where=text("scope_type = 'WORKSPACE'"),
            postgresql_where=text("scope_type = 'WORKSPACE'"),
        ),
        Index(
            "uq_memberships_project_grant",
            "principal_id",
            "project_id",
            "role",
            unique=True,
            sqlite_where=text("scope_type = 'PROJECT'"),
            postgresql_where=text("scope_type = 'PROJECT'"),
        ),
    )

    membership_id: Mapped[UUID] = mapped_column(primary_key=True)
    principal_id: Mapped[UUID] = mapped_column(ForeignKey("principals.principal_id"), index=True)
    scope_type: Mapped[str] = mapped_column(String(16))
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.organization_id"), nullable=True, index=True
    )
    workspace_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("workspaces.workspace_id"), nullable=True, index=True
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("projects.project_id"), nullable=True, index=True
    )
    role: Mapped[str] = mapped_column(String(32))
    state: Mapped[str] = mapped_column(String(16))
    version: Mapped[int] = mapped_column(Integer, default=1)
    granted_by: Mapped[str] = mapped_column(String(256))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProjectPackageBindingRow(Base):
    __tablename__ = "project_package_bindings"
    __table_args__ = (
        UniqueConstraint("project_id", "installation_id", name="uq_project_package_binding"),
        CheckConstraint("package_kind IN ('SCENARIO')", name="ck_binding_package_kind"),
        CheckConstraint("state IN ('ACTIVE', 'DISABLED', 'REVOKED')", name="ck_binding_state"),
    )

    binding_id: Mapped[UUID] = mapped_column(primary_key=True)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.project_id"), index=True)
    installation_id: Mapped[UUID] = mapped_column(
        ForeignKey("scenario_package_installations.installation_id"), index=True
    )
    package_kind: Mapped[str] = mapped_column(String(24))
    state: Mapped[str] = mapped_column(String(16), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(256))
    updated_by: Mapped[str] = mapped_column(String(256))


class IdempotencyRecordRow(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("actor_ref", "action_name", "idempotency_key"),
        CheckConstraint(
            "resource_type IN ('ORGANIZATION', 'WORKSPACE', 'PROJECT', 'MEMBERSHIP', "
            "'PROJECT_PACKAGE_BINDING')",
            name="ck_idempotency_resource_type",
        ),
    )

    record_id: Mapped[UUID] = mapped_column(primary_key=True)
    actor_ref: Mapped[str] = mapped_column(String(256))
    operation: Mapped[str] = mapped_column("action_name", String(64))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    resource_type: Mapped[str] = mapped_column(String(32))
    resource_id: Mapped[UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FdsPackageVersionRow(Base):
    __tablename__ = "fds_package_versions"
    __table_args__ = (
        UniqueConstraint("package_id", "package_version", name="uq_fds_package_version"),
        CheckConstraint(
            "kind IN ('DOMAIN', 'ORGANIZATION_OVERLAY', 'SCENARIO', 'COMPONENT')",
            name="ck_fds_package_versions_kind",
        ),
        CheckConstraint(
            "state IN ('REGISTERED_VALIDATED', 'QUARANTINED', 'WITHDRAWN', "
            "'LOGICALLY_UNINSTALLED')",
            name="ck_fds_package_versions_state",
        ),
        CheckConstraint(
            "(visibility = 'ORGANIZATION_PRIVATE' AND owner_organization_id IS NOT NULL) OR "
            "(visibility <> 'ORGANIZATION_PRIVATE' AND owner_organization_id IS NULL)",
            name="ck_fds_package_versions_owner_scope",
        ),
    )

    package_version_id: Mapped[UUID] = mapped_column(primary_key=True)
    package_id: Mapped[str] = mapped_column(String(128), index=True)
    package_version: Mapped[str] = mapped_column(String(32))
    kind: Mapped[str] = mapped_column(String(32), index=True)
    component_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    manifest: Mapped[dict[str, object]] = mapped_column(JSON)
    normalized_manifest: Mapped[str] = mapped_column(Text)
    manifest_digest: Mapped[str] = mapped_column(String(80), index=True)
    content_digest: Mapped[str] = mapped_column(String(80), index=True)
    artifact_ref: Mapped[str] = mapped_column(String(512))
    sbom_ref: Mapped[str] = mapped_column(String(512))
    signature_ref: Mapped[str] = mapped_column(String(128))
    publisher: Mapped[str] = mapped_column(String(160))
    namespace_owner: Mapped[str] = mapped_column(String(160))
    license_id: Mapped[str] = mapped_column(String(120))
    license_verified: Mapped[bool] = mapped_column(default=False)
    provenance_ref: Mapped[str] = mapped_column(String(512))
    provenance_digest: Mapped[str] = mapped_column(String(80))
    visibility: Mapped[str] = mapped_column(String(32), index=True)
    content_classification: Mapped[str] = mapped_column(String(32))
    trust_tier: Mapped[str] = mapped_column(String(32))
    owner_organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.organization_id"), nullable=True, index=True
    )
    state: Mapped[str] = mapped_column(String(32), index=True)
    governance_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    governed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)


class FdsInstallationRow(Base):
    __tablename__ = "fds_installations"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "root_package_version_id",
            "lock_digest",
            name="uq_fds_installation_lock",
        ),
        CheckConstraint(
            "state IN ('INSTALLED_DISABLED', 'DISABLED', 'REVOKED', 'LOGICALLY_UNINSTALLED')",
            name="ck_fds_installations_state",
        ),
    )

    installation_id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.organization_id"), index=True
    )
    root_package_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("fds_package_versions.package_version_id"), index=True
    )
    root_package_id: Mapped[str] = mapped_column(String(128))
    root_package_version: Mapped[str] = mapped_column(String(32))
    root_kind: Mapped[str] = mapped_column(String(32))
    dependency_lock: Mapped[dict[str, object]] = mapped_column(JSON)
    lock_digest: Mapped[str] = mapped_column(String(80), index=True)
    target_versions: Mapped[dict[str, object]] = mapped_column(JSON)
    include_optional: Mapped[bool]
    requested_permissions: Mapped[list[str]] = mapped_column(JSON)
    permission_delta: Mapped[list[str]] = mapped_column(JSON)
    resource_budget: Mapped[dict[str, object]] = mapped_column(JSON)
    resource_budget_delta: Mapped[dict[str, object]] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(32), index=True)
    governance_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)


class FdsInstallationPackageRefRow(Base):
    __tablename__ = "fds_installation_package_refs"
    __table_args__ = (
        UniqueConstraint(
            "installation_id", "package_version_id", name="uq_fds_installation_package_ref"
        ),
    )

    ref_id: Mapped[UUID] = mapped_column(primary_key=True)
    installation_id: Mapped[UUID] = mapped_column(
        ForeignKey("fds_installations.installation_id"), index=True
    )
    package_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("fds_package_versions.package_version_id"), index=True
    )
    package_id: Mapped[str] = mapped_column(String(128))
    package_version: Mapped[str] = mapped_column(String(32))
    kind: Mapped[str] = mapped_column(String(32))
    component_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    manifest_digest: Mapped[str] = mapped_column(String(80))
    content_digest: Mapped[str] = mapped_column(String(80))


class ProjectDomainLockRow(Base):
    __tablename__ = "project_domain_locks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('CURRENT', 'SUPERSEDED', 'REVOKED')",
            name="ck_project_domain_locks_status",
        ),
        Index(
            "uq_project_domain_locks_current",
            "project_id",
            unique=True,
            sqlite_where=text("status = 'CURRENT'"),
            postgresql_where=text("status = 'CURRENT'"),
        ),
    )

    project_domain_lock_id: Mapped[UUID] = mapped_column(primary_key=True)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.project_id"), index=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.organization_id"), index=True
    )
    installation_id: Mapped[UUID] = mapped_column(
        ForeignKey("fds_installations.installation_id"), index=True
    )
    root_package_id: Mapped[str] = mapped_column(String(128))
    root_package_version: Mapped[str] = mapped_column(String(32))
    root_kind: Mapped[str] = mapped_column(String(32))
    dependency_lock: Mapped[dict[str, object]] = mapped_column(JSON)
    lock_digest: Mapped[str] = mapped_column(String(80), index=True)
    requested_permissions: Mapped[list[str]] = mapped_column(JSON)
    permission_delta: Mapped[list[str]] = mapped_column(JSON)
    resource_budget: Mapped[dict[str, object]] = mapped_column(JSON)
    resource_budget_delta: Mapped[dict[str, object]] = mapped_column(JSON)
    purpose: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(32), index=True)
    previous_lock_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("project_domain_locks.project_domain_lock_id"), nullable=True
    )
    created_by: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)


class ProjectDomainLockPackageRefRow(Base):
    __tablename__ = "project_domain_lock_package_refs"
    __table_args__ = (
        UniqueConstraint(
            "project_domain_lock_id",
            "package_version_id",
            name="uq_project_domain_lock_package_ref",
        ),
    )

    ref_id: Mapped[UUID] = mapped_column(primary_key=True)
    project_domain_lock_id: Mapped[UUID] = mapped_column(
        ForeignKey("project_domain_locks.project_domain_lock_id"), index=True
    )
    package_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("fds_package_versions.package_version_id"), index=True
    )
    package_id: Mapped[str] = mapped_column(String(128))
    package_version: Mapped[str] = mapped_column(String(32))
    kind: Mapped[str] = mapped_column(String(32))
    component_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    manifest_digest: Mapped[str] = mapped_column(String(80))
    content_digest: Mapped[str] = mapped_column(String(80))


class FdsIdempotencyRecordRow(Base):
    __tablename__ = "fds_idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "actor_ref", "action_key", "idempotency_key", name="uq_fds_idempotency_key"
        ),
    )

    record_id: Mapped[UUID] = mapped_column(primary_key=True)
    actor_ref: Mapped[str] = mapped_column(String(256))
    action_key: Mapped[str] = mapped_column(String(80))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_digest: Mapped[str] = mapped_column(String(80))
    resource_type: Mapped[str] = mapped_column(String(40))
    resource_id: Mapped[UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SemanticPayloadRow(Base):
    __tablename__ = "semantic_payloads"
    __table_args__ = (
        UniqueConstraint("package_version_id", name="uq_semantic_payload_package_version"),
        CheckConstraint(
            "payload_kind IN ('ONTOLOGY', 'TERMINOLOGY', 'DATA_MAPPING')",
            name="ck_semantic_payload_kind",
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'VALIDATED_LOCAL_SYNTHETIC', "
            "'PUBLISHED_LOCAL_SYNTHETIC', 'WITHDRAWN')",
            name="ck_semantic_payload_status",
        ),
    )

    semantic_payload_id: Mapped[UUID] = mapped_column(primary_key=True)
    package_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("fds_package_versions.package_version_id"), index=True
    )
    package_id: Mapped[str] = mapped_column(String(128), index=True)
    package_version: Mapped[str] = mapped_column(String(32))
    payload_kind: Mapped[str] = mapped_column(String(32), index=True)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.organization_id"), nullable=True, index=True
    )
    definition: Mapped[dict[str, object]] = mapped_column(JSON)
    canonical_payload: Mapped[str] = mapped_column(Text)
    payload_digest: Mapped[str] = mapped_column(String(80), index=True)
    provenance_ref: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(48), index=True)
    governance_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    governed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)


class KnowledgeAssetRow(Base):
    __tablename__ = "knowledge_assets"

    asset_id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.organization_id"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(2000))
    asset_type: Mapped[str] = mapped_column(String(32))
    language: Mapped[str] = mapped_column(String(16))
    owner: Mapped[str] = mapped_column(String(160))
    reviewer: Mapped[str] = mapped_column(String(160))
    created_by: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)


class KnowledgeAssetVersionRow(Base):
    __tablename__ = "knowledge_asset_versions"
    __table_args__ = (
        UniqueConstraint("asset_id", "version_label", name="uq_knowledge_asset_version"),
        UniqueConstraint("package_version_id", name="uq_knowledge_package_version"),
        CheckConstraint(
            "status IN ('DRAFT', 'VALIDATED_LOCAL_SYNTHETIC', "
            "'PUBLISHED_LOCAL_SYNTHETIC', 'WITHDRAWN')",
            name="ck_knowledge_version_status",
        ),
    )

    knowledge_version_id: Mapped[UUID] = mapped_column(primary_key=True)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("knowledge_assets.asset_id"), index=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.organization_id"), index=True
    )
    package_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("fds_package_versions.package_version_id"), index=True
    )
    package_id: Mapped[str] = mapped_column(String(128), index=True)
    package_version: Mapped[str] = mapped_column(String(32))
    version_label: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(2000))
    asset_type: Mapped[str] = mapped_column(String(32))
    language: Mapped[str] = mapped_column(String(16))
    owner: Mapped[str] = mapped_column(String(160))
    reviewer: Mapped[str] = mapped_column(String(160))
    source_ref: Mapped[str] = mapped_column(String(512))
    provenance_digest: Mapped[str] = mapped_column(String(80))
    license_id: Mapped[str] = mapped_column(String(120))
    license_terms: Mapped[str] = mapped_column(String(1000))
    content_classification: Mapped[str] = mapped_column(String(48), index=True)
    allowed_purposes: Mapped[list[str]] = mapped_column(JSON)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(48), index=True)
    content_ref: Mapped[str] = mapped_column(String(96))
    content_type: Mapped[str] = mapped_column(String(48))
    size_bytes: Mapped[int] = mapped_column(Integer)
    content_digest: Mapped[str] = mapped_column(String(80), index=True)
    withdrawal_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)


class ContextManifestRow(Base):
    __tablename__ = "context_manifests"
    __table_args__ = (
        UniqueConstraint("actor_ref", "request_digest", name="uq_context_actor_request"),
    )

    context_manifest_id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.organization_id"), index=True
    )
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.project_id"), index=True)
    actor_ref: Mapped[str] = mapped_column(String(256), index=True)
    purpose: Mapped[str] = mapped_column(String(120))
    project_domain_lock_id: Mapped[UUID] = mapped_column(
        ForeignKey("project_domain_locks.project_domain_lock_id"), index=True
    )
    domain_lock_digest: Mapped[str] = mapped_column(String(80))
    request_digest: Mapped[str] = mapped_column(String(80), index=True)
    manifest_json: Mapped[dict[str, object]] = mapped_column(JSON)
    canonical_digest: Mapped[str] = mapped_column(String(80), index=True)
    compiled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class GroundingResultRow(Base):
    __tablename__ = "grounding_results"

    grounding_result_id: Mapped[UUID] = mapped_column(primary_key=True)
    context_manifest_id: Mapped[UUID] = mapped_column(
        ForeignKey("context_manifests.context_manifest_id"), index=True
    )
    result_json: Mapped[dict[str, object]] = mapped_column(JSON)
    digest: Mapped[str] = mapped_column(String(80), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class SemanticImpactReportRow(Base):
    __tablename__ = "semantic_impact_reports"

    impact_report_id: Mapped[UUID] = mapped_column(primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(24), index=True)
    from_ref: Mapped[str] = mapped_column(String(160), index=True)
    to_ref: Mapped[str] = mapped_column(String(160), index=True)
    report_json: Mapped[dict[str, object]] = mapped_column(JSON)
    digest: Mapped[str] = mapped_column(String(80), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class SemanticIdempotencyRecordRow(Base):
    __tablename__ = "semantic_idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "actor_ref", "action_key", "idempotency_key", name="uq_semantic_idempotency_key"
        ),
    )

    record_id: Mapped[UUID] = mapped_column(primary_key=True)
    actor_ref: Mapped[str] = mapped_column(String(256))
    action_key: Mapped[str] = mapped_column(String(80))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_digest: Mapped[str] = mapped_column(String(80))
    resource_type: Mapped[str] = mapped_column(String(48))
    resource_id: Mapped[UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
