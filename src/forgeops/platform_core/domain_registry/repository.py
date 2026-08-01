from __future__ import annotations

from typing import Protocol
from uuid import UUID

from forgeops.platform_core.audit import AuditEvent
from forgeops.platform_core.domain_registry.entities import (
    FdsInstallation,
    FdsPackageVersionRecord,
    ProjectDomainLock,
)


class DomainRegistryRepository(Protocol):
    def find_idempotent_resource(
        self,
        actor_ref: str,
        operation: str,
        idempotency_key: str,
        request_digest: str,
    ) -> tuple[str, UUID] | None: ...

    def bind_idempotent_resource(
        self,
        actor_ref: str,
        operation: str,
        idempotency_key: str,
        request_digest: str,
        resource_type: str,
        resource_id: UUID,
    ) -> None: ...

    def get_package_version(self, package_version_id: UUID) -> FdsPackageVersionRecord | None: ...

    def get_package_version_by_identity(
        self, package_id: str, package_version: str
    ) -> FdsPackageVersionRecord | None: ...

    def list_package_versions(self) -> tuple[FdsPackageVersionRecord, ...]: ...

    def add_package_version(
        self,
        record: FdsPackageVersionRecord,
        *,
        actor_ref: str,
        idempotency_key: str,
        request_digest: str,
        audit_events: tuple[AuditEvent, ...],
    ) -> FdsPackageVersionRecord: ...

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
    ) -> FdsPackageVersionRecord: ...

    def get_installation(self, installation_id: UUID) -> FdsInstallation | None: ...

    def get_installation_by_lock(
        self, organization_id: UUID, root_package_version_id: UUID, lock_digest: str
    ) -> FdsInstallation | None: ...

    def list_installations(
        self, organization_id: UUID | None = None
    ) -> tuple[FdsInstallation, ...]: ...

    def add_installation(
        self,
        installation: FdsInstallation,
        *,
        actor_ref: str,
        idempotency_key: str,
        request_digest: str,
        audit_events: tuple[AuditEvent, ...],
    ) -> FdsInstallation: ...

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
    ) -> FdsInstallation: ...

    def get_project_domain_lock(self, lock_id: UUID) -> ProjectDomainLock | None: ...

    def get_current_project_domain_lock(self, project_id: UUID) -> ProjectDomainLock | None: ...

    def list_project_domain_locks(self, project_id: UUID) -> tuple[ProjectDomainLock, ...]: ...

    def switch_project_domain_lock(
        self,
        domain_lock: ProjectDomainLock,
        *,
        actor_ref: str,
        idempotency_key: str,
        request_digest: str,
        audit_events: tuple[AuditEvent, ...],
    ) -> ProjectDomainLock: ...

    def current_lock_exists_for_installation(self, installation_id: UUID) -> bool: ...

    def impacts_for_package_version(
        self, package_version_id: UUID
    ) -> tuple[tuple[FdsInstallation, ...], tuple[ProjectDomainLock, ...]]: ...
