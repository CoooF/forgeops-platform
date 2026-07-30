from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from packaging.version import Version

from forgeops.platform_contracts.domain import Environment, PackageLifecycleState, ReleaseState
from forgeops.platform_core.scenario_registry.entities import (
    EnvironmentReleaseRecord,
    InstallationRecord,
)


class InstallationRepository(Protocol):
    def get_by_id(self, installation_id: UUID) -> InstallationRecord | None: ...

    def get_by_package_version(
        self, package_id: str, package_version: str
    ) -> InstallationRecord | None: ...

    def latest_for_package(self, package_id: str) -> InstallationRecord | None: ...

    def list_installations(self) -> tuple[InstallationRecord, ...]: ...

    def add(self, record: InstallationRecord) -> InstallationRecord: ...

    def save(self, record: InstallationRecord) -> InstallationRecord: ...

    def get_release(
        self, installation_id: UUID, environment: Environment
    ) -> EnvironmentReleaseRecord | None: ...

    def add_release(self, release: EnvironmentReleaseRecord) -> EnvironmentReleaseRecord: ...

    def save_release(self, release: EnvironmentReleaseRecord) -> EnvironmentReleaseRecord: ...


class InMemoryInstallationRepository:
    def __init__(self) -> None:
        self._records: dict[UUID, InstallationRecord] = {}
        self._releases: dict[tuple[UUID, Environment], EnvironmentReleaseRecord] = {}

    def get_by_id(self, installation_id: UUID) -> InstallationRecord | None:
        return self._records.get(installation_id)

    def get_by_package_version(
        self, package_id: str, package_version: str
    ) -> InstallationRecord | None:
        return next(
            (
                record
                for record in self._records.values()
                if record.package_id == package_id and record.package_version == package_version
            ),
            None,
        )

    def latest_for_package(self, package_id: str) -> InstallationRecord | None:
        matches = [x for x in self._records.values() if x.package_id == package_id]
        return max(matches, key=lambda item: Version(item.package_version), default=None)

    def list_installations(self) -> tuple[InstallationRecord, ...]:
        return tuple(sorted(self._records.values(), key=lambda item: item.created_at))

    def add(self, record: InstallationRecord) -> InstallationRecord:
        self._records[record.installation_id] = record
        return record

    def save(self, record: InstallationRecord) -> InstallationRecord:
        updated = record.model_copy(update={"updated_at": datetime.now(UTC)})
        self._records[updated.installation_id] = updated
        return updated

    def get_release(
        self, installation_id: UUID, environment: Environment
    ) -> EnvironmentReleaseRecord | None:
        return self._releases.get((installation_id, environment))

    def add_release(self, release: EnvironmentReleaseRecord) -> EnvironmentReleaseRecord:
        self._releases[(release.installation_id, release.environment)] = release
        return release

    def save_release(self, release: EnvironmentReleaseRecord) -> EnvironmentReleaseRecord:
        self._releases[(release.installation_id, release.environment)] = release
        return release


def changed_state(record: InstallationRecord, state: PackageLifecycleState) -> InstallationRecord:
    return record.model_copy(update={"state": state})


def changed_release_state(
    record: EnvironmentReleaseRecord, state: ReleaseState
) -> EnvironmentReleaseRecord:
    return record.model_copy(update={"state": state})
