from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from forgeops.fds_sdk.canonical import sha256_digest
from forgeops.fds_sdk.models import (
    ComponentManifest,
    FdsValidationReport,
    OrganizationOverlayManifest,
    PackageKind,
    PackageRef,
    TargetVersions,
    Visibility,
)
from forgeops.fds_sdk.resolver import DependencyResolver, verify_dependency_lock
from forgeops.fds_sdk.validation import FdsManifestValidator
from forgeops.platform_contracts.errors import ErrorCode, ForgeOpsError
from forgeops.platform_core.audit import AuditEvent, AuditRepository
from forgeops.platform_core.domain_registry.entities import (
    DerivedHealth,
    DomainInstallationState,
    DomainLockDiff,
    DomainLockImpact,
    FdsInstallation,
    FdsPackageVersionRecord,
    HealthSummary,
    InstallationImpact,
    PackageChange,
    PackageImpactReport,
    PackageVersionRef,
    ProjectDomainLock,
    RegistryState,
    installation_transition_allowed,
    registry_transition_allowed,
)
from forgeops.platform_core.domain_registry.repository import DomainRegistryRepository
from forgeops.platform_core.identity_access.entities import (
    MembershipState,
    Organization,
    OrganizationState,
    Project,
    ProjectState,
    ScopeType,
    Workspace,
    WorkspaceState,
)
from forgeops.platform_core.identity_access.policy import (
    ROLE_PERMISSIONS,
    AuthorizationService,
    Permission,
)
from forgeops.platform_core.identity_access.repository import IdentityRepository
from forgeops.platform_core.identity_access.service import ActorContext


class DomainRegistryService:
    def __init__(
        self,
        repository: DomainRegistryRepository,
        identities: IdentityRepository,
        audit: AuditRepository,
        validator: FdsManifestValidator | None = None,
        resolver: DependencyResolver | None = None,
    ) -> None:
        self._repository = repository
        self._identities = identities
        self._audit = audit
        self._validator = validator or FdsManifestValidator()
        self._resolver = resolver or DependencyResolver()
        self._authorization = AuthorizationService()

    def validate_manifest(
        self,
        actor: ActorContext,
        raw_manifest: dict[str, Any],
        owner_organization_id: UUID | None,
        trace_id: str,
    ) -> FdsValidationReport:
        self._authorize_registration(actor, raw_manifest, owner_organization_id, trace_id)
        return self._validator.validate(raw_manifest)

    def register_package_version(
        self,
        actor: ActorContext,
        raw_manifest: dict[str, Any],
        *,
        owner_organization_id: UUID | None,
        idempotency_key: str,
        trace_id: str,
    ) -> FdsPackageVersionRecord:
        self._authorize_registration(actor, raw_manifest, owner_organization_id, trace_id)
        report = self._validator.validate(raw_manifest)
        if not report.valid or report.manifest is None:
            first = report.issues[0]
            self._audit_failure(
                "domain.package.registration.failed.v1",
                actor,
                f"fds-package://{raw_manifest.get('packageId', 'invalid')}",
                first.code.value,
                trace_id,
                details={"issueCodes": [item.code.value for item in report.issues]},
            )
            raise ForgeOpsError(
                first.code,
                first.message,
                details={
                    "issues": [
                        item.model_dump(mode="json", by_alias=True) for item in report.issues
                    ]
                },
                http_status=422,
            )
        assert report.normalized_manifest is not None and report.manifest_digest is not None
        manifest = report.manifest
        self._validate_owner_boundary(manifest, owner_organization_id)
        request_digest = sha256_digest(
            {
                "manifest": manifest,
                "ownerOrganizationId": (
                    str(owner_organization_id) if owner_organization_id else None
                ),
            }
        )
        replay_id = self._idempotent_resource_id(
            actor,
            "fds-package.register",
            idempotency_key,
            request_digest,
            "FDS_PACKAGE_VERSION",
        )
        if replay_id is not None:
            replay = self._repository.get_package_version(replay_id)
            if replay is None:
                raise self._idempotency_corrupt()
            if (
                not self._can_view_record(actor, replay)
                or replay.owner_organization_id != owner_organization_id
            ):
                self._hidden(actor, f"fds-package-version://{replay_id}", trace_id)
            return replay
        existing = self._repository.get_package_version_by_identity(
            manifest.package_id, manifest.package_version
        )
        if existing is not None:
            if (
                not self._can_view_record(actor, existing)
                or existing.owner_organization_id != owner_organization_id
            ):
                self._hidden(
                    actor,
                    f"fds-package://{manifest.package_id}@{manifest.package_version}",
                    trace_id,
                )
            if (
                existing.content_digest == manifest.content_digest
                and existing.manifest_digest == report.manifest_digest
            ):
                self._repository.bind_idempotent_resource(
                    actor.principal.subject_ref,
                    "fds-package.register",
                    idempotency_key,
                    request_digest,
                    "FDS_PACKAGE_VERSION",
                    existing.package_version_id,
                )
                return existing
            self._audit_failure(
                "domain.package.registration.failed.v1",
                actor,
                f"fds-package://{manifest.package_id}@{manifest.package_version}",
                ErrorCode.PACKAGE_VERSION_DIGEST_CONFLICT.value,
                trace_id,
            )
            raise ForgeOpsError(
                ErrorCode.PACKAGE_VERSION_DIGEST_CONFLICT,
                "the Registry package version already exists with different immutable content",
                http_status=409,
            )
        component_kind = (
            manifest.component_kind if isinstance(manifest, ComponentManifest) else None
        )
        now = datetime.now(UTC)
        record = FdsPackageVersionRecord(
            package_id=manifest.package_id,
            package_version=manifest.package_version,
            kind=manifest.kind,
            component_kind=component_kind,
            manifest=manifest,
            normalized_manifest=report.normalized_manifest,
            manifest_digest=report.manifest_digest,
            content_digest=manifest.content_digest,
            artifact_ref=manifest.artifact.artifact_ref,
            sbom_ref=manifest.artifact.sbom_ref,
            signature_ref=manifest.artifact.signature,
            publisher=manifest.publisher,
            namespace_owner=manifest.namespace_owner,
            license_id=manifest.license.license_id,
            license_verified=manifest.license.verified,
            provenance_ref=manifest.provenance.source_ref,
            provenance_digest=manifest.provenance.provenance_digest,
            visibility=manifest.visibility,
            content_classification=manifest.content_classification,
            trust_tier=manifest.trust_tier,
            owner_organization_id=owner_organization_id,
            created_by=actor.principal.subject_ref,
            created_at=now,
            updated_at=now,
        )
        event = self._event(
            "domain.package.registered.v1",
            actor,
            f"fds-package-version://{record.package_version_id}",
            "SUCCESS",
            record.state.value,
            trace_id,
            scope_ref=self._record_scope_ref(record),
            details={
                "packageId": record.package_id,
                "packageVersion": record.package_version,
                "manifestDigest": record.manifest_digest,
                "contentDigest": record.content_digest,
                "trustBoundary": "NOT_ENTERPRISE_VERIFIED",
            },
        )
        return self._repository.add_package_version(
            record,
            actor_ref=actor.principal.subject_ref,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
            audit_events=(event,),
        )

    def list_package_versions(
        self,
        actor: ActorContext,
        *,
        kind: PackageKind | None = None,
        state: RegistryState | None = None,
        visibility: Visibility | None = None,
        organization_id: UUID | None = None,
    ) -> tuple[FdsPackageVersionRecord, ...]:
        records = []
        for record in self._repository.list_package_versions():
            if not self._can_view_record(actor, record):
                continue
            if kind is not None and record.kind != kind:
                continue
            if state is not None and record.state != state:
                continue
            if visibility is not None and record.visibility != visibility:
                continue
            if organization_id is not None and record.owner_organization_id != organization_id:
                continue
            records.append(record)
        return tuple(records)

    def get_package_version(
        self, actor: ActorContext, package_version_id: UUID, trace_id: str
    ) -> FdsPackageVersionRecord:
        record = self._repository.get_package_version(package_version_id)
        if record is None or not self._can_view_record(actor, record):
            self._hidden(actor, f"fds-package-version://{package_version_id}", trace_id)
        assert record is not None
        return record

    def transition_package_version(
        self,
        actor: ActorContext,
        package_version_id: UUID,
        *,
        target: RegistryState,
        reason: str,
        expected_version: int,
        idempotency_key: str,
        trace_id: str,
    ) -> FdsPackageVersionRecord:
        record = self.get_package_version(actor, package_version_id, trace_id)
        self._authorize_record_manage(actor, record, trace_id)
        if target not in {RegistryState.QUARANTINED, RegistryState.WITHDRAWN}:
            raise ForgeOpsError(
                ErrorCode.ILLEGAL_STATE_TRANSITION,
                "unsupported Registry governance transition",
                http_status=409,
            )
        operation = f"fds-package.{target.value.lower()}"
        request_digest = sha256_digest(
            {
                "packageVersionId": str(package_version_id),
                "target": target,
                "reason": reason,
            }
        )
        replay_id = self._idempotent_resource_id(
            actor,
            operation,
            idempotency_key,
            request_digest,
            "FDS_PACKAGE_VERSION",
        )
        if replay_id is not None:
            replay = self._repository.get_package_version(replay_id)
            if replay is None:
                raise self._idempotency_corrupt()
            return replay
        if record.state == target:
            self._repository.bind_idempotent_resource(
                actor.principal.subject_ref,
                operation,
                idempotency_key,
                request_digest,
                "FDS_PACKAGE_VERSION",
                record.package_version_id,
            )
            return record
        if not registry_transition_allowed(record.state, target):
            raise ForgeOpsError(
                ErrorCode.ILLEGAL_STATE_TRANSITION,
                "Registry state does not permit this transition",
                http_status=409,
            )
        updated = record.model_copy(
            update={
                "state": target,
                "governance_reason": reason,
                "governed_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
        )
        event_type = (
            "domain.package.quarantined.v1"
            if target == RegistryState.QUARANTINED
            else "domain.package.withdrawn.v1"
        )
        impacts = self._repository.impacts_for_package_version(package_version_id)
        events = [
            self._event(
                event_type,
                actor,
                f"fds-package-version://{package_version_id}",
                "SUCCESS",
                reason,
                trace_id,
                scope_ref=self._record_scope_ref(record),
                details={
                    "packageId": record.package_id,
                    "packageVersion": record.package_version,
                    "manifestDigest": record.manifest_digest,
                    "affectedInstallations": len(impacts[0]),
                    "affectedProjectDomainLocks": len(impacts[1]),
                },
            )
        ]
        if impacts[0] or impacts[1]:
            events.append(
                self._event(
                    "domain.package.impact.detected.v1",
                    actor,
                    f"fds-package-version://{package_version_id}",
                    "SUCCESS",
                    target.value,
                    trace_id,
                    scope_ref=self._record_scope_ref(record),
                    details={
                        "installationCount": len(impacts[0]),
                        "projectDomainLockCount": len(impacts[1]),
                    },
                )
            )
        return self._repository.save_package_version(
            updated,
            expected_version=expected_version,
            actor_ref=actor.principal.subject_ref,
            operation=operation,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
            audit_events=tuple(events),
        )

    def preview_installation(
        self,
        actor: ActorContext,
        organization_id: UUID,
        *,
        root_package_version_id: UUID,
        target_versions: TargetVersions,
        include_optional: bool,
        trace_id: str,
    ) -> FdsInstallation:
        self._require_organization(
            actor, organization_id, Permission.FDS_INSTALLATION_MANAGE, trace_id
        )
        root = self._require_visible_usable_record(
            actor, root_package_version_id, organization_id, trace_id
        )
        if root.kind not in {PackageKind.DOMAIN, PackageKind.ORGANIZATION_OVERLAY}:
            raise ForgeOpsError(
                ErrorCode.INSTALLATION_STATE_INVALID,
                "only DOMAIN or ORGANIZATION_OVERLAY can be an installation root",
                http_status=422,
            )
        candidates = tuple(
            record
            for record in self._repository.list_package_versions()
            if record.state == RegistryState.REGISTERED_VALIDATED
            and self._record_visible_for_organization(record, organization_id)
        )
        report = self._resolver.resolve(
            PackageRef(
                package_id=root.package_id,
                version_constraint=f"=={root.package_version}",
                expected_kind=root.kind,
                content_digest=root.content_digest,
            ),
            (record.manifest for record in candidates),
            target_versions,
            include_optional=include_optional,
        )
        if not report.valid or report.lock is None:
            first = report.issues[0]
            self._audit_failure(
                "domain.installation.creation.failed.v1",
                actor,
                f"organization://{organization_id}",
                first.code.value,
                trace_id,
                scope_ref=f"organization://{organization_id}",
                details={"issueCodes": [item.code.value for item in report.issues]},
            )
            raise ForgeOpsError(
                ErrorCode.DEPENDENCY_RESOLUTION_FAILED,
                first.message,
                details={
                    "issues": [
                        item.model_dump(mode="json", by_alias=True) for item in report.issues
                    ]
                },
                http_status=422,
            )
        index = {(record.package_id, record.package_version): record for record in candidates}
        refs: list[PackageVersionRef] = []
        for node in report.lock.nodes:
            record = index.get((node.package_id, node.package_version))
            if record is None or record.content_digest != node.content_digest:
                raise ForgeOpsError(
                    ErrorCode.LOCK_CONTENT_MISMATCH,
                    "DependencyLock node is not backed by the current Registry",
                    http_status=409,
                )
            refs.append(record.package_ref())
        if verify_dependency_lock(report.lock, (item.manifest for item in candidates)):
            raise ForgeOpsError(
                ErrorCode.LOCK_DIGEST_MISMATCH,
                "DependencyLock failed canonical verification",
                http_status=409,
            )
        return FdsInstallation(
            organization_id=organization_id,
            root_package_version_id=root.package_version_id,
            root_package_id=root.package_id,
            root_package_version=root.package_version,
            root_kind=root.kind,
            dependency_lock=report.lock,
            lock_digest=report.lock.lock_digest,
            target_versions=target_versions,
            include_optional=include_optional,
            package_version_refs=tuple(refs),
            requested_permissions=report.lock.requested_permissions,
            permission_delta=report.lock.permission_delta,
            resource_budget=report.lock.resource_budget,
            resource_budget_delta=report.lock.resource_budget_delta,
            created_by=actor.principal.subject_ref,
        )

    def create_installation(
        self,
        actor: ActorContext,
        organization_id: UUID,
        *,
        root_package_version_id: UUID,
        target_versions: TargetVersions,
        include_optional: bool,
        idempotency_key: str,
        trace_id: str,
    ) -> FdsInstallation:
        self._require_organization(
            actor, organization_id, Permission.FDS_INSTALLATION_MANAGE, trace_id
        )
        request_digest = sha256_digest(
            {
                "organizationId": str(organization_id),
                "rootPackageVersionId": str(root_package_version_id),
                "targetVersions": target_versions,
                "includeOptional": include_optional,
            }
        )
        replay_id = self._idempotent_resource_id(
            actor,
            "fds-installation.create",
            idempotency_key,
            request_digest,
            "FDS_INSTALLATION",
        )
        if replay_id is not None:
            replay = self._repository.get_installation(replay_id)
            if replay is None:
                raise self._idempotency_corrupt()
            if replay.organization_id != organization_id:
                self._hidden(actor, f"fds-installation://{replay_id}", trace_id)
            return replay
        installation = self.preview_installation(
            actor,
            organization_id,
            root_package_version_id=root_package_version_id,
            target_versions=target_versions,
            include_optional=include_optional,
            trace_id=trace_id,
        )
        existing = self._repository.get_installation_by_lock(
            organization_id, root_package_version_id, installation.lock_digest
        )
        if existing is not None:
            self._repository.bind_idempotent_resource(
                actor.principal.subject_ref,
                "fds-installation.create",
                idempotency_key,
                request_digest,
                "FDS_INSTALLATION",
                existing.installation_id,
            )
            return existing
        event = self._event(
            "domain.installation.created-disabled.v1",
            actor,
            f"fds-installation://{installation.installation_id}",
            "SUCCESS",
            installation.state.value,
            trace_id,
            scope_ref=f"organization://{organization_id}",
            details={
                "rootPackageVersionId": str(root_package_version_id),
                "lockDigest": installation.lock_digest,
                "authorizationEffect": "NONE",
                "runtimeStateCreated": False,
                "semanticRuntimeReady": False,
            },
        )
        return self._repository.add_installation(
            installation,
            actor_ref=actor.principal.subject_ref,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
            audit_events=(event,),
        )

    def list_installations(
        self, actor: ActorContext, organization_id: UUID, trace_id: str
    ) -> tuple[tuple[FdsInstallation, HealthSummary], ...]:
        self._require_organization(
            actor, organization_id, Permission.FDS_INSTALLATION_VIEW, trace_id
        )
        return tuple(
            (item, self.installation_health(item))
            for item in self._repository.list_installations(organization_id)
        )

    def get_installation(
        self, actor: ActorContext, installation_id: UUID, trace_id: str
    ) -> tuple[FdsInstallation, HealthSummary]:
        installation = self._repository.get_installation(installation_id)
        if installation is None or not self._organization_allowed(
            actor, installation.organization_id, Permission.FDS_INSTALLATION_VIEW
        ):
            self._hidden(actor, f"fds-installation://{installation_id}", trace_id)
        assert installation is not None
        return installation, self.installation_health(installation)

    def transition_installation(
        self,
        actor: ActorContext,
        installation_id: UUID,
        *,
        target: DomainInstallationState,
        reason: str,
        expected_version: int,
        idempotency_key: str,
        trace_id: str,
    ) -> FdsInstallation:
        installation, _ = self.get_installation(actor, installation_id, trace_id)
        self._require_organization(
            actor,
            installation.organization_id,
            Permission.FDS_INSTALLATION_MANAGE,
            trace_id,
        )
        if target not in {
            DomainInstallationState.DISABLED,
            DomainInstallationState.REVOKED,
            DomainInstallationState.LOGICALLY_UNINSTALLED,
        }:
            raise ForgeOpsError(
                ErrorCode.INSTALLATION_STATE_INVALID,
                "unsupported installation governance transition",
                http_status=409,
            )
        suffix = {
            DomainInstallationState.DISABLED: "disabled",
            DomainInstallationState.REVOKED: "revoked",
            DomainInstallationState.LOGICALLY_UNINSTALLED: "logically-uninstalled",
        }[target]
        operation = f"fds-installation.{suffix}"
        request_digest = sha256_digest(
            {
                "installationId": str(installation_id),
                "target": target,
                "reason": reason,
            }
        )
        replay_id = self._idempotent_resource_id(
            actor,
            operation,
            idempotency_key,
            request_digest,
            "FDS_INSTALLATION",
        )
        if replay_id is not None:
            replay = self._repository.get_installation(replay_id)
            if replay is None:
                raise self._idempotency_corrupt()
            return replay
        if installation.state == target:
            self._repository.bind_idempotent_resource(
                actor.principal.subject_ref,
                operation,
                idempotency_key,
                request_digest,
                "FDS_INSTALLATION",
                installation.installation_id,
            )
            return installation
        if not installation_transition_allowed(installation.state, target):
            raise ForgeOpsError(
                ErrorCode.INSTALLATION_STATE_INVALID,
                "installation state does not permit this transition",
                http_status=409,
            )
        if (
            target == DomainInstallationState.LOGICALLY_UNINSTALLED
            and self._repository.current_lock_exists_for_installation(installation_id)
        ):
            raise ForgeOpsError(
                ErrorCode.UNINSTALL_BLOCKED_BY_CURRENT_LOCK,
                "logical uninstall is blocked by a current Project DomainLock",
                http_status=409,
            )
        updated = installation.model_copy(
            update={
                "state": target,
                "governance_reason": reason,
                "updated_at": datetime.now(UTC),
            }
        )
        event = self._event(
            f"domain.installation.{suffix}.v1",
            actor,
            f"fds-installation://{installation_id}",
            "SUCCESS",
            reason,
            trace_id,
            scope_ref=f"organization://{installation.organization_id}",
            details={"lockDigest": installation.lock_digest},
        )
        return self._repository.save_installation(
            updated,
            expected_version=expected_version,
            actor_ref=actor.principal.subject_ref,
            operation=operation,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
            audit_events=(event,),
        )

    def compare_installations(
        self,
        actor: ActorContext,
        from_installation_id: UUID,
        to_installation_id: UUID,
        trace_id: str,
    ) -> DomainLockDiff:
        before, _ = self.get_installation(actor, from_installation_id, trace_id)
        after, _ = self.get_installation(actor, to_installation_id, trace_id)
        if before.organization_id != after.organization_id:
            self._hidden(actor, f"fds-installation://{to_installation_id}", trace_id)
        before_nodes = {item.package_id: item for item in before.package_version_refs}
        after_nodes = {item.package_id: item for item in after.package_version_refs}
        added = tuple(
            PackageChange(
                package_id=key,
                to_version=after_nodes[key].package_version,
                to_digest=after_nodes[key].content_digest,
            )
            for key in sorted(after_nodes.keys() - before_nodes.keys())
        )
        removed = tuple(
            PackageChange(
                package_id=key,
                from_version=before_nodes[key].package_version,
                from_digest=before_nodes[key].content_digest,
            )
            for key in sorted(before_nodes.keys() - after_nodes.keys())
        )
        changed = tuple(
            PackageChange(
                package_id=key,
                from_version=before_nodes[key].package_version,
                to_version=after_nodes[key].package_version,
                from_digest=before_nodes[key].content_digest,
                to_digest=after_nodes[key].content_digest,
            )
            for key in sorted(before_nodes.keys() & after_nodes.keys())
            if before_nodes[key].package_version != after_nodes[key].package_version
            or before_nodes[key].content_digest != after_nodes[key].content_digest
        )
        before_permissions = set(before.requested_permissions)
        after_permissions = set(after.requested_permissions)
        budget_fields = ("cpu_millis", "memory_mib", "timeout_seconds", "max_output_bytes")
        budget_delta: dict[str, int | bool] = {
            field: getattr(after.resource_budget, field) - getattr(before.resource_budget, field)
            for field in budget_fields
        }
        budget_delta["networkAccessChanged"] = (
            after.resource_budget.network_access != before.resource_budget.network_access
        )
        trust_changes: list[str] = []
        for key in sorted(before_nodes.keys() & after_nodes.keys()):
            old = self._repository.get_package_version(before_nodes[key].package_version_id)
            new = self._repository.get_package_version(after_nodes[key].package_version_id)
            if (
                old is not None
                and new is not None
                and (old.visibility != new.visibility or old.trust_tier != new.trust_tier)
            ):
                trust_changes.append(key)
        return DomainLockDiff(
            from_installation_id=from_installation_id,
            to_installation_id=to_installation_id,
            added=added,
            removed=removed,
            changed=changed,
            permissions_added=tuple(sorted(after_permissions - before_permissions)),
            permissions_removed=tuple(sorted(before_permissions - after_permissions)),
            budget_delta=budget_delta,
            visibility_trust_changes=tuple(trust_changes),
        )

    def create_project_domain_lock(
        self,
        actor: ActorContext,
        project_id: UUID,
        *,
        installation_id: UUID,
        purpose: str,
        idempotency_key: str,
        trace_id: str,
    ) -> ProjectDomainLock:
        project, _, _, organization_id = self._require_project(
            actor, project_id, Permission.FDS_DOMAIN_LOCK_MANAGE, trace_id
        )
        if project.state != ProjectState.ACTIVE:
            raise ForgeOpsError(
                ErrorCode.PROJECT_NOT_ACTIVE,
                "Project must be ACTIVE before selecting a DomainLock",
                http_status=409,
            )
        request_digest = sha256_digest(
            {
                "projectId": str(project_id),
                "installationId": str(installation_id),
                "purpose": purpose,
            }
        )
        replay_id = self._idempotent_resource_id(
            actor,
            "project-domain-lock.switch",
            idempotency_key,
            request_digest,
            "PROJECT_DOMAIN_LOCK",
        )
        if replay_id is not None:
            replay = self._repository.get_project_domain_lock(replay_id)
            if replay is None:
                raise self._idempotency_corrupt()
            if replay.project_id != project_id:
                self._hidden(actor, f"project-domain-lock://{replay_id}", trace_id)
            return replay
        installation = self._repository.get_installation(installation_id)
        if installation is None or installation.organization_id != organization_id:
            self._hidden(actor, f"fds-installation://{installation_id}", trace_id)
        assert installation is not None
        if installation.state != DomainInstallationState.INSTALLED_DISABLED:
            raise ForgeOpsError(
                ErrorCode.INSTALLATION_STATE_INVALID,
                "only an INSTALLED_DISABLED installation can be selected",
                http_status=409,
            )
        health = self.installation_health(installation)
        if health.health != DerivedHealth.HEALTHY_FOR_SELECTION:
            raise ForgeOpsError(
                ErrorCode.WITHDRAWN_OR_QUARANTINED_DEPENDENCY,
                "installation has a quarantined, withdrawn, or changed Registry dependency",
                details={"reasons": list(health.reasons)},
                http_status=409,
            )
        self._verify_installation_integrity(installation)
        current = self._repository.get_current_project_domain_lock(project_id)
        if current is not None and current.installation_id == installation_id:
            self._repository.bind_idempotent_resource(
                actor.principal.subject_ref,
                "project-domain-lock.switch",
                idempotency_key,
                request_digest,
                "PROJECT_DOMAIN_LOCK",
                current.project_domain_lock_id,
            )
            return current
        domain_lock = ProjectDomainLock(
            project_id=project_id,
            organization_id=organization_id,
            installation_id=installation_id,
            root_package_id=installation.root_package_id,
            root_package_version=installation.root_package_version,
            root_kind=installation.root_kind,
            dependency_lock=installation.dependency_lock,
            lock_digest=installation.lock_digest,
            package_version_refs=installation.package_version_refs,
            requested_permissions=installation.requested_permissions,
            permission_delta=installation.permission_delta,
            resource_budget=installation.resource_budget,
            resource_budget_delta=installation.resource_budget_delta,
            purpose=purpose,
            previous_lock_id=(current.project_domain_lock_id if current else None),
            created_by=actor.principal.subject_ref,
        )
        events = []
        if current is not None:
            events.append(
                self._event(
                    "project.domain-lock.superseded.v1",
                    actor,
                    f"project-domain-lock://{current.project_domain_lock_id}",
                    "SUCCESS",
                    "REPLACED_BY_NEW_CURRENT_LOCK",
                    trace_id,
                    scope_ref=f"project://{project_id}",
                    details={"newLockId": str(domain_lock.project_domain_lock_id)},
                )
            )
        events.append(
            self._event(
                "project.domain-lock.created.v1",
                actor,
                f"project-domain-lock://{domain_lock.project_domain_lock_id}",
                "SUCCESS",
                domain_lock.status.value,
                trace_id,
                scope_ref=f"project://{project_id}",
                details={
                    "installationId": str(installation_id),
                    "lockDigest": domain_lock.lock_digest,
                    "runtimeBindingCreated": False,
                    "authorizationEffect": "NONE",
                    "semanticRuntimeReady": False,
                },
            )
        )
        return self._repository.switch_project_domain_lock(
            domain_lock,
            actor_ref=actor.principal.subject_ref,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
            audit_events=tuple(events),
        )

    def list_project_domain_locks(
        self, actor: ActorContext, project_id: UUID, trace_id: str
    ) -> tuple[tuple[ProjectDomainLock, HealthSummary], ...]:
        self._require_project(actor, project_id, Permission.FDS_DOMAIN_LOCK_HISTORY_VIEW, trace_id)
        return tuple(
            (item, self.domain_lock_health(item))
            for item in self._repository.list_project_domain_locks(project_id)
        )

    def list_project_available_installations(
        self, actor: ActorContext, project_id: UUID, trace_id: str
    ) -> tuple[tuple[FdsInstallation, HealthSummary], ...]:
        _, _, _, organization_id = self._require_project(
            actor, project_id, Permission.FDS_DOMAIN_LOCK_MANAGE, trace_id
        )
        return tuple(
            (item, self.installation_health(item))
            for item in self._repository.list_installations(organization_id)
        )

    def get_current_project_domain_lock(
        self, actor: ActorContext, project_id: UUID, trace_id: str
    ) -> tuple[ProjectDomainLock, HealthSummary] | None:
        self._require_project(actor, project_id, Permission.FDS_DOMAIN_LOCK_VIEW, trace_id)
        lock = self._repository.get_current_project_domain_lock(project_id)
        return (lock, self.domain_lock_health(lock)) if lock is not None else None

    def get_project_domain_lock(
        self, actor: ActorContext, lock_id: UUID, trace_id: str
    ) -> tuple[ProjectDomainLock, HealthSummary]:
        lock = self._repository.get_project_domain_lock(lock_id)
        if lock is None or not self._project_allowed(
            actor, lock.project_id, Permission.FDS_DOMAIN_LOCK_HISTORY_VIEW
        ):
            self._hidden(actor, f"project-domain-lock://{lock_id}", trace_id)
        assert lock is not None
        return lock, self.domain_lock_health(lock)

    def package_impacts(
        self, actor: ActorContext, package_version_id: UUID, trace_id: str
    ) -> PackageImpactReport:
        record = self.get_package_version(actor, package_version_id, trace_id)
        installations, locks = self._repository.impacts_for_package_version(package_version_id)
        visible_installations = tuple(
            item
            for item in installations
            if self._can_view_organization_impact(actor, record, item.organization_id)
        )
        visible_locks = tuple(
            item
            for item in locks
            if self._can_view_organization_impact(actor, record, item.organization_id)
        )
        return PackageImpactReport(
            package_version_id=record.package_version_id,
            package_id=record.package_id,
            package_version=record.package_version,
            registry_state=record.state,
            installations=tuple(
                InstallationImpact(
                    installation_id=item.installation_id,
                    organization_id=item.organization_id,
                    root_package_id=item.root_package_id,
                    state=item.state,
                )
                for item in visible_installations
            ),
            project_domain_locks=tuple(
                DomainLockImpact(
                    project_domain_lock_id=item.project_domain_lock_id,
                    project_id=item.project_id,
                    organization_id=item.organization_id,
                    status=item.status,
                )
                for item in visible_locks
            ),
        )

    def installation_health(self, installation: FdsInstallation) -> HealthSummary:
        reasons = self._reference_health_reasons(installation.package_version_refs)
        if installation.state != DomainInstallationState.INSTALLED_DISABLED:
            reasons.append(f"INSTALLATION_{installation.state.value}")
        return HealthSummary(
            health=(
                DerivedHealth.HEALTHY_FOR_SELECTION
                if not reasons
                else DerivedHealth.BLOCKED_FOR_NEW_USE
            ),
            reasons=tuple(sorted(set(reasons))),
        )

    def domain_lock_health(self, domain_lock: ProjectDomainLock) -> HealthSummary:
        reasons = self._reference_health_reasons(domain_lock.package_version_refs)
        installation = self._repository.get_installation(domain_lock.installation_id)
        if installation is None:
            reasons.append("INSTALLATION_MISSING")
        elif installation.state != DomainInstallationState.INSTALLED_DISABLED:
            reasons.append(f"INSTALLATION_{installation.state.value}")
        return HealthSummary(
            health=DerivedHealth.AT_RISK if reasons else DerivedHealth.HEALTHY_FOR_SELECTION,
            reasons=tuple(sorted(set(reasons))),
        )

    def _reference_health_reasons(self, refs: tuple[PackageVersionRef, ...]) -> list[str]:
        reasons: list[str] = []
        for ref in refs:
            record = self._repository.get_package_version(ref.package_version_id)
            if record is None:
                reasons.append(f"{ref.package_id}:REGISTRY_VERSION_MISSING")
                continue
            if record.state != RegistryState.REGISTERED_VALIDATED:
                reasons.append(f"{ref.package_id}:{record.state.value}")
            if (
                record.package_id != ref.package_id
                or record.package_version != ref.package_version
                or record.content_digest != ref.content_digest
                or record.manifest_digest != ref.manifest_digest
            ):
                reasons.append(f"{ref.package_id}:IMMUTABLE_FACT_MISMATCH")
        return reasons

    def _verify_installation_integrity(self, installation: FdsInstallation) -> None:
        manifests = []
        for ref in installation.package_version_refs:
            record = self._repository.get_package_version(ref.package_version_id)
            if record is None:
                raise ForgeOpsError(
                    ErrorCode.REGISTRY_VERSION_NOT_FOUND,
                    "a locked Registry version is unavailable",
                    http_status=409,
                )
            manifests.append(record.manifest)
        issues = verify_dependency_lock(installation.dependency_lock, manifests)
        if issues or installation.lock_digest != installation.dependency_lock.lock_digest:
            raise ForgeOpsError(
                ErrorCode.LOCK_DIGEST_MISMATCH,
                "stored installation lock failed integrity verification",
                details={"issueCodes": [item.code.value for item in issues]},
                http_status=409,
            )

    def _require_visible_usable_record(
        self,
        actor: ActorContext,
        package_version_id: UUID,
        organization_id: UUID,
        trace_id: str,
    ) -> FdsPackageVersionRecord:
        record = self._repository.get_package_version(package_version_id)
        if record is None or not self._record_visible_for_organization(record, organization_id):
            self._hidden(actor, f"fds-package-version://{package_version_id}", trace_id)
        assert record is not None
        if record.state != RegistryState.REGISTERED_VALIDATED:
            raise ForgeOpsError(
                ErrorCode.REGISTRY_STATE_UNAVAILABLE,
                "Registry version is not available for new use",
                http_status=409,
            )
        return record

    @staticmethod
    def _record_visible_for_organization(
        record: FdsPackageVersionRecord, organization_id: UUID
    ) -> bool:
        if record.visibility in {Visibility.PUBLIC, Visibility.PARTNER}:
            return True
        return (
            record.visibility == Visibility.ORGANIZATION_PRIVATE
            and record.owner_organization_id == organization_id
        )

    def _authorize_registration(
        self,
        actor: ActorContext,
        raw_manifest: dict[str, Any],
        owner_organization_id: UUID | None,
        trace_id: str,
    ) -> None:
        visibility = raw_manifest.get("visibility")
        if visibility == Visibility.ORGANIZATION_PRIVATE.value:
            if owner_organization_id is None:
                raise ForgeOpsError(
                    ErrorCode.ORGANIZATION_SCOPE_MISMATCH,
                    "organization-private Registry versions require ownerOrganizationId",
                    http_status=422,
                )
            self._require_same_organization_permission(
                actor, owner_organization_id, Permission.FDS_REGISTRY_MANAGE, trace_id
            )
            return
        self._require_platform(actor, Permission.FDS_REGISTRY_MANAGE, trace_id)

    @staticmethod
    def _validate_owner_boundary(manifest: Any, owner_organization_id: UUID | None) -> None:
        if isinstance(manifest, OrganizationOverlayManifest) and (
            manifest.visibility != Visibility.ORGANIZATION_PRIVATE or owner_organization_id is None
        ):
            raise ForgeOpsError(
                ErrorCode.ORGANIZATION_SCOPE_MISMATCH,
                "Organization Overlay must be organization-private and owned by an Organization",
                http_status=422,
            )
        if manifest.visibility == Visibility.ORGANIZATION_PRIVATE and owner_organization_id is None:
            raise ForgeOpsError(
                ErrorCode.ORGANIZATION_SCOPE_MISMATCH,
                "organization-private Registry version requires an owner Organization",
                http_status=422,
            )
        if (
            manifest.visibility != Visibility.ORGANIZATION_PRIVATE
            and owner_organization_id is not None
        ):
            raise ForgeOpsError(
                ErrorCode.ORGANIZATION_SCOPE_MISMATCH,
                "ownerOrganizationId is reserved for organization-private Registry versions",
                http_status=422,
            )

    def _authorize_record_manage(
        self, actor: ActorContext, record: FdsPackageVersionRecord, trace_id: str
    ) -> None:
        if record.visibility == Visibility.ORGANIZATION_PRIVATE:
            assert record.owner_organization_id is not None
            self._require_same_organization_permission(
                actor, record.owner_organization_id, Permission.FDS_REGISTRY_MANAGE, trace_id
            )
        else:
            self._require_platform(actor, Permission.FDS_REGISTRY_MANAGE, trace_id)

    def _can_view_record(self, actor: ActorContext, record: FdsPackageVersionRecord) -> bool:
        if record.visibility in {Visibility.PUBLIC, Visibility.PARTNER}:
            return self._has_any_permission(actor, Permission.FDS_REGISTRY_VIEW)
        if record.visibility == Visibility.ORGANIZATION_PRIVATE:
            return record.owner_organization_id is not None and self._same_organization_allowed(
                actor, record.owner_organization_id, Permission.FDS_REGISTRY_VIEW
            )
        return self._platform_allowed(actor, Permission.FDS_REGISTRY_VIEW)

    def _can_view_organization_impact(
        self,
        actor: ActorContext,
        record: FdsPackageVersionRecord,
        organization_id: UUID,
    ) -> bool:
        if record.visibility == Visibility.ORGANIZATION_PRIVATE:
            return (
                record.owner_organization_id == organization_id
                and self._same_organization_allowed(
                    actor, organization_id, Permission.FDS_IMPACT_VIEW
                )
            )
        return self._platform_allowed(
            actor, Permission.FDS_IMPACT_VIEW
        ) or self._same_organization_allowed(actor, organization_id, Permission.FDS_IMPACT_VIEW)

    def _require_platform(self, actor: ActorContext, permission: Permission, trace_id: str) -> None:
        if not self._platform_allowed(actor, permission):
            self._denied(actor, "platform://local", trace_id, conceal=False)

    def _require_same_organization_permission(
        self,
        actor: ActorContext,
        organization_id: UUID,
        permission: Permission,
        trace_id: str,
    ) -> Organization:
        organization = self._identities.get_organization(organization_id)
        if organization is None or not self._same_organization_allowed(
            actor, organization_id, permission
        ):
            self._hidden(actor, f"organization://{organization_id}", trace_id)
        assert organization is not None
        if organization.state != OrganizationState.ACTIVE:
            raise ForgeOpsError(
                ErrorCode.ILLEGAL_STATE_TRANSITION,
                "Organization is not active",
                http_status=409,
            )
        return organization

    def _require_organization(
        self,
        actor: ActorContext,
        organization_id: UUID,
        permission: Permission,
        trace_id: str,
    ) -> Organization:
        organization = self._identities.get_organization(organization_id)
        if organization is None or not self._organization_allowed(
            actor, organization_id, permission
        ):
            self._hidden(actor, f"organization://{organization_id}", trace_id)
        assert organization is not None
        if organization.state != OrganizationState.ACTIVE:
            raise ForgeOpsError(
                ErrorCode.ILLEGAL_STATE_TRANSITION,
                "Organization is not active",
                http_status=409,
            )
        return organization

    def _require_project(
        self,
        actor: ActorContext,
        project_id: UUID,
        permission: Permission,
        trace_id: str,
    ) -> tuple[Project, Workspace, Organization, UUID]:
        project = self._identities.get_project(project_id)
        if project is None:
            self._hidden(actor, f"project://{project_id}", trace_id)
        assert project is not None
        workspace = self._identities.get_workspace(project.workspace_id)
        if workspace is None:
            self._hidden(actor, f"project://{project_id}", trace_id)
        assert workspace is not None
        organization = self._identities.get_organization(workspace.organization_id)
        if organization is None or not self._project_allowed(actor, project_id, permission):
            self._hidden(actor, f"project://{project_id}", trace_id)
        assert organization is not None
        if (
            organization.state != OrganizationState.ACTIVE
            or workspace.state != WorkspaceState.ACTIVE
        ):
            raise ForgeOpsError(
                ErrorCode.ILLEGAL_STATE_TRANSITION,
                "Project parent Scope is not active",
                http_status=409,
            )
        return project, workspace, organization, organization.organization_id

    def _platform_allowed(self, actor: ActorContext, permission: Permission) -> bool:
        return self._authorization.decide(
            actor.principal,
            actor.memberships,
            permission,
            resource_ref="platform://local",
            scope_type=ScopeType.PLATFORM,
            scope_id=None,
        ).allowed

    def _organization_allowed(
        self, actor: ActorContext, organization_id: UUID, permission: Permission
    ) -> bool:
        return self._authorization.decide(
            actor.principal,
            actor.memberships,
            permission,
            resource_ref=f"organization://{organization_id}",
            scope_type=ScopeType.ORGANIZATION,
            scope_id=organization_id,
        ).allowed

    def _same_organization_allowed(
        self, actor: ActorContext, organization_id: UUID, permission: Permission
    ) -> bool:
        for membership in actor.memberships:
            if (
                membership.state != MembershipState.ACTIVE
                or membership.scope_id is None
                or permission not in ROLE_PERMISSIONS[membership.role]
            ):
                continue
            if (
                self._identities.organization_id_for_scope(
                    membership.scope_type, membership.scope_id
                )
                == organization_id
            ):
                return True
        return False

    def _project_allowed(
        self, actor: ActorContext, project_id: UUID, permission: Permission
    ) -> bool:
        project = self._identities.get_project(project_id)
        if project is None:
            return False
        workspace = self._identities.get_workspace(project.workspace_id)
        if workspace is None:
            return False
        return self._authorization.decide(
            actor.principal,
            actor.memberships,
            permission,
            resource_ref=f"project://{project_id}",
            scope_type=ScopeType.PROJECT,
            scope_id=project_id,
            ancestor_scope_ids=frozenset({workspace.workspace_id, workspace.organization_id}),
        ).allowed

    @staticmethod
    def _has_any_permission(actor: ActorContext, permission: Permission) -> bool:
        return any(
            membership.state == MembershipState.ACTIVE
            and permission in ROLE_PERMISSIONS[membership.role]
            for membership in actor.memberships
        )

    def _hidden(self, actor: ActorContext, resource_ref: str, trace_id: str) -> None:
        self._denied(actor, resource_ref, trace_id, conceal=True)

    def _idempotent_resource_id(
        self,
        actor: ActorContext,
        operation: str,
        idempotency_key: str,
        request_digest: str,
        expected_resource_type: str,
    ) -> UUID | None:
        replay = self._repository.find_idempotent_resource(
            actor.principal.subject_ref,
            operation,
            idempotency_key,
            request_digest,
        )
        if replay is None:
            return None
        resource_type, resource_id = replay
        if resource_type != expected_resource_type:
            raise self._idempotency_corrupt()
        return resource_id

    @staticmethod
    def _idempotency_corrupt() -> ForgeOpsError:
        return ForgeOpsError(
            ErrorCode.INTERNAL_FAILURE,
            "idempotency record refers to an incompatible or missing resource",
            http_status=500,
        )

    def _denied(
        self, actor: ActorContext, resource_ref: str, trace_id: str, *, conceal: bool
    ) -> None:
        self._audit_failure(
            "domain.policy.decision.v1",
            actor,
            resource_ref,
            "RESOURCE_NOT_VISIBLE" if conceal else "NO_APPLICABLE_GRANT",
            trace_id,
            scope_ref="concealed://resource" if conceal else "platform://local",
        )
        raise ForgeOpsError(
            ErrorCode.RESOURCE_NOT_FOUND if conceal else ErrorCode.FORBIDDEN,
            "resource is not available" if conceal else "permission denied",
            http_status=404 if conceal else 403,
        )

    def _audit_failure(
        self,
        event_type: str,
        actor: ActorContext,
        resource_ref: str,
        reason: str,
        trace_id: str,
        *,
        scope_ref: str = "platform://local",
        details: dict[str, object] | None = None,
    ) -> None:
        self._audit.append(
            self._event(
                event_type,
                actor,
                resource_ref,
                "DENIED",
                reason,
                trace_id,
                scope_ref=scope_ref,
                details=details,
            )
        )

    @staticmethod
    def _record_scope_ref(record: FdsPackageVersionRecord) -> str:
        if record.owner_organization_id is not None:
            return f"organization://{record.owner_organization_id}"
        return "platform://local"

    @staticmethod
    def _event(
        event_type: str,
        actor: ActorContext,
        resource_ref: str,
        result: str,
        reason: str,
        trace_id: str,
        *,
        scope_ref: str,
        details: dict[str, object] | None = None,
    ) -> AuditEvent:
        return AuditEvent(
            event_type=event_type,
            actor_ref=actor.principal.subject_ref,
            resource_ref=resource_ref,
            result=result,
            reason_code=reason,
            trace_id=trace_id,
            requirement_ids=("REQ-FDS-001", "REQ-IAM-001", "REQ-POL-001"),
            test_ids=("TEST-FDS-AUTH-001",),
            details=details or {},
            scope_ref=scope_ref,
            policy_version="identity-access-v1",
        )
