from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import Field

from forgeops.platform_contracts.domain import StrictModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class PrincipalKind(StrEnum):
    USER = "USER"
    SERVICE = "SERVICE"


class PrincipalState(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class OrganizationState(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    ARCHIVED = "ARCHIVED"


class WorkspaceState(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class ProjectState(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class MembershipState(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class BindingState(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    REVOKED = "REVOKED"


class ScopeType(StrEnum):
    PLATFORM = "PLATFORM"
    ORGANIZATION = "ORGANIZATION"
    WORKSPACE = "WORKSPACE"
    PROJECT = "PROJECT"


class Role(StrEnum):
    ORG_OWNER = "ORG_OWNER"
    ORG_ADMIN = "ORG_ADMIN"
    WORKSPACE_ADMIN = "WORKSPACE_ADMIN"
    PROJECT_OWNER = "PROJECT_OWNER"
    PROJECT_EDITOR = "PROJECT_EDITOR"
    PROJECT_VIEWER = "PROJECT_VIEWER"
    PACKAGE_OPERATOR = "PACKAGE_OPERATOR"
    AUDITOR = "AUDITOR"


class PackageKind(StrEnum):
    SCENARIO = "SCENARIO"


class VersionedEntity(StrictModel):
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=utc_now, alias="createdAt")
    updated_at: datetime = Field(default_factory=utc_now, alias="updatedAt")
    created_by: str = Field(alias="createdBy", min_length=1)
    updated_by: str = Field(alias="updatedBy", min_length=1)


class Principal(StrictModel):
    principal_id: UUID = Field(default_factory=uuid4, alias="principalId")
    subject_ref: str = Field(alias="subjectRef", min_length=1, max_length=256)
    display_name: str = Field(alias="displayName", min_length=1, max_length=120)
    kind: PrincipalKind = PrincipalKind.USER
    state: PrincipalState = PrincipalState.ACTIVE
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=utc_now, alias="createdAt")
    updated_at: datetime = Field(default_factory=utc_now, alias="updatedAt")
    created_by: str = Field(alias="createdBy", min_length=1)
    updated_by: str = Field(alias="updatedBy", min_length=1)


class Organization(VersionedEntity):
    organization_id: UUID = Field(default_factory=uuid4, alias="organizationId")
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(pattern=r"^[a-z][a-z0-9-]{2,62}[a-z0-9]$")
    state: OrganizationState = OrganizationState.ACTIVE


class Workspace(VersionedEntity):
    workspace_id: UUID = Field(default_factory=uuid4, alias="workspaceId")
    organization_id: UUID = Field(alias="organizationId")
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(pattern=r"^[a-z][a-z0-9-]{2,62}[a-z0-9]$")
    state: WorkspaceState = WorkspaceState.ACTIVE


class Project(VersionedEntity):
    project_id: UUID = Field(default_factory=uuid4, alias="projectId")
    workspace_id: UUID = Field(alias="workspaceId")
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(pattern=r"^[a-z][a-z0-9-]{2,62}[a-z0-9]$")
    description: str = Field(default="", max_length=1000)
    state: ProjectState = ProjectState.DRAFT


class Membership(StrictModel):
    membership_id: UUID = Field(default_factory=uuid4, alias="membershipId")
    principal_id: UUID = Field(alias="principalId")
    scope_type: ScopeType = Field(alias="scopeType")
    scope_id: UUID | None = Field(alias="scopeId")
    role: Role
    state: MembershipState = MembershipState.ACTIVE
    version: int = Field(default=1, ge=1)
    granted_by: str = Field(alias="grantedBy", min_length=1)
    granted_at: datetime = Field(default_factory=utc_now, alias="grantedAt")
    updated_at: datetime = Field(default_factory=utc_now, alias="updatedAt")


class ProjectPackageBinding(VersionedEntity):
    binding_id: UUID = Field(default_factory=uuid4, alias="bindingId")
    project_id: UUID = Field(alias="projectId")
    installation_id: UUID = Field(alias="installationId")
    package_kind: PackageKind = Field(default=PackageKind.SCENARIO, alias="packageKind")
    state: BindingState = BindingState.ACTIVE


class AuthenticatedPrincipal(StrictModel):
    subject_ref: str = Field(alias="subjectRef", min_length=1)
    authentication_mode: str = Field(default="LOCAL_SYNTHETIC", alias="authenticationMode")


class AuthorizationDecision(StrictModel):
    principal_id: UUID = Field(alias="principalId")
    subject_ref: str = Field(alias="subjectRef")
    action: str
    resource_ref: str = Field(alias="resourceRef")
    scope_type: ScopeType = Field(alias="scopeType")
    scope_id: UUID | None = Field(alias="scopeId")
    allowed: bool
    reason: str
    policy_version: str = Field(default="identity-access-v1", alias="policyVersion")
