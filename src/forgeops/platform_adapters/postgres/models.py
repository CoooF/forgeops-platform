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
