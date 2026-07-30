from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID, uuid4

from pydantic import Field

from forgeops.platform_contracts.domain import StrictModel
from forgeops.platform_contracts.errors import ErrorCode, ForgeOpsError
from forgeops.platform_core.audit import AuditEvent, AuditRepository


class ActionProposal(StrictModel):
    proposal_id: UUID = Field(default_factory=uuid4, alias="proposalId")
    schema_ref: str = Field(alias="schemaRef")
    payload_ref: str = Field(alias="payloadRef")
    execution_status: str = Field(default="NOT_EXECUTED", pattern="^NOT_EXECUTED$")


class ActionProposalAdapter(Protocol):
    def record(self, proposal: ActionProposal) -> ActionProposal: ...

    def deny_execution(self, proposal: ActionProposal, *, operation: str) -> None: ...


class MockActionAdapter:
    """Records local proposals; it has no execution capability."""

    def __init__(self) -> None:
        self._proposals: dict[UUID, ActionProposal] = {}

    def record(self, proposal: ActionProposal) -> ActionProposal:
        self._proposals[proposal.proposal_id] = proposal
        return proposal

    def deny_execution(self, proposal: ActionProposal, *, operation: str) -> None:
        raise ForgeOpsError(
            ErrorCode.ACTION_EXECUTION_DENIED,
            f"external execution is outside ForgeOps scope: {operation}",
            http_status=403,
        )


class DenyAllActionAdapter:
    def __init__(self, audit: AuditRepository) -> None:
        self._audit = audit

    def record(self, proposal: ActionProposal) -> ActionProposal:
        return proposal

    def deny_execution(self, proposal: ActionProposal, *, operation: str) -> None:
        self._audit.append(
            AuditEvent(
                event_type="action.execution.denied.v1",
                actor_ref="platform-action-boundary",
                resource_ref=str(proposal.proposal_id),
                result="DENIED",
                reason_code=ErrorCode.ACTION_EXECUTION_DENIED.value,
                trace_id="no-trace-local",
                requirement_ids=("REQ-ACT-001",),
                test_ids=("TEST-ACT-001",),
                details={"operation": operation},
            )
        )
        raise ForgeOpsError(
            ErrorCode.ACTION_EXECUTION_DENIED,
            f"DenyAllActionAdapter rejected operation: {operation}",
            http_status=403,
        )


def forbidden_action_terms() -> frozenset[str]:
    return frozenset(
        {
            "update_mes",
            "write_plc",
            "dispatch_to_erp",
            "apply_to_wms",
            "control_dcs",
            "rpa_execute",
        }
    )


def validate_proposal_payload(payload: dict[str, Any]) -> None:
    terms = {str(key).lower() for key in payload}
    forbidden = terms & forbidden_action_terms()
    if forbidden:
        raise ForgeOpsError(
            ErrorCode.ACTION_EXECUTION_DENIED,
            "proposal contains forbidden execution semantics",
            details={"fields": sorted(forbidden)},
            http_status=403,
        )
