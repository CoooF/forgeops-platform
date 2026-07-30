from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from forgeops.config import ActionAdapterKind, assert_release_adapter
from forgeops.platform_contracts.domain import (
    Environment,
    PackageLifecycleState,
    ReleaseState,
)
from forgeops.platform_contracts.errors import ErrorCode, ForgeOpsError
from forgeops.platform_core.audit import AuditEvent, AuditRepository
from forgeops.platform_core.scenario_registry.entities import (
    EnvironmentReleaseRecord,
    InstallationRecord,
)
from forgeops.platform_core.scenario_registry.repository import (
    InstallationRepository,
    changed_release_state,
    changed_state,
)
from forgeops.scenario_sdk.lifecycle import require_transition
from forgeops.scenario_sdk.validation import ManifestValidator, ValidationReport


class ScenarioPackageService:
    def __init__(
        self,
        repository: InstallationRepository,
        audit: AuditRepository,
        validator: ManifestValidator | None = None,
    ) -> None:
        self._repository = repository
        self._audit = audit
        self._validator = validator or ManifestValidator()

    def validate(self, raw_manifest: dict[str, Any], artifact_payload: bytes) -> ValidationReport:
        package_id = str(raw_manifest.get("packageId", "unknown"))
        previous = self._repository.latest_for_package(package_id)
        return self._validator.validate(
            raw_manifest,
            artifact_payload,
            previous_manifest=previous.manifest if previous else None,
        )

    def install(
        self,
        raw_manifest: dict[str, Any],
        artifact_payload: bytes,
        *,
        actor_ref: str,
        trace_id: str,
    ) -> InstallationRecord:
        package_id = str(raw_manifest.get("packageId", "unknown"))
        package_version = str(raw_manifest.get("packageVersion", "unknown"))
        existing = self._repository.get_by_package_version(package_id, package_version)
        declared_digest = str(raw_manifest.get("artifact", {}).get("contentDigest", ""))
        if existing:
            if existing.content_digest != declared_digest:
                raise ForgeOpsError(
                    ErrorCode.PACKAGE_VERSION_DIGEST_CONFLICT,
                    "the package version already exists with a different digest",
                    http_status=409,
                )
            self._append_audit(
                "scenario.package.install.idempotent.v1",
                actor_ref,
                str(existing.installation_id),
                "UNCHANGED",
                "IDEMPOTENT_REPLAY",
                trace_id,
            )
            return existing

        report = self.validate(raw_manifest, artifact_payload)
        if not report.valid or report.manifest is None:
            first = report.issues[0]
            self._append_audit(
                "scenario.package.compatibility.failed.v1",
                actor_ref,
                f"{package_id}@{package_version}",
                "DENIED",
                first.code.value,
                trace_id,
                details={"issues": [item.model_dump(mode="json") for item in report.issues]},
            )
            raise ForgeOpsError(
                first.code,
                first.message,
                details={"issues": [item.model_dump(mode="json") for item in report.issues]},
                http_status=422,
            )

        record = InstallationRecord(
            package_id=report.manifest.package_id,
            package_version=report.manifest.package_version,
            content_digest=report.manifest.artifact.content_digest,
            manifest=report.manifest,
        )
        saved = self._repository.add(record)
        self._append_audit(
            "scenario.package.installed-disabled.v1",
            actor_ref,
            str(saved.installation_id),
            "SUCCESS",
            saved.state.value,
            trace_id,
        )
        return saved

    def mark_tested(
        self, installation_id: UUID, *, actor_ref: str, trace_id: str
    ) -> InstallationRecord:
        return self._transition(
            installation_id, PackageLifecycleState.TESTED, actor_ref=actor_ref, trace_id=trace_id
        )

    def approve(
        self, installation_id: UUID, *, actor_ref: str, trace_id: str
    ) -> InstallationRecord:
        return self._transition(
            installation_id, PackageLifecycleState.APPROVED, actor_ref=actor_ref, trace_id=trace_id
        )

    def grant_permissions(
        self,
        installation_id: UUID,
        permissions: tuple[str, ...],
        *,
        actor_ref: str,
        trace_id: str,
    ) -> InstallationRecord:
        record = self._require_active_record(installation_id)
        if set(permissions) != set(record.manifest.permissions):
            raise ForgeOpsError(
                ErrorCode.UNAUTHORIZED,
                "the grant must exactly match the validated manifest permissions",
                http_status=409,
            )
        saved = self._repository.save(
            record.model_copy(update={"granted_permissions": tuple(sorted(permissions))})
        )
        self._append_audit(
            "scenario.package.permissions.granted.v1",
            actor_ref,
            str(installation_id),
            "SUCCESS",
            "EXACT_MANIFEST_GRANT",
            trace_id,
        )
        return saved

    def bind(
        self,
        installation_id: UUID,
        binding_ref: str,
        *,
        actor_ref: str,
        trace_id: str,
    ) -> InstallationRecord:
        record = self._require_active_record(installation_id)
        bindings = tuple(sorted(set(record.binding_refs) | {binding_ref}))
        saved = self._repository.save(record.model_copy(update={"binding_refs": bindings}))
        self._append_audit(
            "scenario.package.bound.v1",
            actor_ref,
            str(installation_id),
            "SUCCESS",
            "BINDING_RECORDED",
            trace_id,
            details={"bindingRef": binding_ref},
        )
        return saved

    def release(
        self,
        installation_id: UUID,
        environment: Environment,
        action_adapter: ActionAdapterKind,
        *,
        actor_ref: str,
        trace_id: str,
    ) -> EnvironmentReleaseRecord:
        record = self._require_active_record(installation_id)
        require_transition(record.state, PackageLifecycleState.RELEASED_TO_ENV)
        if set(record.granted_permissions) != set(record.manifest.permissions):
            raise ForgeOpsError(
                ErrorCode.PERMISSION_GRANT_REQUIRED,
                "validated permissions must be explicitly granted before release",
                http_status=409,
            )
        if not record.binding_refs:
            raise ForgeOpsError(
                ErrorCode.BINDING_REQUIRED,
                "at least one explicit binding is required before release",
                http_status=409,
            )
        assert_release_adapter(environment, action_adapter)
        if existing := self._repository.get_release(installation_id, environment):
            return existing
        release = self._repository.add_release(
            EnvironmentReleaseRecord(
                installation_id=installation_id,
                environment=environment,
                action_adapter=action_adapter.value,
            )
        )
        self._repository.save(changed_state(record, PackageLifecycleState.RELEASED_TO_ENV))
        self._append_audit(
            "scenario.package.released.v1",
            actor_ref,
            str(installation_id),
            "SUCCESS",
            "RELEASED_DISABLED",
            trace_id,
            details={"environment": environment.value, "actionAdapter": action_adapter.value},
        )
        return release

    def enable(
        self,
        installation_id: UUID,
        environment: Environment,
        *,
        actor_ref: str,
        trace_id: str,
    ) -> EnvironmentReleaseRecord:
        record = self._require_active_record(installation_id)
        require_transition(record.state, PackageLifecycleState.ENABLED)
        release = self._repository.get_release(installation_id, environment)
        if release is None:
            raise ForgeOpsError(
                ErrorCode.ILLEGAL_STATE_TRANSITION,
                "package must be released to the environment before enablement",
                http_status=409,
            )
        enabled = self._repository.save_release(
            changed_release_state(release, ReleaseState.ENABLED)
        )
        self._repository.save(changed_state(record, PackageLifecycleState.ENABLED))
        self._append_audit(
            "scenario.package.enabled.v1",
            actor_ref,
            str(installation_id),
            "SUCCESS",
            environment.value,
            trace_id,
        )
        return enabled

    def disable(
        self,
        installation_id: UUID,
        environment: Environment,
        *,
        actor_ref: str,
        trace_id: str,
    ) -> EnvironmentReleaseRecord:
        record = self._require_active_record(installation_id)
        require_transition(record.state, PackageLifecycleState.DISABLED)
        release = self._require_release(installation_id, environment)
        disabled = self._repository.save_release(
            changed_release_state(release, ReleaseState.DISABLED)
        )
        self._repository.save(changed_state(record, PackageLifecycleState.DISABLED))
        self._append_audit(
            "scenario.package.disabled.v1",
            actor_ref,
            str(installation_id),
            "SUCCESS",
            environment.value,
            trace_id,
        )
        return disabled

    def revoke(
        self,
        installation_id: UUID,
        environment: Environment,
        *,
        actor_ref: str,
        trace_id: str,
    ) -> EnvironmentReleaseRecord:
        record = self._require_active_record(installation_id)
        require_transition(record.state, PackageLifecycleState.REVOKED)
        release = self._require_release(installation_id, environment)
        revoked = self._repository.save_release(
            changed_release_state(release, ReleaseState.REVOKED)
        )
        self._repository.save(changed_state(record, PackageLifecycleState.REVOKED))
        self._append_audit(
            "scenario.package.revoked.v1",
            actor_ref,
            str(installation_id),
            "SUCCESS",
            environment.value,
            trace_id,
        )
        return revoked

    def uninstall(
        self,
        installation_id: UUID,
        *,
        actor_ref: str,
        trace_id: str,
    ) -> InstallationRecord:
        """Logically uninstall a package without deleting history or audit evidence."""
        record = self._require_record(installation_id)
        if record.uninstalled_at is not None:
            self._append_audit(
                "scenario.package.uninstall.idempotent.v1",
                actor_ref,
                str(installation_id),
                "UNCHANGED",
                "IDEMPOTENT_REPLAY",
                trace_id,
            )
            return record
        if record.state not in {PackageLifecycleState.DISABLED, PackageLifecycleState.REVOKED}:
            raise ForgeOpsError(
                ErrorCode.ILLEGAL_STATE_TRANSITION,
                "package must be disabled or revoked before logical uninstall",
                http_status=409,
            )
        saved = self._repository.save(
            record.model_copy(
                update={
                    "binding_refs": (),
                    "granted_permissions": (),
                    "uninstalled_at": datetime.now(UTC),
                }
            )
        )
        self._append_audit(
            "scenario.package.uninstalled.v1",
            actor_ref,
            str(installation_id),
            "SUCCESS",
            "PRESERVE_HISTORY",
            trace_id,
            details={
                "retainManifest": True,
                "retainAudit": True,
                "retainHistoricalRuns": True,
            },
        )
        return saved

    def assert_new_run_allowed(self, installation_id: UUID, environment: Environment) -> None:
        record = self._require_record(installation_id)
        if record.uninstalled_at is not None:
            raise ForgeOpsError(
                ErrorCode.PACKAGE_UNINSTALLED,
                "package is logically uninstalled; historical metadata is retained",
                http_status=409,
            )
        if record.state == PackageLifecycleState.REVOKED:
            raise ForgeOpsError(ErrorCode.PACKAGE_REVOKED, "package is revoked", http_status=409)
        if record.state == PackageLifecycleState.DISABLED:
            raise ForgeOpsError(ErrorCode.PACKAGE_DISABLED, "package is disabled", http_status=409)
        release = self._repository.get_release(installation_id, environment)
        if (
            record.state != PackageLifecycleState.ENABLED
            or not release
            or release.state != ReleaseState.ENABLED
        ):
            raise ForgeOpsError(
                ErrorCode.PACKAGE_NOT_ENABLED,
                "package is not enabled for new runs in this environment",
                http_status=409,
            )

    def _transition(
        self,
        installation_id: UUID,
        target: PackageLifecycleState,
        *,
        actor_ref: str,
        trace_id: str,
    ) -> InstallationRecord:
        record = self._require_active_record(installation_id)
        require_transition(record.state, target)
        saved = self._repository.save(changed_state(record, target))
        self._append_audit(
            "scenario.package.state.changed.v1",
            actor_ref,
            str(installation_id),
            "SUCCESS",
            target.value,
            trace_id,
        )
        return saved

    def _require_record(self, installation_id: UUID) -> InstallationRecord:
        record = self._repository.get_by_id(installation_id)
        if record is None:
            raise ForgeOpsError(ErrorCode.INPUT_INVALID, "installation not found", http_status=404)
        return record

    def _require_active_record(self, installation_id: UUID) -> InstallationRecord:
        record = self._require_record(installation_id)
        if record.uninstalled_at is not None:
            raise ForgeOpsError(
                ErrorCode.PACKAGE_UNINSTALLED,
                "package is logically uninstalled; historical metadata is retained",
                http_status=409,
            )
        return record

    def _require_release(
        self, installation_id: UUID, environment: Environment
    ) -> EnvironmentReleaseRecord:
        release = self._repository.get_release(installation_id, environment)
        if release is None:
            raise ForgeOpsError(
                ErrorCode.INPUT_INVALID, "environment release not found", http_status=404
            )
        return release

    def _append_audit(
        self,
        event_type: str,
        actor_ref: str,
        resource_ref: str,
        result: str,
        reason_code: str,
        trace_id: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self._audit.append(
            AuditEvent(
                event_type=event_type,
                actor_ref=actor_ref,
                resource_ref=resource_ref,
                result=result,
                reason_code=reason_code,
                trace_id=trace_id,
                requirement_ids=("REQ-PKG-001", "REQ-SDK-001"),
                details=details or {},
            )
        )
