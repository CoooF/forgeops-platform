from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, cast
from uuid import UUID

from fastapi import Depends, FastAPI, Header, Query, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from forgeops.platform_contracts.errors import ErrorCode, ForgeOpsError
from forgeops.platform_core.identity_access.service import ActorContext, IdentityAccessService
from forgeops.platform_core.knowledge_hub.entities import (
    KnowledgeAssetType,
    KnowledgeClassification,
)
from forgeops.platform_core.knowledge_hub.service import KnowledgeHubService
from forgeops.platform_core.semantic_runtime.entities import (
    AssetLifecycle,
    ContextRequest,
    GroundingCandidate,
    SemanticPayloadDefinition,
    SemanticQueryType,
    SourceReference,
)
from forgeops.platform_core.semantic_runtime.service import SemanticRuntimeService


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class SemanticPayloadSubmission(ApiModel):
    package_version_id: UUID = Field(alias="packageVersionId")
    definition: SemanticPayloadDefinition


class LifecycleRequest(ApiModel):
    reason: str = Field(min_length=3, max_length=500)


class KnowledgeAssetSubmission(ApiModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    asset_type: KnowledgeAssetType = Field(alias="assetType")
    language: str = Field(pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$")
    owner: str = Field(min_length=1, max_length=160)
    reviewer: str = Field(min_length=1, max_length=160)


class KnowledgeVersionSubmission(ApiModel):
    package_version_id: UUID = Field(alias="packageVersionId")
    version_label: str = Field(
        alias="versionLabel",
        pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$",
    )
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    source_ref: str = Field(alias="sourceRef", min_length=1, max_length=500)
    provenance_digest: str = Field(alias="provenanceDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    license_id: str = Field(alias="licenseId", min_length=1, max_length=120)
    license_terms: str = Field(alias="licenseTerms", min_length=1, max_length=1000)
    content_classification: KnowledgeClassification = Field(alias="contentClassification")
    allowed_purposes: tuple[str, ...] = Field(alias="allowedPurposes", min_length=1, max_length=50)
    valid_from: datetime = Field(alias="validFrom")
    valid_to: datetime | None = Field(default=None, alias="validTo")
    content_type: Literal["text/plain", "application/json"] = Field(alias="contentType")
    content: str = Field(min_length=1, max_length=16_384)


class SemanticQueryRequest(ApiModel):
    query_type: SemanticQueryType = Field(alias="queryType")
    value: str | None = Field(default=None, min_length=1, max_length=300)
    source: SourceReference | None = None
    evaluation_time: datetime = Field(alias="evaluationTime")

    @model_validator(mode="after")
    def selector_matches_query(self) -> SemanticQueryRequest:
        source_query = self.query_type == SemanticQueryType.SOURCE_MAPPING
        if source_query and (self.value is None) == (self.source is None):
            raise ValueError("SOURCE_MAPPING requires exactly one value or source selector")
        if not source_query and (self.value is None or self.source is not None):
            raise ValueError("semantic query requires value and does not accept source")
        return self


class ImpactRequest(ApiModel):
    resource_type: Literal["SEMANTIC", "KNOWLEDGE"] = Field(alias="resourceType")
    from_id: UUID = Field(alias="fromId")
    to_id: UUID = Field(alias="toId")


def require_semantic_actor(
    request: Request,
    x_forgeops_actor: Annotated[str | None, Header()] = None,
) -> ActorContext:
    identity = cast(IdentityAccessService, request.app.state.identity)
    return identity.authenticate(x_forgeops_actor, str(request.state.trace_id))


Actor = Annotated[ActorContext, Depends(require_semantic_actor)]
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)]
IfMatch = Annotated[str, Header(alias="If-Match", min_length=1, max_length=32)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


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


def _dump(value: BaseModel) -> dict[str, Any]:
    return value.model_dump(mode="json", by_alias=True)


def register_semantic_knowledge_routes(
    app: FastAPI,
    semantic: SemanticRuntimeService,
    knowledge: KnowledgeHubService,
) -> None:
    @app.post("/v1/semantic/payloads", status_code=201, tags=["semantic-registry"])
    def register_payload(
        body: SemanticPayloadSubmission,
        actor: Actor,
        request: Request,
        idempotency_key: IdempotencyKey,
    ) -> dict[str, Any]:
        return _dump(
            semantic.register_payload(
                actor,
                body.package_version_id,
                definition=body.definition,
                idempotency_key=idempotency_key,
                trace_id=_trace_id(request),
            )
        )

    @app.get("/v1/semantic/payloads", tags=["semantic-registry"])
    def list_payloads(
        actor: Actor,
        request: Request,
        organization: UUID | None = None,
        limit: Limit = 50,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        items = semantic.list_payloads(actor, organization, _trace_id(request))
        return _page(tuple(_dump(item) for item in items), limit, offset)

    @app.get("/v1/semantic/payloads/{payload_id}", tags=["semantic-registry"])
    def get_payload(payload_id: UUID, actor: Actor, request: Request) -> dict[str, Any]:
        return _dump(semantic.get_payload(actor, payload_id, _trace_id(request)))

    def transition_payload(
        payload_id: UUID,
        target: AssetLifecycle,
        body: LifecycleRequest,
        actor: ActorContext,
        request: Request,
        idempotency_key: str,
        if_match: str,
    ) -> dict[str, Any]:
        return _dump(
            semantic.transition_payload(
                actor,
                payload_id,
                target=target,
                reason=body.reason,
                expected_version=_expected_version(if_match),
                idempotency_key=idempotency_key,
                trace_id=_trace_id(request),
            )
        )

    @app.post("/v1/semantic/payloads/{payload_id}:publish", tags=["semantic-registry"])
    def publish_payload(
        payload_id: UUID,
        body: LifecycleRequest,
        actor: Actor,
        request: Request,
        idempotency_key: IdempotencyKey,
        if_match: IfMatch,
    ) -> dict[str, Any]:
        return transition_payload(
            payload_id,
            AssetLifecycle.PUBLISHED_LOCAL_SYNTHETIC,
            body,
            actor,
            request,
            idempotency_key,
            if_match,
        )

    @app.post("/v1/semantic/payloads/{payload_id}:withdraw", tags=["semantic-registry"])
    def withdraw_payload(
        payload_id: UUID,
        body: LifecycleRequest,
        actor: Actor,
        request: Request,
        idempotency_key: IdempotencyKey,
        if_match: IfMatch,
    ) -> dict[str, Any]:
        return transition_payload(
            payload_id,
            AssetLifecycle.WITHDRAWN,
            body,
            actor,
            request,
            idempotency_key,
            if_match,
        )

    @app.post(
        "/v1/organizations/{organization_id}/knowledge-assets",
        status_code=201,
        tags=["knowledge-hub"],
    )
    def create_knowledge_asset(
        organization_id: UUID,
        body: KnowledgeAssetSubmission,
        actor: Actor,
        request: Request,
        idempotency_key: IdempotencyKey,
    ) -> dict[str, Any]:
        return _dump(
            knowledge.create_asset(
                actor,
                organization_id,
                title=body.title,
                description=body.description,
                asset_type=body.asset_type,
                language=body.language,
                owner=body.owner,
                reviewer=body.reviewer,
                idempotency_key=idempotency_key,
                trace_id=_trace_id(request),
            )
        )

    @app.get("/v1/organizations/{organization_id}/knowledge-assets", tags=["knowledge-hub"])
    def list_knowledge_assets(
        organization_id: UUID,
        actor: Actor,
        request: Request,
        limit: Limit = 50,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        assets = knowledge.list_assets(actor, organization_id, _trace_id(request))
        items = tuple(
            {
                **_dump(asset),
                "versions": [_dump(version) for version in versions],
            }
            for asset, versions in assets
        )
        return _page(items, limit, offset)

    @app.post(
        "/v1/knowledge-assets/{asset_id}/versions",
        status_code=201,
        tags=["knowledge-hub"],
    )
    def register_knowledge_version(
        asset_id: UUID,
        body: KnowledgeVersionSubmission,
        actor: Actor,
        request: Request,
        idempotency_key: IdempotencyKey,
    ) -> dict[str, Any]:
        return _dump(
            knowledge.register_version(
                actor,
                asset_id,
                package_version_id=body.package_version_id,
                version_label=body.version_label,
                title=body.title,
                description=body.description,
                source_ref=body.source_ref,
                provenance_digest=body.provenance_digest,
                license_id=body.license_id,
                license_terms=body.license_terms,
                content_classification=body.content_classification,
                allowed_purposes=body.allowed_purposes,
                valid_from=body.valid_from,
                valid_to=body.valid_to,
                content_type=body.content_type,
                content=body.content,
                idempotency_key=idempotency_key,
                trace_id=_trace_id(request),
            )
        )

    @app.get("/v1/knowledge-versions/{version_id}", tags=["knowledge-hub"])
    def get_knowledge_version(version_id: UUID, actor: Actor, request: Request) -> dict[str, Any]:
        return _dump(knowledge.get_version(actor, version_id, _trace_id(request)))

    @app.get("/v1/knowledge-versions/{version_id}/content", tags=["knowledge-hub"])
    def get_knowledge_content(
        version_id: UUID,
        actor: Actor,
        request: Request,
        max_chars: Annotated[int, Query(alias="maxChars", ge=1, le=16_384)] = 4096,
    ) -> dict[str, Any]:
        version = knowledge.get_version(actor, version_id, _trace_id(request))
        content = knowledge.content(version).decode("utf-8")
        return {
            "knowledgeVersionId": str(version.knowledge_version_id),
            "contentType": version.content_type,
            "contentDigest": version.content_digest,
            "content": content[:max_chars],
            "truncated": len(content) > max_chars,
            "untrustedData": True,
            "executed": False,
        }

    def transition_knowledge(
        version_id: UUID,
        target: AssetLifecycle,
        body: LifecycleRequest,
        actor: ActorContext,
        request: Request,
        idempotency_key: str,
        if_match: str,
    ) -> dict[str, Any]:
        return _dump(
            knowledge.transition_version(
                actor,
                version_id,
                target=target,
                reason=body.reason,
                expected_version=_expected_version(if_match),
                idempotency_key=idempotency_key,
                trace_id=_trace_id(request),
            )
        )

    @app.post("/v1/knowledge-versions/{version_id}:publish", tags=["knowledge-hub"])
    def publish_knowledge_version(
        version_id: UUID,
        body: LifecycleRequest,
        actor: Actor,
        request: Request,
        idempotency_key: IdempotencyKey,
        if_match: IfMatch,
    ) -> dict[str, Any]:
        return transition_knowledge(
            version_id,
            AssetLifecycle.PUBLISHED_LOCAL_SYNTHETIC,
            body,
            actor,
            request,
            idempotency_key,
            if_match,
        )

    @app.post("/v1/knowledge-versions/{version_id}:withdraw", tags=["knowledge-hub"])
    def withdraw_knowledge_version(
        version_id: UUID,
        body: LifecycleRequest,
        actor: Actor,
        request: Request,
        idempotency_key: IdempotencyKey,
        if_match: IfMatch,
    ) -> dict[str, Any]:
        return transition_knowledge(
            version_id,
            AssetLifecycle.WITHDRAWN,
            body,
            actor,
            request,
            idempotency_key,
            if_match,
        )

    @app.get("/v1/projects/{project_id}/semantic-components", tags=["semantic-query"])
    def project_semantic_components(
        project_id: UUID, actor: Actor, request: Request
    ) -> dict[str, Any]:
        return semantic.project_component_inventory(actor, project_id, _trace_id(request))

    @app.post("/v1/projects/{project_id}/semantic-query", tags=["semantic-query"])
    def project_semantic_query(
        project_id: UUID,
        body: SemanticQueryRequest,
        actor: Actor,
        request: Request,
    ) -> dict[str, Any]:
        selector: str | SourceReference = body.source or body.value or ""
        return _dump(
            semantic.query(
                actor,
                project_id,
                query_type=body.query_type,
                value=selector,
                evaluation_time=body.evaluation_time,
                trace_id=_trace_id(request),
            )
        )

    @app.post(
        "/v1/projects/{project_id}/context-manifests",
        status_code=201,
        tags=["context-grounding"],
    )
    def compile_context(
        project_id: UUID,
        body: ContextRequest,
        actor: Actor,
        request: Request,
        idempotency_key: IdempotencyKey,
    ) -> dict[str, Any]:
        return _dump(
            semantic.compile_context(
                actor,
                project_id,
                body,
                idempotency_key=idempotency_key,
                trace_id=_trace_id(request),
            )
        )

    @app.get("/v1/projects/{project_id}/context-manifests", tags=["context-grounding"])
    def list_context_manifests(
        project_id: UUID,
        actor: Actor,
        request: Request,
        limit: Limit = 50,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        items = semantic.list_context_manifests(actor, project_id, _trace_id(request))
        return _page(tuple(_dump(item) for item in items), limit, offset)

    @app.get("/v1/context-manifests/{manifest_id}", tags=["context-grounding"])
    def get_context_manifest(manifest_id: UUID, actor: Actor, request: Request) -> dict[str, Any]:
        return _dump(semantic.get_context_manifest(actor, manifest_id, _trace_id(request)))

    @app.post(
        "/v1/context-manifests/{manifest_id}/grounding-validations",
        status_code=201,
        tags=["context-grounding"],
    )
    def validate_grounding(
        manifest_id: UUID,
        body: GroundingCandidate,
        actor: Actor,
        request: Request,
        idempotency_key: IdempotencyKey,
    ) -> dict[str, Any]:
        return _dump(
            semantic.validate_grounding(
                actor,
                manifest_id,
                body,
                idempotency_key=idempotency_key,
                trace_id=_trace_id(request),
            )
        )

    @app.post("/v1/semantic-impacts", status_code=201, tags=["semantic-impact"])
    def analyze_impact(
        body: ImpactRequest,
        actor: Actor,
        request: Request,
        idempotency_key: IdempotencyKey,
    ) -> dict[str, Any]:
        return _dump(
            semantic.analyze_impact(
                actor,
                body.resource_type,
                body.from_id,
                body.to_id,
                idempotency_key=idempotency_key,
                trace_id=_trace_id(request),
            )
        )

    @app.get("/v1/semantic-impacts", tags=["semantic-impact"])
    def list_impacts(
        actor: Actor,
        request: Request,
        limit: Limit = 50,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        items = semantic.list_impacts(actor, _trace_id(request))
        return _page(tuple(_dump(item) for item in items), limit, offset)
