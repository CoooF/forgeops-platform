from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from forgeops.fds_sdk.canonical import sha256_digest
from forgeops.fds_sdk.models import ComponentKind, PackageKind
from forgeops.platform_adapters.object_storage import ContentAddressedFileStore
from forgeops.platform_contracts.errors import ErrorCode, ForgeOpsError
from forgeops.platform_core.audit import AuditEvent, AuditRepository
from forgeops.platform_core.domain_registry.entities import RegistryState
from forgeops.platform_core.domain_registry.repository import DomainRegistryRepository
from forgeops.platform_core.identity_access.entities import OrganizationState, ScopeType
from forgeops.platform_core.identity_access.policy import AuthorizationService, Permission
from forgeops.platform_core.identity_access.repository import IdentityRepository
from forgeops.platform_core.identity_access.service import ActorContext
from forgeops.platform_core.knowledge_hub.entities import (
    KnowledgeAsset,
    KnowledgeAssetType,
    KnowledgeAssetVersion,
    KnowledgeClassification,
)
from forgeops.platform_core.knowledge_hub.repository import KnowledgeHubRepository
from forgeops.platform_core.semantic_runtime.entities import (
    AssetLifecycle,
    lifecycle_transition_allowed,
)


class KnowledgeHubService:
    """Govern immutable, DomainLock-consumable local-synthetic knowledge versions."""

    def __init__(
        self,
        repository: KnowledgeHubRepository,
        domain_repository: DomainRegistryRepository,
        identities: IdentityRepository,
        audit: AuditRepository,
        object_store: ContentAddressedFileStore,
    ) -> None:
        self._repository = repository
        self._domain_repository = domain_repository
        self._identities = identities
        self._audit = audit
        self._object_store = object_store
        self._authorization = AuthorizationService()

    def create_asset(
        self,
        actor: ActorContext,
        organization_id: UUID,
        *,
        title: str,
        description: str,
        asset_type: KnowledgeAssetType,
        language: str,
        owner: str,
        reviewer: str,
        idempotency_key: str,
        trace_id: str,
    ) -> KnowledgeAsset:
        self._require_organization(actor, organization_id, Permission.KNOWLEDGE_ASSET_MANAGE)
        request_digest = sha256_digest(
            {
                "organizationId": str(organization_id),
                "title": title,
                "description": description,
                "assetType": asset_type,
                "language": language,
                "owner": owner,
                "reviewer": reviewer,
            }
        )
        asset = KnowledgeAsset(
            organization_id=organization_id,
            title=title,
            description=description,
            asset_type=asset_type,
            language=language,
            owner=owner,
            reviewer=reviewer,
            created_by=actor.principal.subject_ref,
        )
        result = self._repository.add_knowledge_asset(
            asset,
            actor_ref=actor.principal.subject_ref,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
        )
        self._audit_success(
            "knowledge.asset.created.v1",
            actor,
            f"knowledge-asset://{result.asset_id}",
            trace_id,
            organization_id,
            {"assetType": result.asset_type.value, "dataMode": "SYNTHETIC_ONLY"},
        )
        return result

    def register_version(
        self,
        actor: ActorContext,
        asset_id: UUID,
        *,
        package_version_id: UUID,
        version_label: str,
        title: str,
        description: str,
        source_ref: str,
        provenance_digest: str,
        license_id: str,
        license_terms: str,
        content_classification: KnowledgeClassification,
        allowed_purposes: tuple[str, ...],
        valid_from: datetime,
        valid_to: datetime | None,
        content_type: Literal["text/plain", "application/json"],
        content: str,
        idempotency_key: str,
        trace_id: str,
    ) -> KnowledgeAssetVersion:
        asset = self._require_asset(actor, asset_id, Permission.KNOWLEDGE_ASSET_MANAGE, trace_id)
        package = self._domain_repository.get_package_version(package_version_id)
        if (
            package is None
            or package.kind != PackageKind.COMPONENT
            or package.component_kind != ComponentKind.KNOWLEDGE
            or package.state != RegistryState.REGISTERED_VALIDATED
            or (
                package.owner_organization_id is not None
                and package.owner_organization_id != asset.organization_id
            )
        ):
            raise ForgeOpsError(
                ErrorCode.KNOWLEDGE_ASSET_INVALID,
                "knowledge version must bind an available KNOWLEDGE Registry component",
                http_status=422,
            )
        payload = content.encode("utf-8")
        if not payload:
            raise ForgeOpsError(
                ErrorCode.KNOWLEDGE_CONTENT_INVALID,
                "knowledge content cannot be empty",
                http_status=422,
            )
        if len(payload) > 16_384:
            raise ForgeOpsError(
                ErrorCode.KNOWLEDGE_CONTENT_TOO_LARGE,
                "knowledge content exceeds the 16 KiB local-synthetic limit",
                http_status=413,
            )
        if content_type == "application/json":
            try:
                json.loads(content)
            except json.JSONDecodeError as exc:
                raise ForgeOpsError(
                    ErrorCode.KNOWLEDGE_CONTENT_INVALID,
                    "application/json knowledge content is invalid",
                    http_status=422,
                ) from exc
        digest = f"sha256:{hashlib.sha256(payload).hexdigest()}"
        if digest != package.content_digest or provenance_digest != package.provenance_digest:
            raise ForgeOpsError(
                ErrorCode.KNOWLEDGE_VERSION_CONFLICT,
                "content or provenance digest differs from the bound Registry immutable facts",
                http_status=409,
            )
        request_digest = sha256_digest(
            {
                "assetId": str(asset_id),
                "packageVersionId": str(package_version_id),
                "versionLabel": version_label,
                "title": title,
                "description": description,
                "sourceRef": source_ref,
                "provenanceDigest": provenance_digest,
                "licenseId": license_id,
                "licenseTerms": license_terms,
                "contentClassification": content_classification,
                "allowedPurposes": allowed_purposes,
                "validFrom": valid_from.isoformat(),
                "validTo": valid_to.isoformat() if valid_to is not None else None,
                "contentType": content_type,
                "contentDigest": digest,
            }
        )
        content_ref = self._object_store.put(payload)
        version = KnowledgeAssetVersion(
            asset_id=asset.asset_id,
            organization_id=asset.organization_id,
            package_version_id=package.package_version_id,
            package_id=package.package_id,
            package_version=package.package_version,
            version_label=version_label,
            title=title,
            description=description,
            asset_type=asset.asset_type,
            language=asset.language,
            owner=asset.owner,
            reviewer=asset.reviewer,
            source_ref=source_ref,
            provenance_digest=provenance_digest,
            license_id=license_id,
            license_terms=license_terms,
            content_classification=content_classification,
            allowed_purposes=allowed_purposes,
            valid_from=valid_from,
            valid_to=valid_to,
            content_ref=content_ref,
            content_type=content_type,
            size_bytes=len(payload),
            content_digest=digest,
            created_by=actor.principal.subject_ref,
        )
        result = self._repository.add_knowledge_version(
            version,
            actor_ref=actor.principal.subject_ref,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
        )
        self._audit_success(
            "knowledge.version.registered.v1",
            actor,
            f"knowledge-version://{result.knowledge_version_id}",
            trace_id,
            asset.organization_id,
            {
                "packageVersionId": str(result.package_version_id),
                "contentDigest": result.content_digest,
                "contentStored": True,
                "contentLogged": False,
            },
        )
        return result

    def transition_version(
        self,
        actor: ActorContext,
        version_id: UUID,
        *,
        target: AssetLifecycle,
        reason: str,
        expected_version: int,
        idempotency_key: str,
        trace_id: str,
    ) -> KnowledgeAssetVersion:
        version = self.get_version(actor, version_id, trace_id)
        self._require_organization(
            actor, version.organization_id, Permission.KNOWLEDGE_ASSET_MANAGE
        )
        operation = f"knowledge-version.{target.value.lower()}"
        request_digest = sha256_digest(
            {"versionId": str(version_id), "target": target, "reason": reason}
        )
        replay = self._repository.find_idempotent_resource(
            actor.principal.subject_ref,
            operation,
            idempotency_key,
            request_digest,
        )
        if replay is not None:
            if replay != ("KNOWLEDGE_VERSION", version_id):
                raise ForgeOpsError(
                    ErrorCode.INTERNAL_FAILURE,
                    "idempotency record refers to an incompatible resource",
                    http_status=500,
                )
            persisted = self._repository.get_knowledge_version(version_id)
            if persisted is None:
                raise ForgeOpsError(
                    ErrorCode.INTERNAL_FAILURE,
                    "idempotency record refers to a missing resource",
                    http_status=500,
                )
            return persisted
        if not lifecycle_transition_allowed(version.status, target):
            if version.status == target:
                self._repository.bind_idempotent_resource(
                    actor.principal.subject_ref,
                    operation,
                    idempotency_key,
                    request_digest,
                    "KNOWLEDGE_VERSION",
                    version_id,
                )
                return version
            raise ForgeOpsError(
                ErrorCode.ILLEGAL_STATE_TRANSITION,
                "knowledge version lifecycle transition is not allowed",
                http_status=409,
            )
        now = datetime.now(UTC)
        updated = version.model_copy(
            update={
                "status": target,
                "withdrawal_reason": reason if target == AssetLifecycle.WITHDRAWN else None,
                "withdrawn_at": now if target == AssetLifecycle.WITHDRAWN else None,
                "updated_at": now,
            }
        )
        result = self._repository.save_knowledge_version(
            updated,
            expected_version=expected_version,
            actor_ref=actor.principal.subject_ref,
            operation=operation,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
        )
        self._audit_success(
            "knowledge.version.transitioned.v1",
            actor,
            f"knowledge-version://{result.knowledge_version_id}",
            trace_id,
            result.organization_id,
            {"status": result.status.value, "reason": reason},
        )
        return result

    def list_assets(
        self, actor: ActorContext, organization_id: UUID, trace_id: str
    ) -> tuple[tuple[KnowledgeAsset, tuple[KnowledgeAssetVersion, ...]], ...]:
        self._require_organization(actor, organization_id, Permission.KNOWLEDGE_ASSET_VIEW)
        return tuple(
            (asset, self._repository.list_knowledge_versions(asset.asset_id))
            for asset in self._repository.list_knowledge_assets(organization_id)
        )

    def get_version(
        self, actor: ActorContext, version_id: UUID, trace_id: str
    ) -> KnowledgeAssetVersion:
        version = self._repository.get_knowledge_version(version_id)
        if version is None or not self._organization_allowed(
            actor, version.organization_id, Permission.KNOWLEDGE_ASSET_VIEW
        ):
            self._hidden(actor, f"knowledge-version://{version_id}", trace_id)
        assert version is not None
        return version

    def content(self, version: KnowledgeAssetVersion) -> bytes:
        try:
            payload = self._object_store.get(version.content_ref)
        except (FileNotFoundError, ValueError) as exc:
            raise ForgeOpsError(
                ErrorCode.KNOWLEDGE_VERSION_UNAVAILABLE,
                "knowledge content is unavailable",
                http_status=409,
            ) from exc
        digest = f"sha256:{hashlib.sha256(payload).hexdigest()}"
        if digest != version.content_digest:
            raise ForgeOpsError(
                ErrorCode.KNOWLEDGE_VERSION_CONFLICT,
                "stored knowledge content failed digest verification",
                http_status=409,
            )
        return payload

    def _require_asset(
        self,
        actor: ActorContext,
        asset_id: UUID,
        permission: Permission,
        trace_id: str,
    ) -> KnowledgeAsset:
        asset = self._repository.get_knowledge_asset(asset_id)
        if asset is None or not self._organization_allowed(
            actor, asset.organization_id, permission
        ):
            self._hidden(actor, f"knowledge-asset://{asset_id}", trace_id)
        assert asset is not None
        return asset

    def _require_organization(
        self, actor: ActorContext, organization_id: UUID, permission: Permission
    ) -> None:
        organization = self._identities.get_organization(organization_id)
        if (
            organization is None
            or organization.state != OrganizationState.ACTIVE
            or not self._organization_allowed(actor, organization_id, permission)
        ):
            self._hidden(actor, f"organization://{organization_id}", "knowledge-hidden")

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

    def _hidden(self, actor: ActorContext, resource_ref: str, trace_id: str) -> None:
        self._audit.append(
            self._event(
                "knowledge.policy.decision.v1",
                actor,
                resource_ref,
                "DENIED",
                "RESOURCE_NOT_VISIBLE",
                trace_id,
                "concealed://resource",
            )
        )
        raise ForgeOpsError(
            ErrorCode.RESOURCE_NOT_FOUND, "resource is not available", http_status=404
        )

    def _audit_success(
        self,
        event_type: str,
        actor: ActorContext,
        resource_ref: str,
        trace_id: str,
        organization_id: UUID,
        details: dict[str, object],
    ) -> None:
        self._audit.append(
            self._event(
                event_type,
                actor,
                resource_ref,
                "SUCCESS",
                "LOCAL_SYNTHETIC",
                trace_id,
                f"organization://{organization_id}",
                details,
            )
        )

    @staticmethod
    def _event(
        event_type: str,
        actor: ActorContext,
        resource_ref: str,
        result: str,
        reason: str,
        trace_id: str,
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
            requirement_ids=("REQ-KNW-001", "REQ-SEM-001", "REQ-POL-001"),
            test_ids=("TEST-KNW-001", "TEST-KNW-AUTH-001"),
            details=details or {},
            scope_ref=scope_ref,
            policy_version="identity-access-v1",
        )
