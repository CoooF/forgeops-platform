from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import UTC, datetime
from typing import Any, ClassVar, Literal
from uuid import UUID

from forgeops.fds_sdk.canonical import canonical_json, sha256_digest
from forgeops.fds_sdk.models import ComponentKind, PackageKind
from forgeops.platform_contracts.errors import ErrorCode, ForgeOpsError
from forgeops.platform_core.audit import AuditEvent, AuditRepository
from forgeops.platform_core.domain_registry.entities import (
    DerivedHealth,
    ProjectDomainLock,
    ProjectDomainLockState,
    RegistryState,
)
from forgeops.platform_core.domain_registry.repository import DomainRegistryRepository
from forgeops.platform_core.domain_registry.service import DomainRegistryService
from forgeops.platform_core.identity_access.entities import (
    OrganizationState,
    ProjectState,
    ScopeType,
    WorkspaceState,
)
from forgeops.platform_core.identity_access.policy import AuthorizationService, Permission
from forgeops.platform_core.identity_access.repository import IdentityRepository
from forgeops.platform_core.identity_access.service import ActorContext
from forgeops.platform_core.knowledge_hub.entities import KnowledgeAssetVersion
from forgeops.platform_core.knowledge_hub.repository import KnowledgeHubRepository
from forgeops.platform_core.knowledge_hub.service import KnowledgeHubService
from forgeops.platform_core.semantic_runtime.entities import (
    AssetLifecycle,
    ContextManifestRecord,
    ContextRequest,
    GroundingCandidate,
    GroundingResultRecord,
    GroundingStatus,
    ImpactReportRecord,
    ImpactSeverity,
    QueryStatus,
    SemanticPayloadDefinition,
    SemanticPayloadKind,
    SemanticPayloadRecord,
    SemanticQueryResult,
    SemanticQueryType,
    SemanticReference,
    SourceReference,
    lifecycle_transition_allowed,
)
from forgeops.platform_core.semantic_runtime.repository import SemanticRuntimeRepository


class SemanticRuntimeService:
    """Deterministic, DomainLock-scoped semantics without an agent or model runtime."""

    _KIND_BINDING: ClassVar[dict[SemanticPayloadKind, ComponentKind]] = {
        SemanticPayloadKind.ONTOLOGY: ComponentKind.ONTOLOGY,
        SemanticPayloadKind.TERMINOLOGY: ComponentKind.TERMINOLOGY,
        SemanticPayloadKind.DATA_MAPPING: ComponentKind.DATA_MAPPING,
    }

    def __init__(
        self,
        repository: SemanticRuntimeRepository,
        knowledge_repository: KnowledgeHubRepository,
        domain_repository: DomainRegistryRepository,
        domain_service: DomainRegistryService,
        identities: IdentityRepository,
        audit: AuditRepository,
        knowledge_service: KnowledgeHubService,
    ) -> None:
        self._repository = repository
        self._knowledge_repository = knowledge_repository
        self._domain_repository = domain_repository
        self._domain_service = domain_service
        self._identities = identities
        self._audit = audit
        self._knowledge_service = knowledge_service
        self._authorization = AuthorizationService()

    def register_payload(
        self,
        actor: ActorContext,
        package_version_id: UUID,
        *,
        definition: SemanticPayloadDefinition,
        idempotency_key: str,
        trace_id: str,
    ) -> SemanticPayloadRecord:
        package = self._domain_repository.get_package_version(package_version_id)
        if package is None:
            self._hidden(actor, f"fds-package-version://{package_version_id}", trace_id)
        assert package is not None
        self._require_semantic_scope(
            actor, package.owner_organization_id, Permission.SEMANTIC_REGISTRY_MANAGE, trace_id
        )
        if (
            package.kind != PackageKind.COMPONENT
            or package.component_kind != self._KIND_BINDING[definition.payload_kind]
            or package.state != RegistryState.REGISTERED_VALIDATED
        ):
            raise ForgeOpsError(
                ErrorCode.SEMANTIC_COMPONENT_KIND_MISMATCH,
                "semantic payload kind must match an available Registry component kind",
                http_status=422,
            )
        self._validate_normalization(definition)
        canonical_payload = canonical_json(definition)
        payload_digest = sha256_digest(definition)
        raw_digest = f"sha256:{hashlib.sha256(canonical_payload.encode('utf-8')).hexdigest()}"
        if raw_digest != package.content_digest:
            raise ForgeOpsError(
                ErrorCode.SEMANTIC_PAYLOAD_DIGEST_CONFLICT,
                "semantic canonical payload digest differs from the Registry immutable content",
                details={
                    "payloadDigest": raw_digest,
                    "registryContentDigest": package.content_digest,
                },
                http_status=409,
            )
        request_digest = sha256_digest(
            {
                "packageVersionId": str(package_version_id),
                "definition": definition,
            }
        )
        existing = self._repository.get_semantic_payload_for_package(package_version_id)
        if existing is not None:
            if existing.payload_digest != payload_digest:
                raise ForgeOpsError(
                    ErrorCode.SEMANTIC_PAYLOAD_DIGEST_CONFLICT,
                    "Registry component already binds a different semantic payload",
                    http_status=409,
                )
            self._repository.bind_idempotent_resource(
                actor.principal.subject_ref,
                "semantic-payload.register",
                idempotency_key,
                request_digest,
                "SEMANTIC_PAYLOAD",
                existing.semantic_payload_id,
            )
            return existing
        payload = SemanticPayloadRecord(
            package_version_id=package.package_version_id,
            package_id=package.package_id,
            package_version=package.package_version,
            component_kind=definition.payload_kind,
            organization_id=package.owner_organization_id,
            definition=definition,
            canonical_payload=canonical_payload,
            payload_digest=payload_digest,
            provenance_ref=package.provenance_ref,
            created_by=actor.principal.subject_ref,
        )
        result = self._repository.add_semantic_payload(
            payload,
            actor_ref=actor.principal.subject_ref,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
        )
        self._audit_success(
            "semantic.payload.registered.v1",
            actor,
            f"semantic-payload://{result.semantic_payload_id}",
            trace_id,
            self._scope_ref(result.organization_id),
            {
                "packageVersionId": str(package_version_id),
                "payloadDigest": result.payload_digest,
                "componentKind": result.component_kind.value,
            },
        )
        return result

    def transition_payload(
        self,
        actor: ActorContext,
        payload_id: UUID,
        *,
        target: AssetLifecycle,
        reason: str,
        expected_version: int,
        idempotency_key: str,
        trace_id: str,
    ) -> SemanticPayloadRecord:
        payload = self.get_payload(actor, payload_id, trace_id)
        self._require_semantic_scope(
            actor, payload.organization_id, Permission.SEMANTIC_REGISTRY_MANAGE, trace_id
        )
        operation = f"semantic-payload.{target.value.lower()}"
        request_digest = sha256_digest(
            {"payloadId": str(payload_id), "target": target, "reason": reason}
        )
        replay = self._repository.find_idempotent_resource(
            actor.principal.subject_ref,
            operation,
            idempotency_key,
            request_digest,
        )
        if replay is not None:
            if replay != ("SEMANTIC_PAYLOAD", payload_id):
                raise ForgeOpsError(
                    ErrorCode.INTERNAL_FAILURE,
                    "idempotency record refers to an incompatible resource",
                    http_status=500,
                )
            persisted = self._repository.get_semantic_payload(payload_id)
            if persisted is None:
                raise ForgeOpsError(
                    ErrorCode.INTERNAL_FAILURE,
                    "idempotency record refers to a missing resource",
                    http_status=500,
                )
            return persisted
        if not lifecycle_transition_allowed(payload.status, target):
            if payload.status == target:
                self._repository.bind_idempotent_resource(
                    actor.principal.subject_ref,
                    operation,
                    idempotency_key,
                    request_digest,
                    "SEMANTIC_PAYLOAD",
                    payload_id,
                )
                return payload
            raise ForgeOpsError(
                ErrorCode.ILLEGAL_STATE_TRANSITION,
                "semantic payload lifecycle transition is not allowed",
                http_status=409,
            )
        updated = payload.model_copy(
            update={
                "status": target,
                "governance_reason": reason,
                "governed_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
        )
        result = self._repository.save_semantic_payload(
            updated,
            expected_version=expected_version,
            actor_ref=actor.principal.subject_ref,
            operation=operation,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
        )
        self._audit_success(
            "semantic.payload.transitioned.v1",
            actor,
            f"semantic-payload://{payload_id}",
            trace_id,
            self._scope_ref(result.organization_id),
            {"status": result.status.value, "reason": reason},
        )
        return result

    def list_payloads(
        self, actor: ActorContext, organization_id: UUID | None, trace_id: str
    ) -> tuple[SemanticPayloadRecord, ...]:
        self._require_semantic_scope(
            actor, organization_id, Permission.SEMANTIC_REGISTRY_VIEW, trace_id
        )
        return tuple(
            payload
            for payload in self._repository.list_semantic_payloads()
            if payload.organization_id is None
            or (organization_id is not None and payload.organization_id == organization_id)
        )

    def get_payload(
        self, actor: ActorContext, payload_id: UUID, trace_id: str
    ) -> SemanticPayloadRecord:
        payload = self._repository.get_semantic_payload(payload_id)
        if payload is None or not self._semantic_scope_allowed(
            actor, payload.organization_id, Permission.SEMANTIC_REGISTRY_VIEW
        ):
            self._hidden(actor, f"semantic-payload://{payload_id}", trace_id)
        assert payload is not None
        return payload

    def query(
        self,
        actor: ActorContext,
        project_id: UUID,
        *,
        query_type: SemanticQueryType,
        value: str | SourceReference,
        evaluation_time: datetime,
        trace_id: str,
    ) -> SemanticQueryResult:
        lock = self._require_current_lock(actor, project_id, Permission.SEMANTIC_QUERY, trace_id)
        refs = self._query_locked(lock, query_type, value, evaluation_time)
        issues: tuple[str, ...]
        if not refs:
            status = QueryStatus.UNKNOWN
            canonical_refs: tuple[SemanticReference, ...] = ()
            candidates: tuple[SemanticReference, ...] = ()
            issues = (self._unknown_issue(query_type),)
        else:
            minimum_priority = min(int(item.value.get("priority", 0)) for item in refs)
            winners = tuple(
                item for item in refs if int(item.value.get("priority", 0)) == minimum_priority
            )
            if len(winners) == 1:
                status = QueryStatus.RESOLVED
                canonical_refs = winners
                candidates = ()
                issues = ()
            else:
                status = QueryStatus.AMBIGUOUS
                canonical_refs = ()
                candidates = winners
                issues = (self._ambiguous_issue(query_type),)
        result = SemanticQueryResult(
            status=status,
            query_type=query_type,
            canonical_refs=canonical_refs,
            candidates=candidates,
            issues=issues,
            project_domain_lock_id=lock.project_domain_lock_id,
            domain_lock_digest=lock.lock_digest,
            audit_correlation=trace_id,
        )
        self._audit_success(
            (
                "semantic.query.ambiguity.v1"
                if result.status == QueryStatus.AMBIGUOUS
                else (
                    "semantic.query.unknown.v1"
                    if result.status == QueryStatus.UNKNOWN
                    else "semantic.query.completed.v1"
                )
            ),
            actor,
            f"project://{project_id}",
            trace_id,
            f"project://{project_id}",
            {
                "queryType": query_type.value,
                "status": result.status.value,
                "candidateCount": len(refs),
                "domainLockDigest": lock.lock_digest,
                "authorizationEffect": "NONE",
            },
        )
        return result

    def project_component_inventory(
        self, actor: ActorContext, project_id: UUID, trace_id: str
    ) -> dict[str, Any]:
        lock = self._require_current_lock(actor, project_id, Permission.SEMANTIC_QUERY, trace_id)
        components: list[dict[str, Any]] = []
        for ref in sorted(lock.package_version_refs, key=lambda item: item.package_id):
            package = self._domain_repository.get_package_version(ref.package_version_id)
            if package is None or package.kind != PackageKind.COMPONENT:
                continue
            semantic = self._repository.get_semantic_payload_for_package(ref.package_version_id)
            knowledge = self._knowledge_repository.get_knowledge_version_for_package(
                ref.package_version_id
            )
            components.append(
                {
                    "packageVersionId": str(ref.package_version_id),
                    "packageId": ref.package_id,
                    "packageVersion": ref.package_version,
                    "componentKind": (
                        package.component_kind.value if package.component_kind else None
                    ),
                    "contentDigest": ref.content_digest,
                    "semanticPayloadId": (str(semantic.semantic_payload_id) if semantic else None),
                    "semanticStatus": semantic.status.value if semantic else None,
                    "knowledgeVersionId": (
                        str(knowledge.knowledge_version_id) if knowledge else None
                    ),
                    "knowledgeStatus": knowledge.status.value if knowledge else None,
                }
            )
        return {
            "projectDomainLockId": str(lock.project_domain_lock_id),
            "domainLockDigest": lock.lock_digest,
            "derivedHealth": "HEALTHY_FOR_SELECTION",
            "components": components,
            "authorizationEffect": "NONE",
            "agentExecuted": False,
            "modelCalled": False,
        }

    def compile_context(
        self,
        actor: ActorContext,
        project_id: UUID,
        context_request: ContextRequest,
        *,
        idempotency_key: str,
        trace_id: str,
    ) -> ContextManifestRecord:
        lock = self._require_current_lock(actor, project_id, Permission.CONTEXT_COMPILE, trace_id)
        if context_request.evaluation_time.tzinfo is None:
            raise ForgeOpsError(
                ErrorCode.EFFECTIVE_PERIOD_INVALID,
                "evaluationTime must include a timezone",
                http_status=422,
            )
        semantic_refs: list[SemanticReference] = []
        mapping_refs: list[SemanticReference] = []
        unresolved: list[str] = []
        ambiguous: list[dict[str, Any]] = []
        excluded: list[dict[str, str]] = []
        for term in sorted(set(context_request.requested_terms), key=self.normalize_term):
            matches = self._query_locked(
                lock, SemanticQueryType.TERM, term, context_request.evaluation_time
            )
            winners = self._minimum_priority(matches)
            if not winners:
                unresolved.append(term)
            elif len(winners) > 1:
                ambiguous.append(
                    {
                        "term": term,
                        "candidateRefs": [item.ref_id for item in winners],
                    }
                )
            else:
                semantic_refs.extend(winners)
                if winners[0].semantic_id is not None:
                    semantic_refs.extend(
                        self._query_locked(
                            lock,
                            SemanticQueryType.SEMANTIC_ID,
                            winners[0].semantic_id,
                            context_request.evaluation_time,
                        )
                    )
        for semantic_id in sorted(set(context_request.semantic_ids)):
            matches = self._query_locked(
                lock,
                SemanticQueryType.SEMANTIC_ID,
                semantic_id,
                context_request.evaluation_time,
            )
            if matches:
                semantic_refs.extend(matches)
            else:
                excluded.append({"ref": semantic_id, "reason": "SEMANTIC_ID_UNKNOWN"})
        for mapping_id in sorted(set(context_request.mapping_ids)):
            matches = self._query_locked(
                lock,
                SemanticQueryType.SOURCE_MAPPING,
                mapping_id,
                context_request.evaluation_time,
            )
            if matches:
                mapping_refs.extend(matches)
            else:
                excluded.append({"ref": mapping_id, "reason": "MAPPING_UNKNOWN"})
        knowledge_refs = self._knowledge_for_context(lock, context_request, excluded)
        candidates: list[tuple[str, SemanticReference | dict[str, Any]]] = []
        candidates.extend(("semantic", item) for item in self._deduplicate_refs(semantic_refs))
        candidates.extend(("mapping", item) for item in self._deduplicate_refs(mapping_refs))
        candidates.extend(("knowledge", item) for item in knowledge_refs)
        included_semantic: list[SemanticReference] = []
        included_mappings: list[SemanticReference] = []
        included_knowledge: list[dict[str, Any]] = []
        used_chars = 0
        for category, item in candidates:
            serialized = canonical_json(item)
            if (
                len(included_semantic) + len(included_mappings) + len(included_knowledge)
                >= context_request.budget.max_items
                or used_chars + len(serialized) > context_request.budget.max_chars
            ):
                excluded.append(
                    {
                        "ref": self._candidate_ref(item),
                        "reason": "CONTEXT_BUDGET_EXCEEDED",
                    }
                )
                continue
            used_chars += len(serialized)
            if category == "semantic":
                assert isinstance(item, SemanticReference)
                included_semantic.append(item)
            elif category == "mapping":
                assert isinstance(item, SemanticReference)
                included_mappings.append(item)
            else:
                assert isinstance(item, dict)
                included_knowledge.append(item)
        request_digest = sha256_digest(
            {
                "actorRef": actor.principal.subject_ref,
                "organizationId": str(lock.organization_id),
                "projectId": str(project_id),
                "projectDomainLockId": str(lock.project_domain_lock_id),
                "domainLockDigest": lock.lock_digest,
                "request": context_request,
            }
        )
        canonical_body = {
            "schemaVersion": "forgeops.context-manifest/v1",
            "compilerVersion": "semantic-runtime-0.1",
            "organizationId": str(lock.organization_id),
            "projectId": str(project_id),
            "actorRef": actor.principal.subject_ref,
            "purpose": context_request.purpose,
            "projectDomainLockId": str(lock.project_domain_lock_id),
            "domainLockDigest": lock.lock_digest,
            "requestDigest": request_digest,
            "includedSemanticRefs": included_semantic,
            "includedMappingRefs": included_mappings,
            "includedKnowledgeRefs": included_knowledge,
            "unresolvedTerms": sorted(unresolved),
            "ambiguousTerms": ambiguous,
            "excludedRefs": excluded,
            "truncated": any(item["reason"] == "CONTEXT_BUDGET_EXCEEDED" for item in excluded),
            "budgetUsage": {
                "items": len(included_semantic) + len(included_mappings) + len(included_knowledge),
                "chars": used_chars,
            },
            "evaluationTime": context_request.model_dump(mode="json", by_alias=True)[
                "evaluationTime"
            ],
            "authorizationEffect": "NONE",
            "agentExecuted": False,
            "modelCalled": False,
            "runtimeBindingCreated": False,
        }
        manifest = ContextManifestRecord(
            organization_id=lock.organization_id,
            project_id=project_id,
            actor_ref=actor.principal.subject_ref,
            purpose=context_request.purpose,
            project_domain_lock_id=lock.project_domain_lock_id,
            domain_lock_digest=lock.lock_digest,
            request_digest=request_digest,
            included_semantic_refs=tuple(included_semantic),
            included_mapping_refs=tuple(included_mappings),
            included_knowledge_refs=tuple(included_knowledge),
            unresolved_terms=tuple(sorted(unresolved)),
            ambiguous_terms=tuple(ambiguous),
            excluded_refs=tuple(excluded),
            truncated=bool(canonical_body["truncated"]),
            budget_usage=canonical_body["budgetUsage"],
            evaluation_time=context_request.evaluation_time,
            canonical_digest=sha256_digest(canonical_body),
        )
        result = self._repository.add_context_manifest(
            manifest,
            actor_ref=actor.principal.subject_ref,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
        )
        self._audit_success(
            "context.manifest.compiled.v1",
            actor,
            f"context-manifest://{result.context_manifest_id}",
            trace_id,
            f"project://{project_id}",
            {
                "canonicalDigest": result.canonical_digest,
                "domainLockDigest": result.domain_lock_digest,
                "itemCount": result.budget_usage["items"],
                "authorizationEffect": "NONE",
                "agentExecuted": False,
                "modelCalled": False,
            },
        )
        return result

    def list_context_manifests(
        self, actor: ActorContext, project_id: UUID, trace_id: str
    ) -> tuple[ContextManifestRecord, ...]:
        self._require_project(actor, project_id, Permission.CONTEXT_COMPILE, trace_id)
        return self._repository.list_context_manifests(project_id)

    def get_context_manifest(
        self, actor: ActorContext, manifest_id: UUID, trace_id: str
    ) -> ContextManifestRecord:
        manifest = self._repository.get_context_manifest(manifest_id)
        if manifest is None or not self._project_allowed(
            actor, manifest.project_id, Permission.CONTEXT_COMPILE
        ):
            self._hidden(actor, f"context-manifest://{manifest_id}", trace_id)
        assert manifest is not None
        if self._manifest_digest(manifest) != manifest.canonical_digest:
            raise ForgeOpsError(
                ErrorCode.CONTEXT_MANIFEST_DIGEST_MISMATCH,
                "stored ContextManifest failed canonical digest verification",
                http_status=409,
            )
        return manifest

    def validate_grounding(
        self,
        actor: ActorContext,
        manifest_id: UUID,
        candidate: GroundingCandidate,
        *,
        idempotency_key: str,
        trace_id: str,
    ) -> GroundingResultRecord:
        manifest = self.get_context_manifest(actor, manifest_id, trace_id)
        self._require_project(actor, manifest.project_id, Permission.GROUNDING_VALIDATE, trace_id)
        semantic_ids = {
            item.semantic_id
            for item in manifest.included_semantic_refs
            if item.semantic_id is not None
        }
        relations = {
            item.semantic_id: item
            for item in manifest.included_semantic_refs
            if item.ref_type == "RELATION" and item.semantic_id is not None
        }
        mappings = {item.ref_id for item in manifest.included_mapping_refs}
        citations = {UUID(item["knowledgeVersionId"]) for item in manifest.included_knowledge_refs}
        constraints = {
            item.ref_id for item in manifest.included_semantic_refs if item.ref_type == "CONSTRAINT"
        }
        unresolved_refs: list[str] = []
        violations: list[str] = []
        for ref in candidate.entity_refs:
            if ref not in semantic_ids:
                unresolved_refs.append(ref)
        for mapping_ref in candidate.mapping_refs:
            if mapping_ref not in mappings:
                unresolved_refs.append(mapping_ref)
        for citation in candidate.knowledge_citations:
            if citation not in citations:
                unresolved_refs.append(str(citation))
        for constraint_id in candidate.declared_constraint_ids:
            if constraint_id not in constraints:
                unresolved_refs.append(constraint_id)
        for assertion in candidate.relation_assertions:
            relation = relations.get(assertion.relation_semantic_id)
            if relation is None:
                unresolved_refs.append(assertion.relation_semantic_id)
                continue
            if (
                relation.value.get("sourceConceptRef") != assertion.source_semantic_id
                or relation.value.get("targetConceptRef") != assertion.target_semantic_id
            ):
                violations.append(f"{assertion.relation_semantic_id}:ENDPOINT_MISMATCH")
        issues: list[str] = []
        if manifest.unresolved_terms or manifest.ambiguous_terms:
            issues.append("CONTEXT_REQUIRES_CLARIFICATION")
        if unresolved_refs:
            issues.append("OUT_OF_CONTEXT_MANIFEST")
        if violations:
            issues.append("CONSTRAINT_VIOLATION")
        if unresolved_refs or violations:
            status = GroundingStatus.INVALID
        elif issues:
            status = GroundingStatus.NEEDS_CLARIFICATION
        else:
            status = GroundingStatus.VALID
        digest_body = {
            "contextManifestId": str(manifest_id),
            "contextManifestDigest": manifest.canonical_digest,
            "candidate": candidate,
            "status": status,
            "issues": issues,
            "unresolvedRefs": sorted(set(unresolved_refs)),
            "constraintViolations": sorted(set(violations)),
        }
        result = GroundingResultRecord(
            context_manifest_id=manifest_id,
            context_manifest_digest=manifest.canonical_digest,
            project_domain_lock_id=manifest.project_domain_lock_id,
            status=status,
            issues=tuple(issues),
            unresolved_refs=tuple(sorted(set(unresolved_refs))),
            constraint_violations=tuple(sorted(set(violations))),
            digest=sha256_digest(digest_body),
            created_by=actor.principal.subject_ref,
        )
        persisted = self._repository.add_grounding_result(
            result,
            actor_ref=actor.principal.subject_ref,
            idempotency_key=idempotency_key,
            request_digest=sha256_digest(digest_body),
        )
        self._audit_success(
            "grounding.validation.completed.v1",
            actor,
            f"grounding-result://{persisted.grounding_result_id}",
            trace_id,
            f"project://{manifest.project_id}",
            {
                "status": persisted.status.value,
                "contextManifestDigest": persisted.context_manifest_digest,
                "modelCalled": False,
                "authorizationEffect": "NONE",
            },
        )
        return persisted

    def analyze_impact(
        self,
        actor: ActorContext,
        resource_type: Literal["SEMANTIC", "KNOWLEDGE"],
        from_id: UUID,
        to_id: UUID,
        *,
        idempotency_key: str,
        trace_id: str,
    ) -> ImpactReportRecord:
        if resource_type == "SEMANTIC":
            before = self.get_payload(actor, from_id, trace_id)
            after = self.get_payload(actor, to_id, trace_id)
            if before.organization_id != after.organization_id:
                self._hidden(actor, f"semantic-payload://{to_id}", trace_id)
            self._require_semantic_scope(
                actor, before.organization_id, Permission.SEMANTIC_IMPACT_VIEW, trace_id
            )
            changes, severity = self._semantic_changes(before, after)
            package_ids = (before.package_version_id, after.package_version_id)
        else:
            before_version = self._knowledge_repository.get_knowledge_version(from_id)
            after_version = self._knowledge_repository.get_knowledge_version(to_id)
            if (
                before_version is None
                or after_version is None
                or before_version.organization_id != after_version.organization_id
                or not self._organization_allowed(
                    actor,
                    before_version.organization_id,
                    Permission.SEMANTIC_IMPACT_VIEW,
                )
            ):
                self._hidden(actor, f"knowledge-version://{to_id}", trace_id)
            assert before_version is not None and after_version is not None
            changes = {
                "contentDigestChanged": (
                    before_version.content_digest != after_version.content_digest
                ),
                "allowedPurposesAdded": sorted(
                    set(after_version.allowed_purposes) - set(before_version.allowed_purposes)
                ),
                "allowedPurposesRemoved": sorted(
                    set(before_version.allowed_purposes) - set(after_version.allowed_purposes)
                ),
                "effectivePeriodChanged": (
                    before_version.valid_from != after_version.valid_from
                    or before_version.valid_to != after_version.valid_to
                ),
            }
            severity = (
                ImpactSeverity.POTENTIALLY_BREAKING
                if changes["contentDigestChanged"]
                or changes["allowedPurposesRemoved"]
                or changes["effectivePeriodChanged"]
                else ImpactSeverity.NON_BREAKING
            )
            package_ids = (
                before_version.package_version_id,
                after_version.package_version_id,
            )
        installation_refs: set[str] = set()
        lock_refs: set[str] = set()
        for package_id in package_ids:
            installations, locks = self._domain_repository.impacts_for_package_version(package_id)
            installation_refs.update(str(item.installation_id) for item in installations)
            lock_refs.update(str(item.project_domain_lock_id) for item in locks)
        body = {
            "resourceType": resource_type,
            "fromRef": str(from_id),
            "toRef": str(to_id),
            "changes": changes,
            "severity": severity,
            "affectedInstallations": sorted(installation_refs),
            "affectedProjectDomainLocks": sorted(lock_refs),
            "workflowImpact": "NOT_EVALUATED",
        }
        report = ImpactReportRecord(
            resource_type=resource_type,
            from_ref=str(from_id),
            to_ref=str(to_id),
            changes=changes,
            severity=severity,
            affected_installations=tuple(sorted(installation_refs)),
            affected_project_domain_locks=tuple(sorted(lock_refs)),
            digest=sha256_digest(body),
            created_by=actor.principal.subject_ref,
        )
        result = self._repository.add_impact_report(
            report,
            actor_ref=actor.principal.subject_ref,
            idempotency_key=idempotency_key,
            request_digest=sha256_digest(body),
        )
        self._audit_success(
            "semantic.impact.analyzed.v1",
            actor,
            f"semantic-impact://{result.impact_report_id}",
            trace_id,
            "platform://local",
            {
                "resourceType": resource_type,
                "severity": result.severity.value,
                "workflowImpact": "NOT_EVALUATED",
            },
        )
        return result

    def list_impacts(self, actor: ActorContext, trace_id: str) -> tuple[ImpactReportRecord, ...]:
        self._require_semantic_scope(actor, None, Permission.SEMANTIC_IMPACT_VIEW, trace_id)
        return self._repository.list_impact_reports()

    def _query_locked(
        self,
        lock: ProjectDomainLock,
        query_type: SemanticQueryType,
        value: str | SourceReference,
        evaluation_time: datetime,
    ) -> tuple[SemanticReference, ...]:
        locked_ids = {item.package_version_id for item in lock.package_version_refs}
        payloads = tuple(
            item
            for item in self._repository.list_semantic_payloads()
            if item.package_version_id in locked_ids
            and item.status == AssetLifecycle.PUBLISHED_LOCAL_SYNTHETIC
            and (item.organization_id is None or item.organization_id == lock.organization_id)
        )
        refs: list[SemanticReference] = []
        for payload in payloads:
            definition = payload.definition
            if query_type == SemanticQueryType.TERM:
                assert isinstance(value, str)
                token = self.normalize_term(value)
                for term in definition.terms:
                    if not self._effective(term.valid_from, term.valid_to, evaluation_time):
                        continue
                    tokens = {term.normalized_token, self.normalize_term(term.preferred_term)}
                    tokens.update(self.normalize_term(alias) for alias in term.aliases)
                    if token in tokens and term.status == "ACTIVE":
                        refs.append(
                            self._reference(payload, "TERM", term.term_id, term.semantic_id, term)
                        )
            elif query_type == SemanticQueryType.SEMANTIC_ID:
                assert isinstance(value, str)
                for concept in definition.concepts:
                    if concept.semantic_id == value and concept.status == "ACTIVE":
                        refs.append(
                            self._reference(
                                payload,
                                "CONCEPT",
                                concept.semantic_id,
                                concept.semantic_id,
                                concept,
                            )
                        )
                for relation in definition.relations:
                    if relation.semantic_id == value and relation.status == "ACTIVE":
                        refs.append(
                            self._reference(
                                payload,
                                "RELATION",
                                relation.semantic_id,
                                relation.semantic_id,
                                relation,
                            )
                        )
                for constraint in definition.constraints:
                    if constraint.subject_ref == value:
                        refs.append(
                            self._reference(
                                payload,
                                "CONSTRAINT",
                                constraint.constraint_id,
                                constraint.subject_ref,
                                constraint,
                            )
                        )
            elif query_type == SemanticQueryType.RELATION:
                assert isinstance(value, str)
                for relation in definition.relations:
                    if relation.semantic_id == value and relation.status == "ACTIVE":
                        refs.append(
                            self._reference(
                                payload,
                                "RELATION",
                                relation.semantic_id,
                                relation.semantic_id,
                                relation,
                            )
                        )
            elif query_type == SemanticQueryType.CONSTRAINT:
                assert isinstance(value, str)
                for constraint in definition.constraints:
                    if constraint.constraint_id == value:
                        refs.append(
                            self._reference(
                                payload,
                                "CONSTRAINT",
                                constraint.constraint_id,
                                constraint.subject_ref,
                                constraint,
                            )
                        )
            else:
                for mapping in definition.mappings:
                    if not self._effective(mapping.valid_from, mapping.valid_to, evaluation_time):
                        continue
                    matches = (
                        mapping.mapping_id == value
                        if isinstance(value, str)
                        else mapping.source == value
                    )
                    if matches and mapping.status == "ACTIVE":
                        refs.append(
                            self._reference(
                                payload,
                                "MAPPING",
                                mapping.mapping_id,
                                mapping.target_semantic_id,
                                mapping,
                            )
                        )
        return tuple(sorted(refs, key=lambda item: (item.ref_id, str(item.package_version_id))))

    def _knowledge_for_context(
        self,
        lock: ProjectDomainLock,
        context_request: ContextRequest,
        excluded: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        locked_ids = {item.package_version_id for item in lock.package_version_refs}
        result: list[dict[str, Any]] = []
        for version_id in sorted(set(context_request.knowledge_version_ids), key=str):
            version = self._knowledge_repository.get_knowledge_version(version_id)
            reason = self._knowledge_exclusion_reason(version, lock, locked_ids, context_request)
            if reason is not None:
                excluded.append({"ref": str(version_id), "reason": reason})
                continue
            assert version is not None
            payload = self._knowledge_service.content(version).decode("utf-8")
            result.append(
                {
                    "knowledgeVersionId": str(version.knowledge_version_id),
                    "assetId": str(version.asset_id),
                    "packageVersionId": str(version.package_version_id),
                    "packageId": version.package_id,
                    "packageVersion": version.package_version,
                    "title": version.title,
                    "contentType": version.content_type,
                    "contentDigest": version.content_digest,
                    "content": payload,
                    "sourceRef": version.source_ref,
                    "provenanceDigest": version.provenance_digest,
                    "licenseId": version.license_id,
                    "contentClassification": version.content_classification.value,
                    "effectiveStatus": version.effective_status(context_request.evaluation_time),
                }
            )
        return result

    @staticmethod
    def _knowledge_exclusion_reason(
        version: KnowledgeAssetVersion | None,
        lock: ProjectDomainLock,
        locked_ids: set[UUID],
        context_request: ContextRequest,
    ) -> str | None:
        if version is None or version.organization_id != lock.organization_id:
            return "KNOWLEDGE_VERSION_UNAVAILABLE"
        if version.package_version_id not in locked_ids:
            return "OUT_OF_DOMAIN_LOCK"
        if version.status != AssetLifecycle.PUBLISHED_LOCAL_SYNTHETIC:
            return "KNOWLEDGE_NOT_PUBLISHED"
        if version.effective_status(context_request.evaluation_time) != (
            AssetLifecycle.PUBLISHED_LOCAL_SYNTHETIC.value
        ):
            return "KNOWLEDGE_NOT_EFFECTIVE"
        if context_request.purpose not in version.allowed_purposes:
            return "PURPOSE_NOT_ALLOWED"
        return None

    def _require_current_lock(
        self,
        actor: ActorContext,
        project_id: UUID,
        permission: Permission,
        trace_id: str,
    ) -> ProjectDomainLock:
        self._require_project(actor, project_id, permission, trace_id)
        lock = self._domain_repository.get_current_project_domain_lock(project_id)
        if lock is None or lock.status != ProjectDomainLockState.CURRENT:
            raise ForgeOpsError(
                ErrorCode.CONTEXT_DOMAIN_LOCK_REQUIRED,
                "a current Project DomainLock is required",
                http_status=409,
            )
        health = self._domain_service.domain_lock_health(lock)
        if health.health != DerivedHealth.HEALTHY_FOR_SELECTION:
            raise ForgeOpsError(
                ErrorCode.CONTEXT_DOMAIN_LOCK_AT_RISK,
                "Project DomainLock is at risk and cannot compile new context",
                details={"reasons": list(health.reasons)},
                http_status=409,
            )
        return lock

    def _require_project(
        self,
        actor: ActorContext,
        project_id: UUID,
        permission: Permission,
        trace_id: str,
    ) -> UUID:
        project = self._identities.get_project(project_id)
        if project is None:
            self._hidden(actor, f"project://{project_id}", trace_id)
        assert project is not None
        workspace = self._identities.get_workspace(project.workspace_id)
        if workspace is None:
            self._hidden(actor, f"project://{project_id}", trace_id)
        assert workspace is not None
        organization = self._identities.get_organization(workspace.organization_id)
        if (
            organization is None
            or organization.state != OrganizationState.ACTIVE
            or workspace.state != WorkspaceState.ACTIVE
            or project.state == ProjectState.ARCHIVED
            or not self._project_allowed(actor, project_id, permission)
        ):
            self._hidden(actor, f"project://{project_id}", trace_id)
        return workspace.organization_id

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

    def _require_semantic_scope(
        self,
        actor: ActorContext,
        organization_id: UUID | None,
        permission: Permission,
        trace_id: str,
    ) -> None:
        if not self._semantic_scope_allowed(actor, organization_id, permission):
            self._hidden(actor, self._scope_ref(organization_id), trace_id)

    def _semantic_scope_allowed(
        self,
        actor: ActorContext,
        organization_id: UUID | None,
        permission: Permission,
    ) -> bool:
        if organization_id is None:
            return self._authorization.decide(
                actor.principal,
                actor.memberships,
                permission,
                resource_ref="platform://local",
                scope_type=ScopeType.PLATFORM,
                scope_id=None,
            ).allowed
        return self._organization_allowed(actor, organization_id, permission)

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

    @staticmethod
    def normalize_term(value: str) -> str:
        return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).casefold()).strip()

    def _validate_normalization(self, definition: SemanticPayloadDefinition) -> None:
        for term in definition.terms:
            declared = term.normalized_token
            valid = {self.normalize_term(term.preferred_term)}
            valid.update(self.normalize_term(alias) for alias in term.aliases)
            if declared not in valid or declared != self.normalize_term(declared):
                raise ForgeOpsError(
                    ErrorCode.SEMANTIC_PAYLOAD_INVALID,
                    "normalizedToken must be a canonical preferred term or alias token",
                    details={"termId": term.term_id},
                    http_status=422,
                )

    @staticmethod
    def _effective(
        valid_from: datetime | None, valid_to: datetime | None, evaluation_time: datetime
    ) -> bool:
        return (valid_from is None or evaluation_time >= valid_from) and (
            valid_to is None or evaluation_time < valid_to
        )

    @staticmethod
    def _reference(
        payload: SemanticPayloadRecord,
        ref_type: str,
        ref_id: str,
        semantic_id: str | None,
        value: Any,
    ) -> SemanticReference:
        dumped = value.model_dump(mode="json", by_alias=True)
        dumped.setdefault("priority", 0)
        return SemanticReference(
            ref_type=ref_type,
            ref_id=ref_id,
            semantic_id=semantic_id,
            package_version_id=payload.package_version_id,
            package_id=payload.package_id,
            package_version=payload.package_version,
            payload_digest=payload.payload_digest,
            provenance_ref=payload.provenance_ref,
            status=str(dumped.get("status", payload.status.value)),
            value=dumped,
        )

    @staticmethod
    def _minimum_priority(
        refs: tuple[SemanticReference, ...],
    ) -> tuple[SemanticReference, ...]:
        if not refs:
            return ()
        minimum = min(int(item.value.get("priority", 0)) for item in refs)
        return tuple(item for item in refs if int(item.value.get("priority", 0)) == minimum)

    @staticmethod
    def _deduplicate_refs(refs: list[SemanticReference]) -> tuple[SemanticReference, ...]:
        index = {(item.ref_type, item.ref_id, item.package_version_id): item for item in refs}
        return tuple(index[key] for key in sorted(index, key=lambda item: str(item)))

    @staticmethod
    def _candidate_ref(item: SemanticReference | dict[str, Any]) -> str:
        if isinstance(item, SemanticReference):
            return item.ref_id
        return str(item.get("knowledgeVersionId", "knowledge"))

    @staticmethod
    def _unknown_issue(query_type: SemanticQueryType) -> str:
        return {
            SemanticQueryType.TERM: ErrorCode.TERM_UNKNOWN.value,
            SemanticQueryType.SOURCE_MAPPING: ErrorCode.MAPPING_UNKNOWN.value,
        }.get(query_type, ErrorCode.SEMANTIC_ID_UNKNOWN.value)

    @staticmethod
    def _ambiguous_issue(query_type: SemanticQueryType) -> str:
        return (
            ErrorCode.MAPPING_AMBIGUOUS.value
            if query_type == SemanticQueryType.SOURCE_MAPPING
            else ErrorCode.TERM_AMBIGUOUS.value
        )

    @staticmethod
    def _manifest_digest(manifest: ContextManifestRecord) -> str:
        body = manifest.model_dump(
            mode="json",
            by_alias=True,
            exclude={"context_manifest_id", "compiled_at", "canonical_digest"},
        )
        return sha256_digest(body)

    @staticmethod
    def _semantic_changes(
        before: SemanticPayloadRecord, after: SemanticPayloadRecord
    ) -> tuple[dict[str, Any], ImpactSeverity]:
        def index(payload: SemanticPayloadRecord) -> dict[str, str]:
            definition = payload.definition
            items = (
                list(definition.concepts)
                + list(definition.relations)
                + list(definition.constraints)
                + list(definition.terms)
                + list(definition.mappings)
            )
            result: dict[str, str] = {}
            for item in items:
                dumped = item.model_dump(mode="json", by_alias=True)
                identifier = next(
                    str(dumped[key])
                    for key in (
                        "semanticId",
                        "constraintId",
                        "termId",
                        "mappingId",
                    )
                    if key in dumped
                )
                result[identifier] = sha256_digest(dumped)
            return result

        old = index(before)
        new = index(after)
        removed = sorted(old.keys() - new.keys())
        added = sorted(new.keys() - old.keys())
        modified = sorted(key for key in old.keys() & new.keys() if old[key] != new[key])
        changes: dict[str, Any] = {
            "added": added,
            "removed": removed,
            "modified": modified,
            "payloadKindChanged": before.component_kind != after.component_kind,
        }
        if removed or changes["payloadKindChanged"]:
            severity = ImpactSeverity.BREAKING
        elif modified:
            severity = ImpactSeverity.POTENTIALLY_BREAKING
        else:
            severity = ImpactSeverity.NON_BREAKING
        return changes, severity

    def _hidden(self, actor: ActorContext, resource_ref: str, trace_id: str) -> None:
        self._audit.append(
            self._event(
                "semantic.policy.decision.v1",
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
        scope_ref: str,
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
                scope_ref,
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
            requirement_ids=(
                "REQ-SEM-001",
                "REQ-KNW-001",
                "REQ-GRD-001",
                "REQ-POL-001",
            ),
            test_ids=("TEST-SEM-001", "TEST-GRD-001", "TEST-SEM-AUTH-001"),
            details=details or {},
            scope_ref=scope_ref,
            policy_version="identity-access-v1",
        )

    @staticmethod
    def _scope_ref(organization_id: UUID | None) -> str:
        return (
            f"organization://{organization_id}"
            if organization_id is not None
            else "platform://local"
        )
