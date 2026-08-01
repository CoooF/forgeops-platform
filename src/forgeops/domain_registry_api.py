from __future__ import annotations

from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import Depends, FastAPI, Header, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from forgeops.fds_sdk.models import PackageKind, TargetVersions, Visibility
from forgeops.platform_contracts.errors import ErrorCode, ForgeOpsError
from forgeops.platform_core.domain_registry.entities import (
    DomainInstallationState,
    FdsInstallation,
    FdsPackageVersionRecord,
    HealthSummary,
    ProjectDomainLock,
    RegistryState,
)
from forgeops.platform_core.domain_registry.service import DomainRegistryService
from forgeops.platform_core.identity_access.service import ActorContext, IdentityAccessService


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class RegistrySubmission(ApiModel):
    manifest: dict[str, Any]
    owner_organization_id: UUID | None = Field(default=None, alias="ownerOrganizationId")


class GovernanceRequest(ApiModel):
    reason: str = Field(min_length=3, max_length=500)


class InstallationRequest(ApiModel):
    root_package_version_id: UUID = Field(alias="rootPackageVersionId")
    target_versions: TargetVersions = Field(alias="targetVersions")
    include_optional: bool = Field(default=False, alias="includeOptional")


class CompareInstallationRequest(ApiModel):
    to_installation_id: UUID = Field(alias="toInstallationId")


class ProjectDomainLockRequest(ApiModel):
    installation_id: UUID = Field(alias="installationId")
    purpose: str = Field(min_length=3, max_length=500)


def require_domain_actor(
    request: Request,
    x_forgeops_actor: Annotated[str | None, Header()] = None,
) -> ActorContext:
    identity = cast(IdentityAccessService, request.app.state.identity)
    return identity.authenticate(x_forgeops_actor, str(request.state.trace_id))


Actor = Annotated[ActorContext, Depends(require_domain_actor)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)]
IfMatch = Annotated[str, Header(alias="If-Match", min_length=1, max_length=32)]


def _trace_id(request: Request) -> str:
    return str(request.state.trace_id)


def _expected_version(value: str) -> int:
    normalized = value.strip()
    if normalized.startswith("W/"):
        normalized = normalized[2:]
    normalized = normalized.strip('"')
    try:
        version = int(normalized)
    except ValueError as exc:
        raise ForgeOpsError(
            ErrorCode.INPUT_INVALID,
            "If-Match must contain a positive integer resource version",
            http_status=422,
        ) from exc
    if version < 1:
        raise ForgeOpsError(
            ErrorCode.INPUT_INVALID,
            "If-Match must contain a positive integer resource version",
            http_status=422,
        )
    return version


def _page(items: tuple[dict[str, Any], ...], limit: int, offset: int) -> dict[str, Any]:
    return {
        "items": list(items[offset : offset + limit]),
        "total": len(items),
        "limit": limit,
        "offset": offset,
    }


def _package_payload(record: FdsPackageVersionRecord) -> dict[str, Any]:
    facts = record.model_dump(
        mode="json",
        by_alias=True,
        exclude={"state", "governance_reason", "governed_at", "updated_at", "version"},
    )
    return {
        "packageVersionId": str(record.package_version_id),
        "immutableFacts": facts,
        "governance": {
            "state": record.state.value,
            "reason": record.governance_reason,
            "governedAt": (
                record.governed_at.isoformat() if record.governed_at is not None else None
            ),
            "updatedAt": record.updated_at.isoformat(),
            "version": record.version,
        },
        "trustBoundary": "NOT_ENTERPRISE_VERIFIED",
        "runtimeCapabilityEnabled": False,
    }


def _installation_payload(installation: FdsInstallation, health: HealthSummary) -> dict[str, Any]:
    facts = installation.model_dump(
        mode="json",
        by_alias=True,
        exclude={"state", "governance_reason", "updated_at", "version"},
    )
    return {
        "installationId": str(installation.installation_id),
        "immutableFacts": facts,
        "installationState": {
            "state": installation.state.value,
            "reason": installation.governance_reason,
            "updatedAt": installation.updated_at.isoformat(),
            "version": installation.version,
        },
        "derivedHealth": health.model_dump(mode="json", by_alias=True),
    }


def _lock_payload(domain_lock: ProjectDomainLock, health: HealthSummary) -> dict[str, Any]:
    facts = domain_lock.model_dump(
        mode="json",
        by_alias=True,
        exclude={"status", "version"},
    )
    return {
        "projectDomainLockId": str(domain_lock.project_domain_lock_id),
        "immutableFacts": facts,
        "lockState": {"status": domain_lock.status.value, "version": domain_lock.version},
        "derivedHealth": health.model_dump(mode="json", by_alias=True),
    }


def register_domain_registry_routes(app: FastAPI, service: DomainRegistryService) -> None:
    @app.post("/v1/fds/package-versions:validate", tags=["fds-registry"])
    def validate_package_version(
        body: RegistrySubmission, actor: Actor, request: Request
    ) -> dict[str, Any]:
        return service.validate_manifest(
            actor, body.manifest, body.owner_organization_id, _trace_id(request)
        ).model_dump(mode="json", by_alias=True)

    @app.post("/v1/fds/package-versions", status_code=201, tags=["fds-registry"])
    def register_package_version(
        body: RegistrySubmission,
        actor: Actor,
        request: Request,
        idempotency_key: IdempotencyKey,
    ) -> dict[str, Any]:
        record = service.register_package_version(
            actor,
            body.manifest,
            owner_organization_id=body.owner_organization_id,
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
        )
        return _package_payload(record)

    @app.get("/v1/fds/package-versions", tags=["fds-registry"])
    def list_package_versions(
        actor: Actor,
        kind: PackageKind | None = None,
        state: RegistryState | None = None,
        visibility: Visibility | None = None,
        organization: UUID | None = None,
        limit: Limit = 50,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        records = service.list_package_versions(
            actor,
            kind=kind,
            state=state,
            visibility=visibility,
            organization_id=organization,
        )
        return _page(tuple(_package_payload(item) for item in records), limit, offset)

    @app.get("/v1/fds/package-versions/{package_version_id}", tags=["fds-registry"])
    def get_package_version(
        package_version_id: UUID, actor: Actor, request: Request
    ) -> dict[str, Any]:
        return _package_payload(
            service.get_package_version(actor, package_version_id, _trace_id(request))
        )

    def transition_package(
        package_version_id: UUID,
        body: GovernanceRequest,
        actor: ActorContext,
        request: Request,
        idempotency_key: str,
        if_match: str,
        target: RegistryState,
    ) -> dict[str, Any]:
        return _package_payload(
            service.transition_package_version(
                actor,
                package_version_id,
                target=target,
                reason=body.reason,
                expected_version=_expected_version(if_match),
                idempotency_key=idempotency_key,
                trace_id=_trace_id(request),
            )
        )

    @app.post(
        "/v1/fds/package-versions/{package_version_id}:quarantine",
        tags=["fds-registry"],
    )
    def quarantine_package_version(
        package_version_id: UUID,
        body: GovernanceRequest,
        actor: Actor,
        request: Request,
        idempotency_key: IdempotencyKey,
        if_match: IfMatch,
    ) -> dict[str, Any]:
        return transition_package(
            package_version_id,
            body,
            actor,
            request,
            idempotency_key,
            if_match,
            RegistryState.QUARANTINED,
        )

    @app.post(
        "/v1/fds/package-versions/{package_version_id}:withdraw",
        tags=["fds-registry"],
    )
    def withdraw_package_version(
        package_version_id: UUID,
        body: GovernanceRequest,
        actor: Actor,
        request: Request,
        idempotency_key: IdempotencyKey,
        if_match: IfMatch,
    ) -> dict[str, Any]:
        return transition_package(
            package_version_id,
            body,
            actor,
            request,
            idempotency_key,
            if_match,
            RegistryState.WITHDRAWN,
        )

    @app.get(
        "/v1/fds/package-versions/{package_version_id}/impacts",
        tags=["fds-registry"],
    )
    def package_version_impacts(
        package_version_id: UUID, actor: Actor, request: Request
    ) -> dict[str, Any]:
        return service.package_impacts(actor, package_version_id, _trace_id(request)).model_dump(
            mode="json", by_alias=True
        )

    @app.post(
        "/v1/organizations/{organization_id}/domain-installations:preview",
        tags=["fds-installations"],
    )
    def preview_installation(
        organization_id: UUID,
        body: InstallationRequest,
        actor: Actor,
        request: Request,
    ) -> dict[str, Any]:
        installation = service.preview_installation(
            actor,
            organization_id,
            root_package_version_id=body.root_package_version_id,
            target_versions=body.target_versions,
            include_optional=body.include_optional,
            trace_id=_trace_id(request),
        )
        return _installation_payload(installation, service.installation_health(installation))

    @app.post(
        "/v1/organizations/{organization_id}/domain-installations",
        status_code=201,
        tags=["fds-installations"],
    )
    def create_installation(
        organization_id: UUID,
        body: InstallationRequest,
        actor: Actor,
        request: Request,
        idempotency_key: IdempotencyKey,
    ) -> dict[str, Any]:
        installation = service.create_installation(
            actor,
            organization_id,
            root_package_version_id=body.root_package_version_id,
            target_versions=body.target_versions,
            include_optional=body.include_optional,
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
        )
        return _installation_payload(installation, service.installation_health(installation))

    @app.get(
        "/v1/organizations/{organization_id}/domain-installations",
        tags=["fds-installations"],
    )
    def list_installations(
        organization_id: UUID,
        actor: Actor,
        request: Request,
        limit: Limit = 50,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        items = service.list_installations(actor, organization_id, _trace_id(request))
        return _page(
            tuple(_installation_payload(item, health) for item, health in items),
            limit,
            offset,
        )

    @app.get("/v1/domain-installations/{installation_id}", tags=["fds-installations"])
    def get_installation(installation_id: UUID, actor: Actor, request: Request) -> dict[str, Any]:
        installation, health = service.get_installation(actor, installation_id, _trace_id(request))
        return _installation_payload(installation, health)

    @app.get(
        "/v1/domain-installations/{installation_id}/lock",
        tags=["fds-installations"],
    )
    def get_installation_lock(
        installation_id: UUID, actor: Actor, request: Request
    ) -> dict[str, Any]:
        installation, health = service.get_installation(actor, installation_id, _trace_id(request))
        return {
            "installationId": str(installation.installation_id),
            "dependencyLock": installation.dependency_lock.model_dump(mode="json", by_alias=True),
            "packageVersionRefs": [
                item.model_dump(mode="json", by_alias=True)
                for item in installation.package_version_refs
            ],
            "derivedHealth": health.model_dump(mode="json", by_alias=True),
            "authorizationEffect": "NONE",
            "runtimeStateCreated": False,
            "semanticRuntimeReady": False,
        }

    def transition_installation(
        installation_id: UUID,
        body: GovernanceRequest,
        actor: ActorContext,
        request: Request,
        idempotency_key: str,
        if_match: str,
        target: DomainInstallationState,
    ) -> dict[str, Any]:
        installation = service.transition_installation(
            actor,
            installation_id,
            target=target,
            reason=body.reason,
            expected_version=_expected_version(if_match),
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
        )
        return _installation_payload(installation, service.installation_health(installation))

    @app.post(
        "/v1/domain-installations/{installation_id}:disable",
        tags=["fds-installations"],
    )
    def disable_installation(
        installation_id: UUID,
        body: GovernanceRequest,
        actor: Actor,
        request: Request,
        idempotency_key: IdempotencyKey,
        if_match: IfMatch,
    ) -> dict[str, Any]:
        return transition_installation(
            installation_id,
            body,
            actor,
            request,
            idempotency_key,
            if_match,
            DomainInstallationState.DISABLED,
        )

    @app.post(
        "/v1/domain-installations/{installation_id}:revoke",
        tags=["fds-installations"],
    )
    def revoke_installation(
        installation_id: UUID,
        body: GovernanceRequest,
        actor: Actor,
        request: Request,
        idempotency_key: IdempotencyKey,
        if_match: IfMatch,
    ) -> dict[str, Any]:
        return transition_installation(
            installation_id,
            body,
            actor,
            request,
            idempotency_key,
            if_match,
            DomainInstallationState.REVOKED,
        )

    @app.post(
        "/v1/domain-installations/{installation_id}:logical-uninstall",
        tags=["fds-installations"],
    )
    def logically_uninstall_installation(
        installation_id: UUID,
        body: GovernanceRequest,
        actor: Actor,
        request: Request,
        idempotency_key: IdempotencyKey,
        if_match: IfMatch,
    ) -> dict[str, Any]:
        return transition_installation(
            installation_id,
            body,
            actor,
            request,
            idempotency_key,
            if_match,
            DomainInstallationState.LOGICALLY_UNINSTALLED,
        )

    @app.post(
        "/v1/domain-installations/{installation_id}:compare",
        tags=["fds-installations"],
    )
    def compare_installations(
        installation_id: UUID,
        body: CompareInstallationRequest,
        actor: Actor,
        request: Request,
    ) -> dict[str, Any]:
        return service.compare_installations(
            actor, installation_id, body.to_installation_id, _trace_id(request)
        ).model_dump(mode="json", by_alias=True)

    @app.get(
        "/v1/projects/{project_id}/domain-installations",
        tags=["project-domain-locks"],
    )
    def project_installations(project_id: UUID, actor: Actor, request: Request) -> dict[str, Any]:
        items = service.list_project_available_installations(actor, project_id, _trace_id(request))
        return _page(
            tuple(_installation_payload(item, health) for item, health in items),
            100,
            0,
        )

    @app.post(
        "/v1/projects/{project_id}/domain-locks",
        status_code=201,
        tags=["project-domain-locks"],
    )
    def create_project_domain_lock(
        project_id: UUID,
        body: ProjectDomainLockRequest,
        actor: Actor,
        request: Request,
        idempotency_key: IdempotencyKey,
    ) -> dict[str, Any]:
        lock = service.create_project_domain_lock(
            actor,
            project_id,
            installation_id=body.installation_id,
            purpose=body.purpose,
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
        )
        return _lock_payload(lock, service.domain_lock_health(lock))

    @app.get("/v1/projects/{project_id}/domain-locks", tags=["project-domain-locks"])
    def list_project_domain_locks(
        project_id: UUID,
        actor: Actor,
        request: Request,
        limit: Limit = 50,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        items = service.list_project_domain_locks(actor, project_id, _trace_id(request))
        return _page(tuple(_lock_payload(item, health) for item, health in items), limit, offset)

    @app.get(
        "/v1/projects/{project_id}/domain-locks/current",
        tags=["project-domain-locks"],
    )
    def current_project_domain_lock(
        project_id: UUID, actor: Actor, request: Request
    ) -> dict[str, Any] | None:
        current = service.get_current_project_domain_lock(actor, project_id, _trace_id(request))
        if current is None:
            return None
        return _lock_payload(*current)

    @app.get("/v1/project-domain-locks/{lock_id}", tags=["project-domain-locks"])
    def get_project_domain_lock(lock_id: UUID, actor: Actor, request: Request) -> dict[str, Any]:
        lock, health = service.get_project_domain_lock(actor, lock_id, _trace_id(request))
        return _lock_payload(lock, health)
