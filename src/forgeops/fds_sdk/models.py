from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, model_validator

from forgeops.platform_contracts.domain import StrictModel
from forgeops.platform_contracts.envelopes import ArtifactAttestation
from forgeops.platform_contracts.errors import ErrorCode

FDS_API_VERSION = "forgeops.ai/fds/v1alpha1"
FDS_CONTRACT_VERSION = "0.1.0"
LOCK_FORMAT_VERSION = "forgeops.ai/fds-lock/v1alpha1"
COMPATIBILITY_REPORT_VERSION = "forgeops.ai/fds-compatibility/v1alpha1"

Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
PackageId = Annotated[
    str,
    Field(pattern=r"^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)+$", min_length=3, max_length=128),
]
StrictVersion = Annotated[str, Field(pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")]
Capability = Annotated[str, Field(pattern=r"^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)+$")]
Namespace = Annotated[str, Field(pattern=r"^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)+$")]


class PackageKind(StrEnum):
    DOMAIN = "DOMAIN"
    ORGANIZATION_OVERLAY = "ORGANIZATION_OVERLAY"
    SCENARIO = "SCENARIO"
    COMPONENT = "COMPONENT"


class ComponentKind(StrEnum):
    ONTOLOGY = "ONTOLOGY"
    TERMINOLOGY = "TERMINOLOGY"
    KNOWLEDGE = "KNOWLEDGE"
    AGENT_PROFILE = "AGENT_PROFILE"
    SKILL = "SKILL"
    MCP_SERVER = "MCP_SERVER"
    CONNECTOR = "CONNECTOR"
    DATA_MAPPING = "DATA_MAPPING"
    POLICY = "POLICY"
    EVALUATION = "EVALUATION"
    UI_EXTENSION = "UI_EXTENSION"


class Visibility(StrEnum):
    PUBLIC = "PUBLIC"
    PARTNER = "PARTNER"
    ORGANIZATION_PRIVATE = "ORGANIZATION_PRIVATE"
    PRIVATE = "PRIVATE"


class TrustTier(StrEnum):
    FIRST_PARTY_LOCAL = "FIRST_PARTY_LOCAL"
    ENTERPRISE_APPROVED = "ENTERPRISE_APPROVED"
    THIRD_PARTY_SIGNED = "THIRD_PARTY_SIGNED"


class ContentClassification(StrEnum):
    SYNTHETIC = "SYNTHETIC"
    PUBLIC = "PUBLIC"
    ORGANIZATION_PRIVATE = "ORGANIZATION_PRIVATE"


class SupportStatus(StrEnum):
    EXPERIMENTAL = "EXPERIMENTAL"
    SUPPORTED = "SUPPORTED"
    DEPRECATED = "DEPRECATED"
    WITHDRAWN = "WITHDRAWN"


class RuntimeForm(StrEnum):
    METADATA_ONLY = "METADATA_ONLY"
    DECLARATIVE = "DECLARATIVE"
    ISOLATED_WORKER = "ISOLATED_WORKER"
    REMOTE_REFERENCE = "REMOTE_REFERENCE"


class LicenseMetadata(StrictModel):
    license_id: str = Field(alias="licenseId", min_length=1, max_length=120)
    license_ref: str | None = Field(default=None, alias="licenseRef")
    redistribution_allowed: bool = Field(default=False, alias="redistributionAllowed")
    derivative_work_allowed: bool = Field(default=False, alias="derivativeWorkAllowed")
    verified: bool = False


class Provenance(StrictModel):
    source_ref: str = Field(alias="sourceRef", min_length=1)
    provenance_digest: Digest = Field(alias="provenanceDigest")
    synthetic: Literal[True]


class Compatibility(StrictModel):
    platform: str = Field(min_length=1)
    fds: str = Field(min_length=1)
    scenario_sdk: str = Field(alias="scenarioSdk", min_length=1)


class RequestedResourceBudget(StrictModel):
    cpu_millis: int = Field(default=0, alias="cpuMillis", ge=0, le=16_000)
    memory_mib: int = Field(default=0, alias="memoryMiB", ge=0, le=65_536)
    timeout_seconds: int = Field(default=0, alias="timeoutSeconds", ge=0, le=86_400)
    max_output_bytes: int = Field(default=0, alias="maxOutputBytes", ge=0, le=100_000_000)
    network_access: bool = Field(default=False, alias="networkAccess")
    secret_refs: tuple[str, ...] = Field(default=(), alias="secretRefs")


class LifecyclePolicy(StrictModel):
    disable_policy: Literal["PRESERVE_HISTORY"] = Field(
        default="PRESERVE_HISTORY", alias="disablePolicy"
    )
    uninstall_policy: Literal["PRESERVE_HISTORY"] = Field(
        default="PRESERVE_HISTORY", alias="uninstallPolicy"
    )
    retain_manifest: Literal[True] = Field(default=True, alias="retainManifest")
    retain_audit: Literal[True] = Field(default=True, alias="retainAudit")
    retain_historical_runs: Literal[True] = Field(default=True, alias="retainHistoricalRuns")


class PackageRef(StrictModel):
    package_id: PackageId = Field(alias="packageId")
    version_constraint: str = Field(alias="versionConstraint", min_length=1)
    expected_kind: PackageKind | None = Field(default=None, alias="expectedKind")
    expected_capability: Capability | None = Field(default=None, alias="expectedCapability")
    content_digest: Digest | None = Field(default=None, alias="contentDigest")


class ComponentRef(StrictModel):
    package: PackageRef
    component_kind: ComponentKind = Field(alias="componentKind")


class DependencyRequirement(StrictModel):
    package: PackageRef
    required: bool = True
    expected_component_kind: ComponentKind | None = Field(
        default=None, alias="expectedComponentKind"
    )


class ConflictDeclaration(StrictModel):
    package_id: PackageId | None = Field(default=None, alias="packageId")
    version_constraint: str | None = Field(default=None, alias="versionConstraint")
    capability: Capability | None = None

    @model_validator(mode="after")
    def target_is_present(self) -> ConflictDeclaration:
        if self.package_id is None and self.capability is None:
            raise ValueError("conflict requires packageId or capability")
        if self.version_constraint is not None and self.package_id is None:
            raise ValueError("versionConstraint requires packageId")
        return self


class LegacyManifestReference(StrictModel):
    category: str
    contract_id: str = Field(alias="contractId")
    version: StrictVersion
    schema_ref: str = Field(alias="schemaRef")
    artifact_digest: Digest | None = Field(default=None, alias="artifactDigest")


class LegacyScenarioSource(StrictModel):
    manifest_version: str = Field(alias="manifestVersion")
    scenario_sdk: str = Field(alias="scenarioSdk")
    manifest_digest: Digest = Field(alias="manifestDigest")
    references: tuple[LegacyManifestReference, ...]
    compatibility_limitations: tuple[str, ...] = Field(alias="compatibilityLimitations")


class CommonManifest(StrictModel):
    api_version: Literal["forgeops.ai/fds/v1alpha1"] = Field(alias="apiVersion")
    kind: PackageKind
    package_id: PackageId = Field(alias="packageId")
    package_version: StrictVersion = Field(alias="packageVersion")
    publisher: str = Field(min_length=1, max_length=160)
    namespace_owner: str = Field(alias="namespaceOwner", min_length=1, max_length=160)
    license: LicenseMetadata
    provenance: Provenance
    visibility: Visibility
    trust_tier: TrustTier = Field(alias="trustTier")
    content_classification: ContentClassification = Field(alias="contentClassification")
    public_release_approved: bool = Field(default=False, alias="publicReleaseApproved")
    content_digest: Digest = Field(alias="contentDigest")
    artifact: ArtifactAttestation
    compatibility: Compatibility
    applicability: tuple[str, ...]
    prohibited_uses: tuple[str, ...] = Field(alias="prohibitedUses")
    support_status: SupportStatus = Field(alias="supportStatus")
    permissions: tuple[str, ...]
    resource_budget: RequestedResourceBudget = Field(alias="resourceBudget")
    accepted_dependency_permissions: tuple[str, ...] = Field(alias="acceptedDependencyPermissions")
    dependency_resource_budget_allowance: RequestedResourceBudget = Field(
        alias="dependencyResourceBudgetAllowance"
    )
    lifecycle: LifecyclePolicy
    evaluation_refs: tuple[str, ...] = Field(alias="evaluationRefs")
    dependencies: tuple[DependencyRequirement, ...]
    conflicts: tuple[ConflictDeclaration, ...]
    provided_capabilities: tuple[Capability, ...] = Field(alias="providedCapabilities")
    provided_namespaces: tuple[Namespace, ...] = Field(alias="providedNamespaces")


class DomainManifest(CommonManifest):
    kind: Literal[PackageKind.DOMAIN]
    domain_namespace: Namespace = Field(alias="domainNamespace")
    extends: tuple[PackageRef, ...]
    imports: tuple[PackageRef, ...]
    components: tuple[ComponentRef, ...]
    competency_question_refs: tuple[str, ...] = Field(alias="competencyQuestionRefs")


class OrganizationOverlayManifest(CommonManifest):
    kind: Literal[PackageKind.ORGANIZATION_OVERLAY]
    overrides_domain_capabilities: tuple[Capability, ...] = Field(
        alias="overridesDomainCapabilities"
    )
    allowed_override_kinds: tuple[ComponentKind, ...] = Field(alias="allowedOverrideKinds")
    components: tuple[ComponentRef, ...]


class ScenarioDescriptor(CommonManifest):
    kind: Literal[PackageKind.SCENARIO]
    required_domain_capabilities: tuple[Capability, ...] = Field(alias="requiredDomainCapabilities")
    components: tuple[ComponentRef, ...]
    input_contract_digest: Digest | None = Field(alias="inputContractDigest")
    output_contract_digest: Digest | None = Field(alias="outputContractDigest")
    legacy_source: LegacyScenarioSource | None = Field(default=None, alias="legacySource")


class ComponentManifest(CommonManifest):
    kind: Literal[PackageKind.COMPONENT]
    component_kind: ComponentKind = Field(alias="componentKind")
    runtime_form: RuntimeForm = Field(alias="runtimeForm")
    applicable_domain_capabilities: tuple[Capability, ...] = Field(
        alias="applicableDomainCapabilities"
    )


type FdsManifest = (
    DomainManifest | OrganizationOverlayManifest | ScenarioDescriptor | ComponentManifest
)
FDS_MANIFEST_ADAPTER: TypeAdapter[FdsManifest] = TypeAdapter(
    Annotated[FdsManifest, Field(discriminator="kind")]
)


class FdsValidationIssue(StrictModel):
    code: ErrorCode
    message: str
    path: str = "$"


class FdsValidationReport(StrictModel):
    valid: bool
    manifest: FdsManifest | None = None
    normalized_manifest: str | None = Field(default=None, alias="normalizedManifest")
    manifest_digest: Digest | None = Field(default=None, alias="manifestDigest")
    issues: tuple[FdsValidationIssue, ...] = ()


class TargetVersions(StrictModel):
    platform: StrictVersion
    fds: StrictVersion
    scenario_sdk: StrictVersion = Field(alias="scenarioSdk")


class LockedNode(StrictModel):
    package_id: PackageId = Field(alias="packageId")
    package_version: StrictVersion = Field(alias="packageVersion")
    kind: PackageKind
    component_kind: ComponentKind | None = Field(default=None, alias="componentKind")
    source_ref: str = Field(alias="sourceRef")
    publisher: str
    content_digest: Digest = Field(alias="contentDigest")


class LockedEdge(StrictModel):
    from_package_id: PackageId = Field(alias="fromPackageId")
    to_package_id: PackageId = Field(alias="toPackageId")
    version_constraint: str = Field(alias="versionConstraint")
    required: bool


class DependencyLock(StrictModel):
    lock_version: Literal["forgeops.ai/fds-lock/v1alpha1"] = Field(alias="lockVersion")
    root_package_id: PackageId = Field(alias="rootPackageId")
    root_package_version: StrictVersion = Field(alias="rootPackageVersion")
    target_versions: TargetVersions = Field(alias="targetVersions")
    nodes: tuple[LockedNode, ...]
    edges: tuple[LockedEdge, ...]
    skipped_optional_dependencies: tuple[PackageId, ...] = Field(
        alias="skippedOptionalDependencies"
    )
    requested_permissions: tuple[str, ...] = Field(alias="requestedPermissions")
    permission_delta: tuple[str, ...] = Field(alias="permissionDelta")
    accepted_dependency_permissions: tuple[str, ...] = Field(alias="acceptedDependencyPermissions")
    resource_budget: RequestedResourceBudget = Field(alias="resourceBudget")
    resource_budget_delta: RequestedResourceBudget = Field(alias="resourceBudgetDelta")
    authorization_effect: Literal["NONE"] = Field(default="NONE", alias="authorizationEffect")
    runtime_state_created: Literal[False] = Field(default=False, alias="runtimeStateCreated")
    lock_digest: Digest = Field(alias="lockDigest")


class ResolutionReport(StrictModel):
    valid: bool
    lock: DependencyLock | None = None
    issues: tuple[FdsValidationIssue, ...] = ()


class CompatibilityStatus(StrEnum):
    COMPATIBLE_WITH_LIMITATIONS = "COMPATIBLE_WITH_LIMITATIONS"
    INCOMPATIBLE = "INCOMPATIBLE"


class CompatibilityReport(StrictModel):
    report_version: Literal["forgeops.ai/fds-compatibility/v1alpha1"] = Field(alias="reportVersion")
    status: CompatibilityStatus
    source_package_id: str | None = Field(alias="sourcePackageId")
    source_package_version: str | None = Field(alias="sourcePackageVersion")
    source_manifest_digest: Digest = Field(alias="sourceManifestDigest")
    descriptor_digest: Digest | None = Field(alias="descriptorDigest")
    legacy_scenario_sdk: str | None = Field(alias="legacyScenarioSdk")
    resolver_ready: Literal[False] = Field(default=False, alias="resolverReady")
    history_mutated: Literal[False] = Field(default=False, alias="historyMutated")
    limitations: tuple[str, ...]
    issues: tuple[FdsValidationIssue, ...]
    report_digest: Digest = Field(alias="reportDigest")


class LegacyAdaptationResult(StrictModel):
    descriptor: ScenarioDescriptor | None
    report: CompatibilityReport
