from __future__ import annotations

import pytest
from pydantic import ValidationError

from forgeops.platform_contracts.domain import Proposal, Scenario


def test_common_entities_reject_unknown_domain_fields() -> None:
    with pytest.raises(ValidationError):
        Scenario(key="generic-scenario", owner_ref="local-owner", machine_id="forbidden")


def test_proposal_can_only_be_not_executed() -> None:
    with pytest.raises(ValidationError):
        Proposal(
            candidate_ref="candidate://1",
            schema_ref="schema://1",
            payload_ref="payload://1",
            execution_status="EXECUTED",
        )
