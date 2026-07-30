from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class Environment(StrEnum):
    DEV = "DEV"
    TEST = "TEST"
    INT = "INT"
    PREPROD = "PREPROD"
    PROD = "PROD"


class PackageLifecycleState(StrEnum):
    DISCOVERED = "DISCOVERED"
    VALIDATED = "VALIDATED"
    INSTALLED_DISABLED = "INSTALLED_DISABLED"
    TESTED = "TESTED"
    APPROVED = "APPROVED"
    RELEASED_TO_ENV = "RELEASED_TO_ENV"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    REVOKED = "REVOKED"
    INCOMPATIBLE = "INCOMPATIBLE"


class ReleaseState(StrEnum):
    RELEASED_DISABLED = "RELEASED_DISABLED"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    REVOKED = "REVOKED"


class GenericStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    ARCHIVED = "ARCHIVED"


class Entity(StrictModel):
    id: UUID = Field(default_factory=uuid4)
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Scenario(Entity):
    key: str = Field(pattern=r"^[a-z][a-z0-9-]{2,63}$")
    owner_ref: str
    status: GenericStatus = GenericStatus.DRAFT


class Workflow(Entity):
    scenario_ref: str
    schema_ref: str
    status: GenericStatus = GenericStatus.DRAFT


class Run(Entity):
    scenario_ref: str
    workflow_ref: str
    correlation_id: str
    status: GenericStatus = GenericStatus.DRAFT


class Node(Entity):
    node_type: str
    input_schema_ref: str
    output_schema_ref: str


class Agent(Entity):
    profile_ref: str
    capability_refs: tuple[str, ...] = ()


class Capability(Entity):
    capability_type: str
    schema_ref: str
    status: GenericStatus = GenericStatus.DRAFT


class DataProduct(Entity):
    schema_ref: str
    owner_ref: str
    content_ref: str


class Evidence(Entity):
    schema_ref: str
    content_ref: str
    content_digest: str


class Candidate(Entity):
    run_ref: str
    schema_ref: str
    payload_ref: str
    evidence_refs: tuple[str, ...] = ()


class Simulation(Entity):
    candidate_ref: str
    model_ref: str
    result_ref: str


class Evaluation(Entity):
    candidate_ref: str
    profile_ref: str
    metrics: dict[str, float] = Field(default_factory=dict)
    applicable: bool


class Proposal(Entity):
    candidate_ref: str
    schema_ref: str
    payload_ref: str
    execution_status: str = Field(default="NOT_EXECUTED", pattern="^NOT_EXECUTED$")


class Review(Entity):
    proposal_ref: str
    reviewer_ref: str
    disposition: str


class Outcome(Entity):
    proposal_ref: str
    source_ref: str
    schema_ref: str
    payload: dict[str, Any]
