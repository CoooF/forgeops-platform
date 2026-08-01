from __future__ import annotations

import pytest

from forgeops.platform_core.domain_registry.entities import (
    DomainInstallationState,
    RegistryState,
    installation_transition_allowed,
    registry_transition_allowed,
)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (RegistryState.REGISTERED_VALIDATED, RegistryState.QUARANTINED),
        (RegistryState.REGISTERED_VALIDATED, RegistryState.WITHDRAWN),
        (RegistryState.QUARANTINED, RegistryState.WITHDRAWN),
    ],
)
def test_registry_state_machine_allows_only_forward_governance(
    current: RegistryState, target: RegistryState
) -> None:
    assert registry_transition_allowed(current, target)
    assert not registry_transition_allowed(target, current)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (DomainInstallationState.INSTALLED_DISABLED, DomainInstallationState.DISABLED),
        (DomainInstallationState.INSTALLED_DISABLED, DomainInstallationState.REVOKED),
        (DomainInstallationState.DISABLED, DomainInstallationState.REVOKED),
        (DomainInstallationState.DISABLED, DomainInstallationState.LOGICALLY_UNINSTALLED),
        (DomainInstallationState.REVOKED, DomainInstallationState.LOGICALLY_UNINSTALLED),
    ],
)
def test_installation_state_machine_allows_documented_forward_transitions(
    current: DomainInstallationState, target: DomainInstallationState
) -> None:
    assert installation_transition_allowed(current, target)


@pytest.mark.parametrize("state", list(RegistryState))
def test_registry_state_machine_treats_same_state_as_service_level_idempotency(
    state: RegistryState,
) -> None:
    assert not registry_transition_allowed(state, state)


@pytest.mark.parametrize("state", list(DomainInstallationState))
def test_installation_state_machine_has_no_transition_out_of_logical_uninstall(
    state: DomainInstallationState,
) -> None:
    assert not installation_transition_allowed(DomainInstallationState.LOGICALLY_UNINSTALLED, state)
