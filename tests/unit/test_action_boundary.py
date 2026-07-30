from __future__ import annotations

import pytest

from forgeops.platform_contracts.errors import ErrorCode, ForgeOpsError
from forgeops.platform_core.action_boundary import (
    ActionProposal,
    DenyAllActionAdapter,
    MockActionAdapter,
    validate_proposal_payload,
)
from forgeops.platform_core.audit import InMemoryAuditRepository


def test_mock_records_but_cannot_execute() -> None:
    adapter = MockActionAdapter()
    proposal = ActionProposal(schemaRef="schema://proposal", payloadRef="blob://one")
    assert adapter.record(proposal).execution_status == "NOT_EXECUTED"
    with pytest.raises(ForgeOpsError) as captured:
        adapter.deny_execution(proposal, operation="send")
    assert captured.value.code == ErrorCode.ACTION_EXECUTION_DENIED


def test_deny_all_always_audits_and_rejects() -> None:
    audit = InMemoryAuditRepository()
    adapter = DenyAllActionAdapter(audit)
    proposal = ActionProposal(schemaRef="schema://proposal", payloadRef="blob://one")
    with pytest.raises(ForgeOpsError) as captured:
        adapter.deny_execution(proposal, operation="unknown-operation")
    assert captured.value.code == ErrorCode.ACTION_EXECUTION_DENIED
    assert audit.list_events()[0].event_type == "action.execution.denied.v1"


def test_execution_semantics_are_forbidden_in_payload() -> None:
    with pytest.raises(ForgeOpsError):
        validate_proposal_payload({"update_mes": True})
