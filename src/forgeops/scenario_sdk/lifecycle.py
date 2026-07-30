from __future__ import annotations

from forgeops.platform_contracts.domain import PackageLifecycleState
from forgeops.platform_contracts.errors import ErrorCode, ForgeOpsError

ALLOWED_TRANSITIONS: dict[PackageLifecycleState, frozenset[PackageLifecycleState]] = {
    PackageLifecycleState.DISCOVERED: frozenset(
        {PackageLifecycleState.VALIDATED, PackageLifecycleState.INCOMPATIBLE}
    ),
    PackageLifecycleState.VALIDATED: frozenset(
        {PackageLifecycleState.INSTALLED_DISABLED, PackageLifecycleState.INCOMPATIBLE}
    ),
    PackageLifecycleState.INSTALLED_DISABLED: frozenset(
        {PackageLifecycleState.TESTED, PackageLifecycleState.REVOKED}
    ),
    PackageLifecycleState.TESTED: frozenset(
        {PackageLifecycleState.APPROVED, PackageLifecycleState.REVOKED}
    ),
    PackageLifecycleState.APPROVED: frozenset(
        {PackageLifecycleState.RELEASED_TO_ENV, PackageLifecycleState.REVOKED}
    ),
    PackageLifecycleState.RELEASED_TO_ENV: frozenset(
        {
            PackageLifecycleState.ENABLED,
            PackageLifecycleState.DISABLED,
            PackageLifecycleState.REVOKED,
        }
    ),
    PackageLifecycleState.ENABLED: frozenset(
        {PackageLifecycleState.DISABLED, PackageLifecycleState.REVOKED}
    ),
    PackageLifecycleState.DISABLED: frozenset(
        {PackageLifecycleState.RELEASED_TO_ENV, PackageLifecycleState.REVOKED}
    ),
    PackageLifecycleState.REVOKED: frozenset(),
    PackageLifecycleState.INCOMPATIBLE: frozenset(),
}


def require_transition(current: PackageLifecycleState, target: PackageLifecycleState) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise ForgeOpsError(
            ErrorCode.ILLEGAL_STATE_TRANSITION,
            f"transition {current.value} -> {target.value} is not allowed",
            details={"current": current.value, "target": target.value},
            http_status=409,
        )
