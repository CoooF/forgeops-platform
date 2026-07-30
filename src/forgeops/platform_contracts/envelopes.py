from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from forgeops.platform_contracts.domain import StrictModel


class ContractRef(StrictModel):
    contract_id: str = Field(alias="contractId", min_length=3, max_length=128)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    schema_ref: str = Field(alias="schemaRef", min_length=1)


class ResourceBudget(StrictModel):
    cpu_millis: int = Field(alias="cpuMillis", ge=1, le=16_000)
    memory_mib: int = Field(alias="memoryMiB", ge=16, le=65_536)
    timeout_seconds: int = Field(alias="timeoutSeconds", ge=1, le=86_400)
    max_output_bytes: int = Field(alias="maxOutputBytes", ge=1, le=100_000_000)
    network_access: bool = Field(default=False, alias="networkAccess")
    secret_refs: tuple[str, ...] = Field(default=(), alias="secretRefs")


class ArtifactAttestation(StrictModel):
    artifact_ref: str = Field(alias="artifactRef", min_length=1)
    content_digest: str = Field(alias="contentDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    signature: str = Field(pattern=r"^local-sha256:[0-9a-f]{64}$")
    sbom_ref: str = Field(alias="sbomRef", min_length=1)
    executable: bool = False
    worker_boundary: str | None = Field(default=None, alias="workerBoundary")


class RequestContext(StrictModel):
    request_id: UUID = Field(default_factory=uuid4, alias="requestId")
    trace_id: str = Field(alias="traceId", min_length=8, max_length=64)
    actor_ref: str = Field(alias="actorRef", min_length=1)
    environment: str
    purpose: str = Field(min_length=1)
    granted_permissions: tuple[str, ...] = Field(default=(), alias="grantedPermissions")


class DataProviderRequest(StrictModel):
    context: RequestContext
    requirement: ContractRef
    scope_ref: str = Field(alias="scopeRef")


class DataProviderResult(StrictModel):
    data_product_ref: str = Field(alias="dataProductRef")
    snapshot_ref: str = Field(alias="snapshotRef")
    evidence_refs: tuple[str, ...] = Field(alias="evidenceRefs")


class AgentTaskRequest(StrictModel):
    context: RequestContext
    profile: ContractRef
    input_ref: str = Field(alias="inputRef")
    evidence_refs: tuple[str, ...] = Field(alias="evidenceRefs")
    output_schema_ref: str = Field(alias="outputSchemaRef")
    budget: ResourceBudget


class AgentTaskResult(StrictModel):
    result_ref: str = Field(alias="resultRef")
    evidence_refs: tuple[str, ...] = Field(alias="evidenceRefs")
    trace_ref: str = Field(alias="traceRef")
    degraded_to_template: bool = Field(alias="degradedToTemplate")


class SolverRequest(StrictModel):
    context: RequestContext
    adapter: ContractRef
    problem_ref: str = Field(alias="problemRef")
    objective_ref: str = Field(alias="objectiveRef")
    budget: ResourceBudget


class SolverResult(StrictModel):
    status: str
    candidate_refs: tuple[str, ...] = Field(alias="candidateRefs")
    metric_refs: tuple[str, ...] = Field(alias="metricRefs")
    evidence_refs: tuple[str, ...] = Field(alias="evidenceRefs")


class SimulationRequest(StrictModel):
    context: RequestContext
    model: ContractRef
    snapshot_ref: str = Field(alias="snapshotRef")
    candidate_ref: str = Field(alias="candidateRef")
    seed: int
    budget: ResourceBudget


class SimulationResult(StrictModel):
    result_ref: str = Field(alias="resultRef")
    evidence_refs: tuple[str, ...] = Field(alias="evidenceRefs")
    applicability_ref: str = Field(alias="applicabilityRef")


class EvaluationRequest(StrictModel):
    context: RequestContext
    profile: ContractRef
    candidate_refs: tuple[str, ...] = Field(alias="candidateRefs")
    result_refs: tuple[str, ...] = Field(alias="resultRefs")


class EvaluationResult(StrictModel):
    evaluation_ref: str = Field(alias="evaluationRef")
    hard_gate_passed: bool = Field(alias="hardGatePassed")
    metrics: dict[str, float]
    applicability_ref: str = Field(alias="applicabilityRef")


class NodeExecutionRequest(StrictModel):
    context: RequestContext
    node: ContractRef
    input_ref: str = Field(alias="inputRef")
    output_schema_ref: str = Field(alias="outputSchemaRef")
    budget: ResourceBudget
    idempotency_key: str = Field(alias="idempotencyKey", min_length=8)


class NodeExecutionResult(StrictModel):
    status: str
    output_ref: str = Field(alias="outputRef")
    evidence_refs: tuple[str, ...] = Field(alias="evidenceRefs")
    metadata: dict[str, Any] = Field(default_factory=dict)
