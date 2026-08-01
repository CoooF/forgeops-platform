from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from forgeops.fds_sdk.models import (
    FDS_MANIFEST_ADAPTER,
    DependencyLock,
    RequestedResourceBudget,
    TargetVersions,
)
from forgeops.platform_adapters.postgres.models import (
    AuditEventRow,
    FdsIdempotencyRecordRow,
    FdsInstallationPackageRefRow,
    FdsInstallationRow,
    FdsPackageVersionRow,
    ProjectDomainLockPackageRefRow,
    ProjectDomainLockRow,
)
from forgeops.platform_contracts.errors import ErrorCode, ForgeOpsError
from forgeops.platform_core.audit import AuditEvent
from forgeops.platform_core.domain_registry.entities import (
    DomainInstallationState,
    FdsInstallation,
    FdsPackageVersionRecord,
    PackageVersionRef,
    ProjectDomainLock,
    ProjectDomainLockState,
    RegistryState,
)


class SqlDomainRegistryRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def find_idempotent_resource(
        self,
        actor_ref: str,
        operation: str,
        idempotency_key: str,
        request_digest: str,
    ) -> tuple[str, UUID] | None:
        with self._session_factory() as session:
            replay = self._find_replay(
                session, actor_ref, operation, idempotency_key, request_digest
            )
            return (replay.resource_type, replay.resource_id) if replay is not None else None

    def bind_idempotent_resource(
        self,
        actor_ref: str,
        operation: str,
        idempotency_key: str,
        request_digest: str,
        resource_type: str,
        resource_id: UUID,
    ) -> None:
        with self._session_factory() as session, session.begin():
            replay = self._find_replay(
                session, actor_ref, operation, idempotency_key, request_digest
            )
            if replay is not None:
                if replay.resource_type != resource_type or replay.resource_id != resource_id:
                    raise self._idempotency_corrupt()
                return
            self._add_idempotency(
                session,
                actor_ref,
                operation,
                idempotency_key,
                request_digest,
                resource_type,
                resource_id,
            )
            self._flush(session)

    def get_package_version(self, package_version_id: UUID) -> FdsPackageVersionRecord | None:
        with self._session_factory() as session:
            return self._package_record(session.get(FdsPackageVersionRow, package_version_id))

    def get_package_version_by_identity(
        self, package_id: str, package_version: str
    ) -> FdsPackageVersionRecord | None:
        with self._session_factory() as session:
            row = session.scalar(
                select(FdsPackageVersionRow).where(
                    FdsPackageVersionRow.package_id == package_id,
                    FdsPackageVersionRow.package_version == package_version,
                )
            )
            return self._package_record(row)

    def list_package_versions(self) -> tuple[FdsPackageVersionRecord, ...]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(FdsPackageVersionRow).order_by(
                    FdsPackageVersionRow.package_id,
                    FdsPackageVersionRow.package_version,
                )
            )
            return tuple(self._required_package_record(row) for row in rows)

    def add_package_version(
        self,
        record: FdsPackageVersionRecord,
        *,
        actor_ref: str,
        idempotency_key: str,
        request_digest: str,
        audit_events: tuple[AuditEvent, ...],
    ) -> FdsPackageVersionRecord:
        with self._session_factory() as session, session.begin():
            replay = self._find_replay(
                session,
                actor_ref,
                "fds-package.register",
                idempotency_key,
                request_digest,
            )
            if replay is not None:
                return self._replayed_package(session, replay)
            session.add(self._package_row(record))
            self._add_audit_events(session, audit_events)
            self._add_idempotency(
                session,
                actor_ref,
                "fds-package.register",
                idempotency_key,
                request_digest,
                "FDS_PACKAGE_VERSION",
                record.package_version_id,
            )
            self._flush(session, package_conflict=True)
        return record

    def save_package_version(
        self,
        record: FdsPackageVersionRecord,
        *,
        expected_version: int,
        actor_ref: str,
        operation: str,
        idempotency_key: str,
        request_digest: str,
        audit_events: tuple[AuditEvent, ...],
    ) -> FdsPackageVersionRecord:
        with self._session_factory() as session, session.begin():
            replay = self._find_replay(
                session, actor_ref, operation, idempotency_key, request_digest
            )
            if replay is not None:
                return self._replayed_package(session, replay)
            row = session.scalar(
                select(FdsPackageVersionRow)
                .where(FdsPackageVersionRow.package_version_id == record.package_version_id)
                .with_for_update()
            )
            if row is None or row.version != expected_version:
                raise self._concurrency_conflict(expected_version)
            row.state = record.state.value
            row.governance_reason = record.governance_reason
            row.governed_at = record.governed_at
            row.updated_at = record.updated_at
            row.version = expected_version + 1
            self._add_audit_events(session, audit_events)
            self._add_idempotency(
                session,
                actor_ref,
                operation,
                idempotency_key,
                request_digest,
                "FDS_PACKAGE_VERSION",
                record.package_version_id,
            )
            self._flush(session)
        return record.model_copy(update={"version": expected_version + 1})

    def get_installation(self, installation_id: UUID) -> FdsInstallation | None:
        with self._session_factory() as session:
            return self._installation(session, session.get(FdsInstallationRow, installation_id))

    def get_installation_by_lock(
        self, organization_id: UUID, root_package_version_id: UUID, lock_digest: str
    ) -> FdsInstallation | None:
        with self._session_factory() as session:
            row = session.scalar(
                select(FdsInstallationRow).where(
                    FdsInstallationRow.organization_id == organization_id,
                    FdsInstallationRow.root_package_version_id == root_package_version_id,
                    FdsInstallationRow.lock_digest == lock_digest,
                )
            )
            return self._installation(session, row)

    def list_installations(
        self, organization_id: UUID | None = None
    ) -> tuple[FdsInstallation, ...]:
        with self._session_factory() as session:
            statement = select(FdsInstallationRow)
            if organization_id is not None:
                statement = statement.where(FdsInstallationRow.organization_id == organization_id)
            rows = session.scalars(
                statement.order_by(
                    FdsInstallationRow.created_at, FdsInstallationRow.installation_id
                )
            )
            return tuple(self._required_installation(session, row) for row in rows)

    def add_installation(
        self,
        installation: FdsInstallation,
        *,
        actor_ref: str,
        idempotency_key: str,
        request_digest: str,
        audit_events: tuple[AuditEvent, ...],
    ) -> FdsInstallation:
        with self._session_factory() as session, session.begin():
            replay = self._find_replay(
                session,
                actor_ref,
                "fds-installation.create",
                idempotency_key,
                request_digest,
            )
            if replay is not None:
                return self._replayed_installation(session, replay)
            session.add(self._installation_row(installation))
            session.flush()
            for ref in installation.package_version_refs:
                session.add(self._installation_ref_row(installation.installation_id, ref))
            self._add_audit_events(session, audit_events)
            self._add_idempotency(
                session,
                actor_ref,
                "fds-installation.create",
                idempotency_key,
                request_digest,
                "FDS_INSTALLATION",
                installation.installation_id,
            )
            self._flush(session)
        return installation

    def save_installation(
        self,
        installation: FdsInstallation,
        *,
        expected_version: int,
        actor_ref: str,
        operation: str,
        idempotency_key: str,
        request_digest: str,
        audit_events: tuple[AuditEvent, ...],
    ) -> FdsInstallation:
        with self._session_factory() as session, session.begin():
            replay = self._find_replay(
                session, actor_ref, operation, idempotency_key, request_digest
            )
            if replay is not None:
                return self._replayed_installation(session, replay)
            row = session.scalar(
                select(FdsInstallationRow)
                .where(FdsInstallationRow.installation_id == installation.installation_id)
                .with_for_update()
            )
            if row is None or row.version != expected_version:
                raise self._concurrency_conflict(expected_version)
            row.state = installation.state.value
            row.governance_reason = installation.governance_reason
            row.updated_at = installation.updated_at
            row.version = expected_version + 1
            self._add_audit_events(session, audit_events)
            self._add_idempotency(
                session,
                actor_ref,
                operation,
                idempotency_key,
                request_digest,
                "FDS_INSTALLATION",
                installation.installation_id,
            )
            self._flush(session)
        return installation.model_copy(update={"version": expected_version + 1})

    def get_project_domain_lock(self, lock_id: UUID) -> ProjectDomainLock | None:
        with self._session_factory() as session:
            return self._domain_lock(session, session.get(ProjectDomainLockRow, lock_id))

    def get_current_project_domain_lock(self, project_id: UUID) -> ProjectDomainLock | None:
        with self._session_factory() as session:
            row = session.scalar(
                select(ProjectDomainLockRow).where(
                    ProjectDomainLockRow.project_id == project_id,
                    ProjectDomainLockRow.status == ProjectDomainLockState.CURRENT.value,
                )
            )
            return self._domain_lock(session, row)

    def list_project_domain_locks(self, project_id: UUID) -> tuple[ProjectDomainLock, ...]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(ProjectDomainLockRow)
                .where(ProjectDomainLockRow.project_id == project_id)
                .order_by(
                    ProjectDomainLockRow.created_at.desc(),
                    ProjectDomainLockRow.project_domain_lock_id,
                )
            )
            return tuple(self._required_domain_lock(session, row) for row in rows)

    def switch_project_domain_lock(
        self,
        domain_lock: ProjectDomainLock,
        *,
        actor_ref: str,
        idempotency_key: str,
        request_digest: str,
        audit_events: tuple[AuditEvent, ...],
    ) -> ProjectDomainLock:
        with self._session_factory() as session, session.begin():
            replay = self._find_replay(
                session,
                actor_ref,
                "project-domain-lock.switch",
                idempotency_key,
                request_digest,
            )
            if replay is not None:
                return self._replayed_domain_lock(session, replay)
            current = session.scalar(
                select(ProjectDomainLockRow)
                .where(
                    ProjectDomainLockRow.project_id == domain_lock.project_id,
                    ProjectDomainLockRow.status == ProjectDomainLockState.CURRENT.value,
                )
                .with_for_update()
            )
            if current is not None:
                if domain_lock.previous_lock_id != current.project_domain_lock_id:
                    raise ForgeOpsError(
                        ErrorCode.CURRENT_DOMAIN_LOCK_CONFLICT,
                        "current Project DomainLock changed before the switch committed",
                        http_status=409,
                    )
                current.status = ProjectDomainLockState.SUPERSEDED.value
                current.version += 1
            elif domain_lock.previous_lock_id is not None:
                raise ForgeOpsError(
                    ErrorCode.CURRENT_DOMAIN_LOCK_CONFLICT,
                    "expected current Project DomainLock is no longer current",
                    http_status=409,
                )
            session.add(self._domain_lock_row(domain_lock))
            session.flush()
            for ref in domain_lock.package_version_refs:
                session.add(self._domain_lock_ref_row(domain_lock.project_domain_lock_id, ref))
            self._add_audit_events(session, audit_events)
            self._add_idempotency(
                session,
                actor_ref,
                "project-domain-lock.switch",
                idempotency_key,
                request_digest,
                "PROJECT_DOMAIN_LOCK",
                domain_lock.project_domain_lock_id,
            )
            self._flush(session, current_lock_conflict=True)
        return domain_lock

    def current_lock_exists_for_installation(self, installation_id: UUID) -> bool:
        with self._session_factory() as session:
            return (
                session.scalar(
                    select(ProjectDomainLockRow.project_domain_lock_id).where(
                        ProjectDomainLockRow.installation_id == installation_id,
                        ProjectDomainLockRow.status == ProjectDomainLockState.CURRENT.value,
                    )
                )
                is not None
            )

    def impacts_for_package_version(
        self, package_version_id: UUID
    ) -> tuple[tuple[FdsInstallation, ...], tuple[ProjectDomainLock, ...]]:
        with self._session_factory() as session:
            installation_ids = tuple(
                session.scalars(
                    select(FdsInstallationPackageRefRow.installation_id).where(
                        FdsInstallationPackageRefRow.package_version_id == package_version_id
                    )
                )
            )
            lock_ids = tuple(
                session.scalars(
                    select(ProjectDomainLockPackageRefRow.project_domain_lock_id).where(
                        ProjectDomainLockPackageRefRow.package_version_id == package_version_id
                    )
                )
            )
            installations = (
                tuple(
                    self._required_installation(session, row)
                    for row in session.scalars(
                        select(FdsInstallationRow)
                        .where(FdsInstallationRow.installation_id.in_(installation_ids))
                        .order_by(FdsInstallationRow.created_at)
                    )
                )
                if installation_ids
                else ()
            )
            locks = (
                tuple(
                    self._required_domain_lock(session, row)
                    for row in session.scalars(
                        select(ProjectDomainLockRow)
                        .where(ProjectDomainLockRow.project_domain_lock_id.in_(lock_ids))
                        .order_by(ProjectDomainLockRow.created_at)
                    )
                )
                if lock_ids
                else ()
            )
            return installations, locks

    @staticmethod
    def _package_row(record: FdsPackageVersionRecord) -> FdsPackageVersionRow:
        return FdsPackageVersionRow(
            package_version_id=record.package_version_id,
            package_id=record.package_id,
            package_version=record.package_version,
            kind=record.kind.value,
            component_kind=record.component_kind.value if record.component_kind else None,
            manifest=record.manifest.model_dump(mode="json", by_alias=True),
            normalized_manifest=record.normalized_manifest,
            manifest_digest=record.manifest_digest,
            content_digest=record.content_digest,
            artifact_ref=record.artifact_ref,
            sbom_ref=record.sbom_ref,
            signature_ref=record.signature_ref,
            publisher=record.publisher,
            namespace_owner=record.namespace_owner,
            license_id=record.license_id,
            license_verified=record.license_verified,
            provenance_ref=record.provenance_ref,
            provenance_digest=record.provenance_digest,
            visibility=record.visibility.value,
            content_classification=record.content_classification.value,
            trust_tier=record.trust_tier.value,
            owner_organization_id=record.owner_organization_id,
            state=record.state.value,
            governance_reason=record.governance_reason,
            governed_at=record.governed_at,
            created_by=record.created_by,
            created_at=record.created_at,
            updated_at=record.updated_at,
            version=record.version,
        )

    @staticmethod
    def _package_record(row: FdsPackageVersionRow | None) -> FdsPackageVersionRecord | None:
        if row is None:
            return None
        return FdsPackageVersionRecord(
            package_version_id=row.package_version_id,
            package_id=row.package_id,
            package_version=row.package_version,
            kind=row.kind,
            component_kind=row.component_kind,
            manifest=FDS_MANIFEST_ADAPTER.validate_python(row.manifest),
            normalized_manifest=row.normalized_manifest,
            manifest_digest=row.manifest_digest,
            content_digest=row.content_digest,
            artifact_ref=row.artifact_ref,
            sbom_ref=row.sbom_ref,
            signature_ref=row.signature_ref,
            publisher=row.publisher,
            namespace_owner=row.namespace_owner,
            license_id=row.license_id,
            license_verified=row.license_verified,
            provenance_ref=row.provenance_ref,
            provenance_digest=row.provenance_digest,
            visibility=row.visibility,
            content_classification=row.content_classification,
            trust_tier=row.trust_tier,
            owner_organization_id=row.owner_organization_id,
            state=RegistryState(row.state),
            governance_reason=row.governance_reason,
            governed_at=SqlDomainRegistryRepository._utc_optional(row.governed_at),
            created_by=row.created_by,
            created_at=SqlDomainRegistryRepository._utc(row.created_at),
            updated_at=SqlDomainRegistryRepository._utc(row.updated_at),
            version=row.version,
        )

    @classmethod
    def _required_package_record(cls, row: FdsPackageVersionRow) -> FdsPackageVersionRecord:
        record = cls._package_record(row)
        assert record is not None
        return record

    @staticmethod
    def _installation_row(installation: FdsInstallation) -> FdsInstallationRow:
        return FdsInstallationRow(
            installation_id=installation.installation_id,
            organization_id=installation.organization_id,
            root_package_version_id=installation.root_package_version_id,
            root_package_id=installation.root_package_id,
            root_package_version=installation.root_package_version,
            root_kind=installation.root_kind.value,
            dependency_lock=installation.dependency_lock.model_dump(mode="json", by_alias=True),
            lock_digest=installation.lock_digest,
            target_versions=installation.target_versions.model_dump(mode="json", by_alias=True),
            include_optional=installation.include_optional,
            requested_permissions=list(installation.requested_permissions),
            permission_delta=list(installation.permission_delta),
            resource_budget=installation.resource_budget.model_dump(mode="json", by_alias=True),
            resource_budget_delta=installation.resource_budget_delta.model_dump(
                mode="json", by_alias=True
            ),
            state=installation.state.value,
            governance_reason=installation.governance_reason,
            created_by=installation.created_by,
            created_at=installation.created_at,
            updated_at=installation.updated_at,
            version=installation.version,
        )

    @classmethod
    def _installation(
        cls, session: Session, row: FdsInstallationRow | None
    ) -> FdsInstallation | None:
        if row is None:
            return None
        refs = session.scalars(
            select(FdsInstallationPackageRefRow)
            .where(FdsInstallationPackageRefRow.installation_id == row.installation_id)
            .order_by(FdsInstallationPackageRefRow.package_id)
        )
        return FdsInstallation(
            installation_id=row.installation_id,
            organization_id=row.organization_id,
            root_package_version_id=row.root_package_version_id,
            root_package_id=row.root_package_id,
            root_package_version=row.root_package_version,
            root_kind=row.root_kind,
            dependency_lock=DependencyLock.model_validate(row.dependency_lock),
            lock_digest=row.lock_digest,
            target_versions=TargetVersions.model_validate(row.target_versions),
            include_optional=row.include_optional,
            package_version_refs=tuple(cls._package_ref(ref) for ref in refs),
            requested_permissions=tuple(row.requested_permissions),
            permission_delta=tuple(row.permission_delta),
            resource_budget=RequestedResourceBudget.model_validate(row.resource_budget),
            resource_budget_delta=RequestedResourceBudget.model_validate(row.resource_budget_delta),
            state=DomainInstallationState(row.state),
            governance_reason=row.governance_reason,
            created_by=row.created_by,
            created_at=cls._utc(row.created_at),
            updated_at=cls._utc(row.updated_at),
            version=row.version,
        )

    @classmethod
    def _required_installation(cls, session: Session, row: FdsInstallationRow) -> FdsInstallation:
        installation = cls._installation(session, row)
        assert installation is not None
        return installation

    @staticmethod
    def _installation_ref_row(
        installation_id: UUID, ref: PackageVersionRef
    ) -> FdsInstallationPackageRefRow:
        return FdsInstallationPackageRefRow(
            ref_id=uuid4(),
            installation_id=installation_id,
            **SqlDomainRegistryRepository._package_ref_values(ref),
        )

    @staticmethod
    def _domain_lock_row(domain_lock: ProjectDomainLock) -> ProjectDomainLockRow:
        return ProjectDomainLockRow(
            project_domain_lock_id=domain_lock.project_domain_lock_id,
            project_id=domain_lock.project_id,
            organization_id=domain_lock.organization_id,
            installation_id=domain_lock.installation_id,
            root_package_id=domain_lock.root_package_id,
            root_package_version=domain_lock.root_package_version,
            root_kind=domain_lock.root_kind.value,
            dependency_lock=domain_lock.dependency_lock.model_dump(mode="json", by_alias=True),
            lock_digest=domain_lock.lock_digest,
            requested_permissions=list(domain_lock.requested_permissions),
            permission_delta=list(domain_lock.permission_delta),
            resource_budget=domain_lock.resource_budget.model_dump(mode="json", by_alias=True),
            resource_budget_delta=domain_lock.resource_budget_delta.model_dump(
                mode="json", by_alias=True
            ),
            purpose=domain_lock.purpose,
            status=domain_lock.status.value,
            previous_lock_id=domain_lock.previous_lock_id,
            created_by=domain_lock.created_by,
            created_at=domain_lock.created_at,
            version=domain_lock.version,
        )

    @classmethod
    def _domain_lock(
        cls, session: Session, row: ProjectDomainLockRow | None
    ) -> ProjectDomainLock | None:
        if row is None:
            return None
        refs = session.scalars(
            select(ProjectDomainLockPackageRefRow)
            .where(
                ProjectDomainLockPackageRefRow.project_domain_lock_id == row.project_domain_lock_id
            )
            .order_by(ProjectDomainLockPackageRefRow.package_id)
        )
        return ProjectDomainLock(
            project_domain_lock_id=row.project_domain_lock_id,
            project_id=row.project_id,
            organization_id=row.organization_id,
            installation_id=row.installation_id,
            root_package_id=row.root_package_id,
            root_package_version=row.root_package_version,
            root_kind=row.root_kind,
            dependency_lock=DependencyLock.model_validate(row.dependency_lock),
            lock_digest=row.lock_digest,
            package_version_refs=tuple(cls._package_ref(ref) for ref in refs),
            requested_permissions=tuple(row.requested_permissions),
            permission_delta=tuple(row.permission_delta),
            resource_budget=RequestedResourceBudget.model_validate(row.resource_budget),
            resource_budget_delta=RequestedResourceBudget.model_validate(row.resource_budget_delta),
            purpose=row.purpose,
            status=ProjectDomainLockState(row.status),
            previous_lock_id=row.previous_lock_id,
            created_by=row.created_by,
            created_at=cls._utc(row.created_at),
            version=row.version,
        )

    @classmethod
    def _required_domain_lock(
        cls, session: Session, row: ProjectDomainLockRow
    ) -> ProjectDomainLock:
        lock = cls._domain_lock(session, row)
        assert lock is not None
        return lock

    @staticmethod
    def _domain_lock_ref_row(
        lock_id: UUID, ref: PackageVersionRef
    ) -> ProjectDomainLockPackageRefRow:
        return ProjectDomainLockPackageRefRow(
            ref_id=uuid4(),
            project_domain_lock_id=lock_id,
            **SqlDomainRegistryRepository._package_ref_values(ref),
        )

    @staticmethod
    def _package_ref_values(ref: PackageVersionRef) -> dict[str, object]:
        return {
            "package_version_id": ref.package_version_id,
            "package_id": ref.package_id,
            "package_version": ref.package_version,
            "kind": ref.kind.value,
            "component_kind": ref.component_kind.value if ref.component_kind else None,
            "manifest_digest": ref.manifest_digest,
            "content_digest": ref.content_digest,
        }

    @staticmethod
    def _package_ref(
        ref: FdsInstallationPackageRefRow | ProjectDomainLockPackageRefRow,
    ) -> PackageVersionRef:
        return PackageVersionRef(
            package_version_id=ref.package_version_id,
            package_id=ref.package_id,
            package_version=ref.package_version,
            kind=ref.kind,
            component_kind=ref.component_kind,
            manifest_digest=ref.manifest_digest,
            content_digest=ref.content_digest,
        )

    @staticmethod
    def _find_replay(
        session: Session,
        actor_ref: str,
        operation: str,
        idempotency_key: str,
        request_digest: str,
    ) -> FdsIdempotencyRecordRow | None:
        replay = session.scalar(
            select(FdsIdempotencyRecordRow).where(
                FdsIdempotencyRecordRow.actor_ref == actor_ref,
                FdsIdempotencyRecordRow.action_key == operation,
                FdsIdempotencyRecordRow.idempotency_key == idempotency_key,
            )
        )
        if replay is not None and replay.request_digest != request_digest:
            raise ForgeOpsError(
                ErrorCode.IDEMPOTENCY_CONFLICT,
                "Idempotency-Key was already used with a different request",
                http_status=409,
            )
        return replay

    @staticmethod
    def _add_idempotency(
        session: Session,
        actor_ref: str,
        operation: str,
        idempotency_key: str,
        request_digest: str,
        resource_type: str,
        resource_id: UUID,
    ) -> None:
        session.add(
            FdsIdempotencyRecordRow(
                record_id=uuid4(),
                actor_ref=actor_ref,
                action_key=operation,
                idempotency_key=idempotency_key,
                request_digest=request_digest,
                resource_type=resource_type,
                resource_id=resource_id,
                created_at=datetime.now(UTC),
            )
        )

    @staticmethod
    def _add_audit_events(session: Session, events: tuple[AuditEvent, ...]) -> None:
        for event in events:
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
                    scope_ref=event.scope_ref,
                    policy_version=event.policy_version,
                )
            )

    @classmethod
    def _replayed_package(
        cls, session: Session, replay: FdsIdempotencyRecordRow
    ) -> FdsPackageVersionRecord:
        record = cls._package_record(session.get(FdsPackageVersionRow, replay.resource_id))
        if record is None:
            raise cls._idempotency_corrupt()
        return record

    @classmethod
    def _replayed_installation(
        cls, session: Session, replay: FdsIdempotencyRecordRow
    ) -> FdsInstallation:
        installation = cls._installation(
            session, session.get(FdsInstallationRow, replay.resource_id)
        )
        if installation is None:
            raise cls._idempotency_corrupt()
        return installation

    @classmethod
    def _replayed_domain_lock(
        cls, session: Session, replay: FdsIdempotencyRecordRow
    ) -> ProjectDomainLock:
        lock = cls._domain_lock(session, session.get(ProjectDomainLockRow, replay.resource_id))
        if lock is None:
            raise cls._idempotency_corrupt()
        return lock

    @staticmethod
    def _flush(
        session: Session,
        *,
        package_conflict: bool = False,
        current_lock_conflict: bool = False,
    ) -> None:
        try:
            session.flush()
        except IntegrityError as exc:
            message = str(exc.orig).lower()
            if current_lock_conflict and (
                "uq_project_domain_locks_current" in message
                or "project_domain_locks.project_id" in message
            ):
                code = ErrorCode.CURRENT_DOMAIN_LOCK_CONFLICT
            elif package_conflict and (
                "uq_fds_package_version" in message or "fds_package_versions.package_id" in message
            ):
                code = ErrorCode.PACKAGE_VERSION_DIGEST_CONFLICT
            else:
                code = ErrorCode.IDEMPOTENCY_CONFLICT
            raise ForgeOpsError(
                code, "resource conflicts with an existing record", http_status=409
            ) from exc

    @staticmethod
    def _concurrency_conflict(expected_version: int) -> ForgeOpsError:
        return ForgeOpsError(
            ErrorCode.CONCURRENCY_CONFLICT,
            "resource version does not match If-Match",
            details={"expectedVersion": expected_version},
            http_status=409,
        )

    @staticmethod
    def _idempotency_corrupt() -> ForgeOpsError:
        return ForgeOpsError(
            ErrorCode.INTERNAL_FAILURE,
            "idempotency record refers to a missing resource",
            http_status=500,
        )

    @staticmethod
    def _utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    @classmethod
    def _utc_optional(cls, value: datetime | None) -> datetime | None:
        return cls._utc(value) if value is not None else None
