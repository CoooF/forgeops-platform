from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from forgeops.platform_core.identity_access.entities import (
    Membership,
    MembershipState,
    Organization,
    Principal,
    PrincipalState,
    Role,
    ScopeType,
)
from forgeops.platform_core.identity_access.policy import (
    ROLE_PERMISSIONS,
    ROLE_SCOPE_TYPES,
    AuthorizationService,
    Permission,
)


def principal(state: PrincipalState = PrincipalState.ACTIVE) -> Principal:
    return Principal(
        subject_ref="matrix-actor",
        display_name="Matrix Actor",
        state=state,
        created_by="test",
        updated_by="test",
    )


@pytest.mark.parametrize("role", list(Role))
@pytest.mark.parametrize("permission", list(Permission))
def test_role_permission_matrix_is_deny_by_default(role: Role, permission: Permission) -> None:
    policy = AuthorizationService()
    actor = principal()
    scope_type = next(iter(ROLE_SCOPE_TYPES[role]))
    scope_id = None if scope_type == ScopeType.PLATFORM else uuid4()
    membership = Membership(
        principal_id=actor.principal_id,
        scope_type=scope_type,
        scope_id=scope_id,
        role=role,
        granted_by="test",
    )
    decision = policy.decide(
        actor,
        (membership,),
        permission,
        resource_ref="resource://matrix",
        scope_type=scope_type,
        scope_id=scope_id,
    )
    assert decision.allowed is (permission in ROLE_PERMISSIONS[role])


@pytest.mark.parametrize("role", list(Role))
def test_role_never_crosses_to_an_unrelated_scope(role: Role) -> None:
    policy = AuthorizationService()
    actor = principal()
    scope_type = next(
        (item for item in ROLE_SCOPE_TYPES[role] if item != ScopeType.PLATFORM),
        ScopeType.PLATFORM,
    )
    direct_scope = None if scope_type == ScopeType.PLATFORM else uuid4()
    wrong_scope = None if scope_type == ScopeType.PLATFORM else uuid4()
    membership = Membership(
        principal_id=actor.principal_id,
        scope_type=scope_type,
        scope_id=direct_scope,
        role=role,
        granted_by="test",
    )
    permission = next(iter(ROLE_PERMISSIONS[role]))
    decision = policy.decide(
        actor,
        (membership,),
        permission,
        resource_ref="resource://wrong-scope",
        scope_type=scope_type,
        scope_id=wrong_scope,
    )
    assert decision.allowed is (scope_type == ScopeType.PLATFORM)


def test_disabled_principal_and_suspended_membership_are_denied() -> None:
    policy = AuthorizationService()
    scope_id = uuid4()
    active = principal()
    membership = Membership(
        principal_id=active.principal_id,
        scope_type=ScopeType.PROJECT,
        scope_id=scope_id,
        role=Role.PROJECT_OWNER,
        state=MembershipState.SUSPENDED,
        granted_by="test",
    )
    suspended = policy.decide(
        active,
        (membership,),
        Permission.PROJECT_VIEW,
        resource_ref="project://test",
        scope_type=ScopeType.PROJECT,
        scope_id=scope_id,
    )
    assert not suspended.allowed
    disabled = policy.decide(
        principal(PrincipalState.DISABLED),
        (),
        Permission.PROJECT_VIEW,
        resource_ref="project://test",
        scope_type=ScopeType.PROJECT,
        scope_id=scope_id,
    )
    assert not disabled.allowed
    assert disabled.reason == "PRINCIPAL_DISABLED"


def test_slug_and_scope_models_are_strict() -> None:
    with pytest.raises(ValidationError):
        Organization(
            name="Bad slug",
            slug="Bad Slug",
            created_by="test",
            updated_by="test",
        )
    with pytest.raises(ValidationError):
        Membership(
            principal_id=uuid4(),
            scope_type=ScopeType.PROJECT,
            scope_id=uuid4(),
            role=Role.PROJECT_VIEWER,
            granted_by="test",
            clientRole="ORG_OWNER",
        )
