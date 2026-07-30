from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from packaging.version import Version
from sqlalchemy import select
from sqlalchemy.orm import Session

from forgeops.platform_adapters.postgres.models import (
    AuditEventRow,
    EnvironmentReleaseRow,
    InstallationRow,
)
from forgeops.platform_contracts.domain import Environment, PackageLifecycleState, ReleaseState
from forgeops.platform_core.audit import AuditEvent
from forgeops.platform_core.scenario_registry.entities import (
    EnvironmentReleaseRecord,
    InstallationRecord,
)
from forgeops.scenario_sdk.manifest import ScenarioManifest


class SqlInstallationRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def get_by_id(self, installation_id: UUID) -> InstallationRecord | None:
        with self._session_factory() as session:
            return self._installation_record(session.get(InstallationRow, installation_id))

    def get_by_package_version(
        self, package_id: str, package_version: str
    ) -> InstallationRecord | None:
        with self._session_factory() as session:
            row = session.scalar(
                select(InstallationRow).where(
                    InstallationRow.package_id == package_id,
                    InstallationRow.package_version == package_version,
                )
            )
            return self._installation_record(row)

    def latest_for_package(self, package_id: str) -> InstallationRecord | None:
        with self._session_factory() as session:
            records = [
                self._installation_record(row)
                for row in session.scalars(
                    select(InstallationRow).where(InstallationRow.package_id == package_id)
                )
            ]
        present = [record for record in records if record is not None]
        return max(present, key=lambda item: Version(item.package_version), default=None)

    def list_installations(self) -> tuple[InstallationRecord, ...]:
        with self._session_factory() as session:
            records = [
                self._installation_record(row)
                for row in session.scalars(
                    select(InstallationRow).order_by(InstallationRow.created_at)
                )
            ]
        return tuple(record for record in records if record is not None)

    def add(self, record: InstallationRecord) -> InstallationRecord:
        with self._session_factory() as session, session.begin():
            session.add(self._installation_row(record))
        return record

    def save(self, record: InstallationRecord) -> InstallationRecord:
        with self._session_factory() as session, session.begin():
            row = session.get(InstallationRow, record.installation_id)
            if row is None:
                raise LookupError(f"installation not found: {record.installation_id}")
            row.state = record.state.value
            row.granted_permissions = list(record.granted_permissions)
            row.binding_refs = list(record.binding_refs)
            row.uninstalled_at = record.uninstalled_at
            row.updated_at = record.updated_at
        return record

    def get_release(
        self, installation_id: UUID, environment: Environment
    ) -> EnvironmentReleaseRecord | None:
        with self._session_factory() as session:
            row = session.scalar(
                select(EnvironmentReleaseRow).where(
                    EnvironmentReleaseRow.installation_id == installation_id,
                    EnvironmentReleaseRow.environment == environment.value,
                )
            )
            return self._release_record(row)

    def add_release(self, release: EnvironmentReleaseRecord) -> EnvironmentReleaseRecord:
        with self._session_factory() as session, session.begin():
            session.add(self._release_row(release))
        return release

    def save_release(self, release: EnvironmentReleaseRecord) -> EnvironmentReleaseRecord:
        with self._session_factory() as session, session.begin():
            row = session.get(EnvironmentReleaseRow, release.release_id)
            if row is None:
                raise LookupError(f"environment release not found: {release.release_id}")
            row.state = release.state.value
        return release

    @staticmethod
    def _installation_record(row: InstallationRow | None) -> InstallationRecord | None:
        if row is None:
            return None
        return InstallationRecord(
            installation_id=row.installation_id,
            package_id=row.package_id,
            package_version=row.package_version,
            content_digest=row.content_digest,
            manifest=ScenarioManifest.model_validate(row.manifest),
            state=PackageLifecycleState(row.state),
            granted_permissions=tuple(row.granted_permissions),
            binding_refs=tuple(row.binding_refs),
            uninstalled_at=row.uninstalled_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _installation_row(record: InstallationRecord) -> InstallationRow:
        return InstallationRow(
            installation_id=record.installation_id,
            package_id=record.package_id,
            package_version=record.package_version,
            content_digest=record.content_digest,
            manifest=record.manifest.model_dump(mode="json", by_alias=True),
            state=record.state.value,
            granted_permissions=list(record.granted_permissions),
            binding_refs=list(record.binding_refs),
            uninstalled_at=record.uninstalled_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _release_record(row: EnvironmentReleaseRow | None) -> EnvironmentReleaseRecord | None:
        if row is None:
            return None
        return EnvironmentReleaseRecord(
            release_id=row.release_id,
            installation_id=row.installation_id,
            environment=Environment(row.environment),
            state=ReleaseState(row.state),
            action_adapter=row.action_adapter,
            released_at=row.released_at,
        )

    @staticmethod
    def _release_row(record: EnvironmentReleaseRecord) -> EnvironmentReleaseRow:
        return EnvironmentReleaseRow(
            release_id=record.release_id,
            installation_id=record.installation_id,
            environment=record.environment.value,
            state=record.state.value,
            action_adapter=record.action_adapter,
            released_at=record.released_at,
        )


class SqlAuditRepository:
    """Append/list only. No update or delete method exists by design."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def append(self, event: AuditEvent) -> None:
        with self._session_factory() as session, session.begin():
            session.add(
                AuditEventRow(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    actor_ref=event.actor_ref,
                    resource_ref=event.resource_ref,
                    result=event.result,
                    reason_code=event.reason_code,
                    occurred_at=event.occurred_at,
                    trace_id=event.trace_id,
                    requirement_ids=list(event.requirement_ids),
                    test_ids=list(event.test_ids),
                    details=event.details,
                )
            )

    def list_events(self, *, limit: int = 100) -> tuple[AuditEvent, ...]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(AuditEventRow).order_by(AuditEventRow.occurred_at.desc()).limit(limit)
            )
            return tuple(
                AuditEvent(
                    event_id=row.event_id,
                    event_type=row.event_type,
                    actor_ref=row.actor_ref,
                    resource_ref=row.resource_ref,
                    result=row.result,
                    reason_code=row.reason_code,
                    occurred_at=row.occurred_at,
                    trace_id=row.trace_id,
                    requirement_ids=tuple(row.requirement_ids),
                    test_ids=tuple(row.test_ids),
                    details=row.details,
                )
                for row in rows
            )
