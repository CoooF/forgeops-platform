from __future__ import annotations

from itertools import pairwise

import pytest

from forgeops.platform_contracts.domain import PackageLifecycleState
from forgeops.platform_contracts.errors import ErrorCode, ForgeOpsError
from forgeops.scenario_sdk.lifecycle import require_transition


def test_happy_path_transitions_are_explicit() -> None:
    path = (
        PackageLifecycleState.DISCOVERED,
        PackageLifecycleState.VALIDATED,
        PackageLifecycleState.INSTALLED_DISABLED,
        PackageLifecycleState.TESTED,
        PackageLifecycleState.APPROVED,
        PackageLifecycleState.RELEASED_TO_ENV,
        PackageLifecycleState.ENABLED,
    )
    for current, target in pairwise(path):
        require_transition(current, target)


def test_illegal_transition_has_stable_reason() -> None:
    with pytest.raises(ForgeOpsError) as captured:
        require_transition(PackageLifecycleState.INSTALLED_DISABLED, PackageLifecycleState.ENABLED)
    assert captured.value.code == ErrorCode.ILLEGAL_STATE_TRANSITION
    assert captured.value.details == {
        "current": "INSTALLED_DISABLED",
        "target": "ENABLED",
    }


@pytest.mark.parametrize(
    "terminal",
    [PackageLifecycleState.REVOKED, PackageLifecycleState.INCOMPATIBLE],
)
def test_terminal_states_cannot_transition(terminal: PackageLifecycleState) -> None:
    with pytest.raises(ForgeOpsError):
        require_transition(terminal, PackageLifecycleState.DISCOVERED)
