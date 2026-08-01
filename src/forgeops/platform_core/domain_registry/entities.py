from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field

from forgeops.fds_sdk.models import (
    ComponentKind,
    ContentClassification,
    DependencyLock,
    FdsManifest,
    PackageKind,
    RequestedResourceBudget,
    TargetVersions,
    TrustTier,
    Visibility,
)
from forgeops.platform_contracts.domain import StrictModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class RegistryState(StrEnum):
    REGISTERED_VALIDATED = "REGISTERED_VALIDATED"
    QUARANTINED = "QUARANTINED"
    WITHDRAWN = "WITHDRAWN"
    LOGICALLY_UNINSTALLED = "LOGICALLY_UNINSTALLED"


class DomainInstallationState(StrEnum):
    INSTALLED_DISABLED = "INSTALLED_DISABLED"
    DISABLED = "DISABLED"
    REVOKED = "REVOKED"
    LOGICALLY_UNINSTALLED = "LOGICALLY_UNINSTALLED"


class ProjectDomainLockState(StrEnum):
    CURRENT = "CURRENT"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"


class DerivedHealth(StrEnum):
    HEALTHY_FOR_SELECTION = "HEALTHY_FOR_SELECTION"
    AT_RISK = "AT_RISK"
    BLOCKED_FOR_NEW_USE = "BLOCKED_FOR_NEW_USE"


def registry_transition_allowed(current: RegistryState, target: RegistryState) -> bool:
    """Return whether a non-idempotent Registry governance transition is legal."""
    allowed = {
        RegistryState.REGISTERED_VALIDATED: {
            RegistryState.QUARANTINED,
            RegistryState.WITHDRAWN,
        },
        RegistryState.QUARANTINED: {RegistryState.WITHDRAWN},
        RegistryState.WITHDRAWN: set(),
        RegistryState.LOGICALLY_UNINSTALLED: set(),
    }
    return target in allowed[current]


def installation_transition_allowed(
    current: DomainInstallationState, target: DomainInstallationState
) -> bool:
    """Return whether a non-idempotent Installation governance transition is legal."""
    allowed = {
        DomainInstallationState.INSTALLED_DISABLED: {
            DomainInstallationState.DISABLED,
            DomainInstallationState.REVOKED,
        },
        DomainInstallationState.DISABLED: {
            DomainInstallationState.REVOKED,
            DomainInstallationState.LOGICALLY_UNINSTALLED,
        },
        DomainInstallationState.REVOKED: {DomainInstallationState.LOGICALLY_UNINSTALLED},
        DomainInstallationState.LOGICALLY_UNINSTALLED: set(),
    }
    return target in allowed[current]


class PackageVersionRef(StrictModel):
    package_version_id: UUID = Field(alias="packageVersionId")
    package_id: str = Field(alias="packageId")
    package_version: str = Field(alias="packageVersion")
    kind: PackageKind
    component_kind: ComponentKind | None = Field(default=None, alias="componentKind")
    manifest_digest: str = Field(alias="manifestDigest")
    content_digest: str = Field(alias="contentDigest")


class FdsPackageVersionRecord(StrictModel):
    package_version_id: UUID = Field(default_factory=uuid4, alias="packageVersionId")
    package_id: str = Field(alias="packageId")
    package_version: str = Field(alias="packageVersion")
    kind: PackageKind
    component_kind: ComponentKind | None = Field(default=None, alias="componentKind")
    manifest: FdsManifest
    normalized_manifest: str = Field(alias="normalizedManifest")
    manifest_digest: str = Field(alias="manifestDigest")
    content_digest: str = Field(alias="contentDigest")
    artifact_ref: str = Field(alias="artifactRef")
    sbom_ref: str = Field(alias="sbomRef")
    signature_ref: str = Field(alias="signatureRef")
    publisher: str
    namespace_owner: str = Field(alias="namespaceOwner")
    license_id: str = Field(alias="licenseId")
    license_verified: bool = Field(alias="licenseVerified")
    provenance_ref: str = Field(alias="provenanceRef")
    provenance_digest: str = Field(alias="provenanceDigest")
    visibility: Visibility
    content_classification: ContentClassification = Field(alias="contentClassification")
    trust_tier: TrustTier = Field(alias="trustTier")
    owner_organization_id: UUID | None = Field(default=None, alias="ownerOrganizationId")
    state: RegistryState = RegistryState.REGISTERED_VALIDATED
    governance_reason: str | None = Field(default=None, alias="governanceReason")
    governed_at: datetime | None = Field(default=None, alias="governedAt")
    created_by: str = Field(alias="createdBy")
    created_at: datetime = Field(default_factory=utc_now, alias="createdAt")
    updated_at: datetime = Field(default_factory=utc_now, alias="updatedAt")
    version: int = Field(default=1, ge=1)

    def package_ref(self) -> PackageVersionRef:
        return PackageVersionRef(
            package_version_id=self.package_version_id,
            package_id=self.package_id,
            package_version=self.package_version,
            kind=self.kind,
            component_kind=self.component_kind,
            manifest_digest=self.manifest_digest,
            content_digest=self.content_digest,
        )


class FdsInstallation(StrictModel):
    installation_id: UUID = Field(default_factory=uuid4, alias="installationId")
    organization_id: UUID = Field(alias="organizationId")
    root_package_version_id: UUID = Field(alias="rootPackageVersionId")
    root_package_id: str = Field(alias="rootPackageId")
    root_package_version: str = Field(alias="rootPackageVersion")
    root_kind: PackageKind = Field(alias="rootKind")
    dependency_lock: DependencyLock = Field(alias="dependencyLock")
    lock_digest: str = Field(alias="lockDigest")
    target_versions: TargetVersions = Field(alias="targetVersions")
    include_optional: bool = Field(alias="includeOptional")
    package_version_refs: tuple[PackageVersionRef, ...] = Field(alias="packageVersionRefs")
    requested_permissions: tuple[str, ...] = Field(alias="requestedPermissions")
    permission_delta: tuple[str, ...] = Field(alias="permissionDelta")
    resource_budget: RequestedResourceBudget = Field(alias="resourceBudget")
    resource_budget_delta: RequestedResourceBudget = Field(alias="resourceBudgetDelta")
    state: DomainInstallationState = DomainInstallationState.INSTALLED_DISABLED
    authorization_effect: Literal["NONE"] = Field(default="NONE", alias="authorizationEffect")
    runtime_state_created: Literal[False] = Field(default=False, alias="runtimeStateCreated")
    semantic_runtime_ready: Literal[False] = Field(default=False, alias="semanticRuntimeReady")
    governance_reason: str | None = Field(default=None, alias="governanceReason")
    created_by: str = Field(alias="createdBy")
    created_at: datetime = Field(default_factory=utc_now, alias="createdAt")
    updated_at: datetime = Field(default_factory=utc_now, alias="updatedAt")
    version: int = Field(default=1, ge=1)


class ProjectDomainLock(StrictModel):
    project_domain_lock_id: UUID = Field(default_factory=uuid4, alias="projectDomainLockId")
    project_id: UUID = Field(alias="projectId")
    organization_id: UUID = Field(alias="organizationId")
    installation_id: UUID = Field(alias="installationId")
    root_package_id: str = Field(alias="rootPackageId")
    root_package_version: str = Field(alias="rootPackageVersion")
    root_kind: PackageKind = Field(alias="rootKind")
    dependency_lock: DependencyLock = Field(alias="dependencyLock")
    lock_digest: str = Field(alias="lockDigest")
    package_version_refs: tuple[PackageVersionRef, ...] = Field(alias="packageVersionRefs")
    requested_permissions: tuple[str, ...] = Field(alias="requestedPermissions")
    permission_delta: tuple[str, ...] = Field(alias="permissionDelta")
    resource_budget: RequestedResourceBudget = Field(alias="resourceBudget")
    resource_budget_delta: RequestedResourceBudget = Field(alias="resourceBudgetDelta")
    purpose: str = Field(min_length=1, max_length=500)
    status: ProjectDomainLockState = ProjectDomainLockState.CURRENT
    previous_lock_id: UUID | None = Field(default=None, alias="previousLockId")
    runtime_binding_created: Literal[False] = Field(default=False, alias="runtimeBindingCreated")
    authorization_effect: Literal["NONE"] = Field(default="NONE", alias="authorizationEffect")
    semantic_runtime_ready: Literal[False] = Field(default=False, alias="semanticRuntimeReady")
    created_by: str = Field(alias="createdBy")
    created_at: datetime = Field(default_factory=utc_now, alias="createdAt")
    version: int = Field(default=1, ge=1)


class HealthSummary(StrictModel):
    health: DerivedHealth
    reasons: tuple[str, ...] = ()


class InstallationImpact(StrictModel):
    installation_id: UUID = Field(alias="installationId")
    organization_id: UUID = Field(alias="organizationId")
    root_package_id: str = Field(alias="rootPackageId")
    state: DomainInstallationState


class DomainLockImpact(StrictModel):
    project_domain_lock_id: UUID = Field(alias="projectDomainLockId")
    project_id: UUID = Field(alias="projectId")
    organization_id: UUID = Field(alias="organizationId")
    status: ProjectDomainLockState


class PackageImpactReport(StrictModel):
    package_version_id: UUID = Field(alias="packageVersionId")
    package_id: str = Field(alias="packageId")
    package_version: str = Field(alias="packageVersion")
    registry_state: RegistryState = Field(alias="registryState")
    installations: tuple[InstallationImpact, ...]
    project_domain_locks: tuple[DomainLockImpact, ...] = Field(alias="projectDomainLocks")


class PackageChange(StrictModel):
    package_id: str = Field(alias="packageId")
    from_version: str | None = Field(default=None, alias="fromVersion")
    to_version: str | None = Field(default=None, alias="toVersion")
    from_digest: str | None = Field(default=None, alias="fromDigest")
    to_digest: str | None = Field(default=None, alias="toDigest")


class DomainLockDiff(StrictModel):
    from_installation_id: UUID = Field(alias="fromInstallationId")
    to_installation_id: UUID = Field(alias="toInstallationId")
    added: tuple[PackageChange, ...]
    removed: tuple[PackageChange, ...]
    changed: tuple[PackageChange, ...]
    permissions_added: tuple[str, ...] = Field(alias="permissionsAdded")
    permissions_removed: tuple[str, ...] = Field(alias="permissionsRemoved")
    budget_delta: dict[str, int | bool] = Field(alias="budgetDelta")
    visibility_trust_changes: tuple[str, ...] = Field(alias="visibilityTrustChanges")
    semantic_difference_status: Literal["NOT_EVALUATED"] = Field(
        default="NOT_EVALUATED", alias="semanticDifferenceStatus"
    )
