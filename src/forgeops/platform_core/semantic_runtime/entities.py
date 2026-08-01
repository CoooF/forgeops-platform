from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from forgeops.platform_contracts.domain import StrictModel

SemanticId = Annotated[
    str,
    Field(pattern=r"^[a-z][a-z0-9+.-]*:[^\s]+$", min_length=5, max_length=300),
]
Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


def utc_now() -> datetime:
    return datetime.now(UTC)


class AssetLifecycle(StrEnum):
    DRAFT = "DRAFT"
    VALIDATED_LOCAL_SYNTHETIC = "VALIDATED_LOCAL_SYNTHETIC"
    PUBLISHED_LOCAL_SYNTHETIC = "PUBLISHED_LOCAL_SYNTHETIC"
    WITHDRAWN = "WITHDRAWN"


def lifecycle_transition_allowed(current: AssetLifecycle, target: AssetLifecycle) -> bool:
    return (
        target
        in {
            AssetLifecycle.DRAFT: {AssetLifecycle.VALIDATED_LOCAL_SYNTHETIC},
            AssetLifecycle.VALIDATED_LOCAL_SYNTHETIC: {
                AssetLifecycle.PUBLISHED_LOCAL_SYNTHETIC,
                AssetLifecycle.WITHDRAWN,
            },
            AssetLifecycle.PUBLISHED_LOCAL_SYNTHETIC: {AssetLifecycle.WITHDRAWN},
            AssetLifecycle.WITHDRAWN: set(),
        }[current]
    )


class SemanticPayloadKind(StrEnum):
    ONTOLOGY = "ONTOLOGY"
    TERMINOLOGY = "TERMINOLOGY"
    DATA_MAPPING = "DATA_MAPPING"


class ConceptKind(StrEnum):
    ENTITY = "ENTITY"
    EVENT = "EVENT"
    ATTRIBUTE = "ATTRIBUTE"
    VALUE = "VALUE"
    CATEGORY = "CATEGORY"


class RelationDirection(StrEnum):
    DIRECTED = "DIRECTED"
    BIDIRECTIONAL = "BIDIRECTIONAL"


class Cardinality(StrEnum):
    ONE_TO_ONE = "ONE_TO_ONE"
    ONE_TO_MANY = "ONE_TO_MANY"
    MANY_TO_ONE = "MANY_TO_ONE"
    MANY_TO_MANY = "MANY_TO_MANY"


class ConstraintKind(StrEnum):
    REQUIRED_RELATION = "REQUIRED_RELATION"
    ALLOWED_CONCEPT_KIND = "ALLOWED_CONCEPT_KIND"
    CARDINALITY = "CARDINALITY"
    UNIT_DIMENSION = "UNIT_DIMENSION"
    VALUE_TYPE = "VALUE_TYPE"
    VALUE_ENUM = "VALUE_ENUM"
    VALUE_RANGE = "VALUE_RANGE"


class MappingType(StrEnum):
    EXACT = "EXACT"
    EQUIVALENT = "EQUIVALENT"
    NARROWER = "NARROWER"
    BROADER = "BROADER"


class SemanticNamespace(StrictModel):
    namespace_id: str = Field(alias="namespaceId", pattern=r"^[a-z][a-z0-9.-]+$", max_length=160)
    canonical_uri: str = Field(alias="canonicalUri", pattern=r"^(?:urn:[^\s]+|https://[^\s]+)$")
    owner: str = Field(min_length=1, max_length=160)
    scope: Literal["PUBLIC", "ORGANIZATION_PRIVATE", "SYNTHETIC"]
    default_locale: str = Field(alias="defaultLocale", pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$")
    version: str = Field(pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
    status: Literal["ACTIVE", "DEPRECATED"] = "ACTIVE"
    provenance_ref: str = Field(alias="provenanceRef", min_length=1, max_length=500)


class ConceptDefinition(StrictModel):
    semantic_id: SemanticId = Field(alias="semanticId")
    preferred_label: str = Field(alias="preferredLabel", min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    concept_kind: ConceptKind = Field(alias="conceptKind")
    labels: dict[str, str] = Field(default_factory=dict)
    aliases: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    status: Literal["ACTIVE", "DEPRECATED"] = "ACTIVE"
    version: str = Field(pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
    provenance_ref: str = Field(alias="provenanceRef", min_length=1, max_length=500)
    parent_refs: tuple[SemanticId, ...] = Field(default=(), alias="parentRefs")
    category_refs: tuple[SemanticId, ...] = Field(default=(), alias="categoryRefs")


class RelationDefinition(StrictModel):
    semantic_id: SemanticId = Field(alias="semanticId")
    source_concept_ref: SemanticId = Field(alias="sourceConceptRef")
    target_concept_ref: SemanticId = Field(alias="targetConceptRef")
    direction: RelationDirection
    cardinality: Cardinality
    status: Literal["ACTIVE", "DEPRECATED"] = "ACTIVE"
    provenance_ref: str = Field(alias="provenanceRef", min_length=1, max_length=500)
    external_controlled_ref: bool = Field(default=False, alias="externalControlledRef")


class ConstraintDefinition(StrictModel):
    constraint_id: str = Field(alias="constraintId", pattern=r"^[a-z][a-z0-9.-]+$", max_length=160)
    kind: ConstraintKind
    subject_ref: SemanticId = Field(alias="subjectRef")
    relation_ref: SemanticId | None = Field(default=None, alias="relationRef")
    allowed_concept_kind: ConceptKind | None = Field(default=None, alias="allowedConceptKind")
    min_count: int | None = Field(default=None, alias="minCount", ge=0, le=1000)
    max_count: int | None = Field(default=None, alias="maxCount", ge=0, le=1000)
    unit_dimension: str | None = Field(default=None, alias="unitDimension", max_length=120)
    value_type: Literal["STRING", "INTEGER", "NUMBER", "BOOLEAN"] | None = Field(
        default=None, alias="valueType"
    )
    enum_values: tuple[str, ...] = Field(default=(), alias="enumValues", max_length=100)
    minimum: float | None = None
    maximum: float | None = None
    provenance_ref: str = Field(alias="provenanceRef", min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_expression(self) -> ConstraintDefinition:
        if (
            self.max_count is not None
            and self.min_count is not None
            and self.max_count < self.min_count
        ):
            raise ValueError("maxCount must be greater than or equal to minCount")
        required: dict[ConstraintKind, bool] = {
            ConstraintKind.REQUIRED_RELATION: self.relation_ref is not None,
            ConstraintKind.ALLOWED_CONCEPT_KIND: self.allowed_concept_kind is not None,
            ConstraintKind.CARDINALITY: self.relation_ref is not None
            and (self.min_count is not None or self.max_count is not None),
            ConstraintKind.UNIT_DIMENSION: self.unit_dimension is not None,
            ConstraintKind.VALUE_TYPE: self.value_type is not None,
            ConstraintKind.VALUE_ENUM: bool(self.enum_values),
            ConstraintKind.VALUE_RANGE: self.minimum is not None or self.maximum is not None,
        }
        if not required[self.kind]:
            raise ValueError(f"constraint fields do not express {self.kind.value}")
        return self


class TermDefinition(StrictModel):
    term_id: str = Field(alias="termId", pattern=r"^[a-z][a-z0-9.-]+$", max_length=160)
    preferred_term: str = Field(alias="preferredTerm", min_length=1, max_length=200)
    aliases: tuple[str, ...] = ()
    language: str = Field(pattern=r"^[a-z]{2}$")
    locale: str = Field(pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$")
    normalized_token: str = Field(alias="normalizedToken", min_length=1, max_length=240)
    semantic_id: SemanticId = Field(alias="semanticId")
    valid_from: datetime | None = Field(default=None, alias="validFrom")
    valid_to: datetime | None = Field(default=None, alias="validTo")
    priority: int = Field(default=100, ge=0, le=1000)
    disambiguation_hint: str | None = Field(
        default=None, alias="disambiguationHint", max_length=500
    )
    provenance_ref: str = Field(alias="provenanceRef", min_length=1, max_length=500)
    status: Literal["ACTIVE", "DEPRECATED"] = "ACTIVE"

    @model_validator(mode="after")
    def valid_period(self) -> TermDefinition:
        if self.valid_from and self.valid_to and self.valid_to <= self.valid_from:
            raise ValueError("validTo must be after validFrom")
        return self


class SourceReference(StrictModel):
    source_system: str = Field(alias="sourceSystem", pattern=r"^[a-z][a-z0-9.-]+$", max_length=160)
    ref_type: str = Field(alias="refType", pattern=r"^[a-z][a-z0-9.-]+$", max_length=80)
    object_ref: str = Field(alias="objectRef", min_length=1, max_length=240)
    field_ref: str | None = Field(default=None, alias="fieldRef", max_length=240)
    code: str | None = Field(default=None, max_length=240)


class SemanticMapping(StrictModel):
    mapping_id: str = Field(alias="mappingId", pattern=r"^[a-z][a-z0-9.-]+$", max_length=160)
    source: SourceReference
    source_value_type: str = Field(alias="sourceValueType", min_length=1, max_length=80)
    unit: str | None = Field(default=None, max_length=80)
    time_semantics: str | None = Field(default=None, alias="timeSemantics", max_length=120)
    target_semantic_id: SemanticId = Field(alias="targetSemanticId")
    mapping_type: MappingType = Field(alias="mappingType")
    confidence: Annotated[float, Field(ge=0, le=1)] | None = None
    priority: int = Field(default=100, ge=0, le=1000)
    owner: str = Field(min_length=1, max_length=160)
    provenance_ref: str = Field(alias="provenanceRef", min_length=1, max_length=500)
    valid_from: datetime | None = Field(default=None, alias="validFrom")
    valid_to: datetime | None = Field(default=None, alias="validTo")
    status: Literal["ACTIVE", "DEPRECATED"] = "ACTIVE"

    @model_validator(mode="after")
    def valid_period(self) -> SemanticMapping:
        if self.valid_from and self.valid_to and self.valid_to <= self.valid_from:
            raise ValueError("validTo must be after validFrom")
        return self


class SemanticPayloadDefinition(StrictModel):
    schema_version: Literal["forgeops.semantic/v1"] = Field(alias="schemaVersion")
    payload_kind: SemanticPayloadKind = Field(alias="payloadKind")
    namespaces: tuple[SemanticNamespace, ...] = ()
    concepts: tuple[ConceptDefinition, ...] = ()
    relations: tuple[RelationDefinition, ...] = ()
    constraints: tuple[ConstraintDefinition, ...] = ()
    terms: tuple[TermDefinition, ...] = ()
    mappings: tuple[SemanticMapping, ...] = ()

    @model_validator(mode="after")
    def kind_shape_and_uniqueness(self) -> SemanticPayloadDefinition:
        if self.payload_kind == SemanticPayloadKind.ONTOLOGY and (self.terms or self.mappings):
            raise ValueError("ONTOLOGY payload cannot contain terms or mappings")
        if self.payload_kind == SemanticPayloadKind.TERMINOLOGY and (
            self.concepts or self.relations or self.constraints or self.mappings
        ):
            raise ValueError("TERMINOLOGY payload can contain only namespaces and terms")
        if self.payload_kind == SemanticPayloadKind.DATA_MAPPING and (
            self.namespaces or self.concepts or self.relations or self.constraints or self.terms
        ):
            raise ValueError("DATA_MAPPING payload can contain only mappings")
        identifiers = [item.semantic_id for item in self.concepts] + [
            item.semantic_id for item in self.relations
        ]
        identifiers += [item.constraint_id for item in self.constraints]
        identifiers += [item.term_id for item in self.terms]
        identifiers += [item.mapping_id for item in self.mappings]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("payload identifiers must be unique")
        if self.payload_kind == SemanticPayloadKind.ONTOLOGY:
            concept_ids = {item.semantic_id for item in self.concepts}
            for relation in self.relations:
                if not relation.external_controlled_ref and (
                    relation.source_concept_ref not in concept_ids
                    or relation.target_concept_ref not in concept_ids
                ):
                    raise ValueError(
                        "relation concept refs must resolve within the ontology payload"
                    )
        return self


class SemanticPayloadRecord(StrictModel):
    semantic_payload_id: UUID = Field(default_factory=uuid4, alias="semanticPayloadId")
    package_version_id: UUID = Field(alias="packageVersionId")
    package_id: str = Field(alias="packageId")
    package_version: str = Field(alias="packageVersion")
    component_kind: SemanticPayloadKind = Field(alias="componentKind")
    organization_id: UUID | None = Field(default=None, alias="organizationId")
    definition: SemanticPayloadDefinition
    canonical_payload: str = Field(alias="canonicalPayload")
    payload_digest: Digest = Field(alias="payloadDigest")
    provenance_ref: str = Field(alias="provenanceRef")
    status: AssetLifecycle = AssetLifecycle.VALIDATED_LOCAL_SYNTHETIC
    governance_reason: str | None = Field(default=None, alias="governanceReason")
    governed_at: datetime | None = Field(default=None, alias="governedAt")
    created_by: str = Field(alias="createdBy")
    created_at: datetime = Field(default_factory=utc_now, alias="createdAt")
    updated_at: datetime = Field(default_factory=utc_now, alias="updatedAt")
    version: int = Field(default=1, ge=1)


class QueryStatus(StrEnum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    UNKNOWN = "UNKNOWN"
    DENIED = "DENIED"
    INVALID = "INVALID"


class SemanticQueryType(StrEnum):
    TERM = "TERM"
    SEMANTIC_ID = "SEMANTIC_ID"
    RELATION = "RELATION"
    CONSTRAINT = "CONSTRAINT"
    SOURCE_MAPPING = "SOURCE_MAPPING"


class SemanticReference(StrictModel):
    ref_type: str = Field(alias="refType")
    ref_id: str = Field(alias="refId")
    semantic_id: SemanticId | None = Field(default=None, alias="semanticId")
    package_version_id: UUID = Field(alias="packageVersionId")
    package_id: str = Field(alias="packageId")
    package_version: str = Field(alias="packageVersion")
    payload_digest: Digest = Field(alias="payloadDigest")
    provenance_ref: str = Field(alias="provenanceRef")
    status: str
    value: dict[str, Any]


class SemanticQueryResult(StrictModel):
    schema_version: Literal["forgeops.semantic-query/v1"] = Field(
        default="forgeops.semantic-query/v1", alias="schemaVersion"
    )
    status: QueryStatus
    query_type: SemanticQueryType = Field(alias="queryType")
    canonical_refs: tuple[SemanticReference, ...] = Field(alias="canonicalRefs")
    candidates: tuple[SemanticReference, ...] = ()
    issues: tuple[str, ...] = ()
    project_domain_lock_id: UUID = Field(alias="projectDomainLockId")
    domain_lock_digest: Digest = Field(alias="domainLockDigest")
    audit_correlation: str = Field(alias="auditCorrelation")
    authorization_effect: Literal["NONE"] = Field(default="NONE", alias="authorizationEffect")


class ContextBudget(StrictModel):
    max_items: int = Field(alias="maxItems", ge=1, le=500)
    max_chars: int = Field(alias="maxChars", ge=1, le=100_000)


class ContextRequest(StrictModel):
    purpose: str = Field(min_length=1, max_length=120)
    requested_terms: tuple[str, ...] = Field(default=(), alias="requestedTerms", max_length=100)
    semantic_ids: tuple[SemanticId, ...] = Field(default=(), alias="semanticIds", max_length=100)
    mapping_ids: tuple[str, ...] = Field(default=(), alias="mappingIds", max_length=100)
    knowledge_version_ids: tuple[UUID, ...] = Field(
        default=(), alias="knowledgeVersionIds", max_length=100
    )
    budget: ContextBudget
    locale: str = Field(default="zh-CN", pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$")
    evaluation_time: datetime = Field(alias="evaluationTime")


class ContextManifestRecord(StrictModel):
    context_manifest_id: UUID = Field(default_factory=uuid4, alias="contextManifestId")
    schema_version: Literal["forgeops.context-manifest/v1"] = Field(
        default="forgeops.context-manifest/v1", alias="schemaVersion"
    )
    compiler_version: Literal["semantic-runtime-0.1"] = Field(
        default="semantic-runtime-0.1", alias="compilerVersion"
    )
    organization_id: UUID = Field(alias="organizationId")
    project_id: UUID = Field(alias="projectId")
    actor_ref: str = Field(alias="actorRef")
    purpose: str
    project_domain_lock_id: UUID = Field(alias="projectDomainLockId")
    domain_lock_digest: Digest = Field(alias="domainLockDigest")
    request_digest: Digest = Field(alias="requestDigest")
    included_semantic_refs: tuple[SemanticReference, ...] = Field(alias="includedSemanticRefs")
    included_mapping_refs: tuple[SemanticReference, ...] = Field(alias="includedMappingRefs")
    included_knowledge_refs: tuple[dict[str, Any], ...] = Field(alias="includedKnowledgeRefs")
    unresolved_terms: tuple[str, ...] = Field(alias="unresolvedTerms")
    ambiguous_terms: tuple[dict[str, Any], ...] = Field(alias="ambiguousTerms")
    excluded_refs: tuple[dict[str, str], ...] = Field(alias="excludedRefs")
    truncated: bool
    budget_usage: dict[str, int] = Field(alias="budgetUsage")
    evaluation_time: datetime = Field(alias="evaluationTime")
    compiled_at: datetime = Field(default_factory=utc_now, alias="compiledAt")
    canonical_digest: Digest = Field(alias="canonicalDigest")
    authorization_effect: Literal["NONE"] = Field(default="NONE", alias="authorizationEffect")
    agent_executed: Literal[False] = Field(default=False, alias="agentExecuted")
    model_called: Literal[False] = Field(default=False, alias="modelCalled")
    runtime_binding_created: Literal[False] = Field(default=False, alias="runtimeBindingCreated")


class GroundingStatus(StrEnum):
    VALID = "VALID"
    INVALID = "INVALID"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"


class RelationAssertion(StrictModel):
    relation_semantic_id: SemanticId = Field(alias="relationSemanticId")
    source_semantic_id: SemanticId = Field(alias="sourceSemanticId")
    target_semantic_id: SemanticId = Field(alias="targetSemanticId")


class GroundingCandidate(StrictModel):
    entity_refs: tuple[SemanticId, ...] = Field(default=(), alias="entityRefs")
    relation_assertions: tuple[RelationAssertion, ...] = Field(
        default=(), alias="relationAssertions"
    )
    mapping_refs: tuple[str, ...] = Field(default=(), alias="mappingRefs")
    knowledge_citations: tuple[UUID, ...] = Field(default=(), alias="knowledgeCitations")
    declared_constraint_ids: tuple[str, ...] = Field(default=(), alias="declaredConstraintIds")


class GroundingResultRecord(StrictModel):
    grounding_result_id: UUID = Field(default_factory=uuid4, alias="groundingResultId")
    schema_version: Literal["forgeops.grounding-result/v1"] = Field(
        default="forgeops.grounding-result/v1", alias="schemaVersion"
    )
    context_manifest_id: UUID = Field(alias="contextManifestId")
    context_manifest_digest: Digest = Field(alias="contextManifestDigest")
    project_domain_lock_id: UUID = Field(alias="projectDomainLockId")
    status: GroundingStatus
    issues: tuple[str, ...]
    unresolved_refs: tuple[str, ...] = Field(alias="unresolvedRefs")
    constraint_violations: tuple[str, ...] = Field(alias="constraintViolations")
    digest: Digest
    created_by: str = Field(alias="createdBy")
    created_at: datetime = Field(default_factory=utc_now, alias="createdAt")
    authorization_effect: Literal["NONE"] = Field(default="NONE", alias="authorizationEffect")
    model_called: Literal[False] = Field(default=False, alias="modelCalled")


class ImpactSeverity(StrEnum):
    BREAKING = "BREAKING"
    POTENTIALLY_BREAKING = "POTENTIALLY_BREAKING"
    NON_BREAKING = "NON_BREAKING"
    UNKNOWN = "UNKNOWN"


class ImpactReportRecord(StrictModel):
    impact_report_id: UUID = Field(default_factory=uuid4, alias="impactReportId")
    schema_version: Literal["forgeops.semantic-impact/v1"] = Field(
        default="forgeops.semantic-impact/v1", alias="schemaVersion"
    )
    resource_type: Literal["SEMANTIC", "KNOWLEDGE"] = Field(alias="resourceType")
    from_ref: str = Field(alias="fromRef")
    to_ref: str = Field(alias="toRef")
    changes: dict[str, Any]
    severity: ImpactSeverity
    affected_installations: tuple[str, ...] = Field(alias="affectedInstallations")
    affected_project_domain_locks: tuple[str, ...] = Field(alias="affectedProjectDomainLocks")
    workflow_impact: Literal["NOT_EVALUATED"] = Field(
        default="NOT_EVALUATED", alias="workflowImpact"
    )
    digest: Digest
    created_by: str = Field(alias="createdBy")
    created_at: datetime = Field(default_factory=utc_now, alias="createdAt")
