from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import Field

from forgeops.platform_contracts.domain import (
    Environment,
    PackageLifecycleState,
    ReleaseState,
    StrictModel,
)
from forgeops.scenario_sdk.manifest import ScenarioManifest


class InstallationRecord(StrictModel):
    installation_id: UUID = Field(default_factory=uuid4, alias="installationId")
    package_id: str = Field(alias="packageId")
    package_version: str = Field(alias="packageVersion")
    content_digest: str = Field(alias="contentDigest")
    manifest: ScenarioManifest
    state: PackageLifecycleState = PackageLifecycleState.INSTALLED_DISABLED
    granted_permissions: tuple[str, ...] = Field(default=(), alias="grantedPermissions")
    binding_refs: tuple[str, ...] = Field(default=(), alias="bindingRefs")
    uninstalled_at: datetime | None = Field(default=None, alias="uninstalledAt")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="createdAt")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="updatedAt")


class EnvironmentReleaseRecord(StrictModel):
    release_id: UUID = Field(default_factory=uuid4, alias="releaseId")
    installation_id: UUID = Field(alias="installationId")
    environment: Environment
    state: ReleaseState = ReleaseState.RELEASED_DISABLED
    action_adapter: str = Field(alias="actionAdapter")
    released_at: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="releasedAt")
