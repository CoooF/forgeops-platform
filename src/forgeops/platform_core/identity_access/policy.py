from __future__ import annotations

from enum import StrEnum
from typing import Protocol
from uuid import UUID

from forgeops.platform_core.identity_access.entities import (
    AuthorizationDecision,
    Membership,
    MembershipState,
    Principal,
    PrincipalState,
    Role,
    ScopeType,
)


class Permission(StrEnum):
    ORGANIZATION_CREATE = "organization.create"
    ORGANIZATION_VIEW = "organization.view"
    ORGANIZATION_UPDATE = "organization.update"
    ORGANIZATION_ARCHIVE = "organization.archive"
    WORKSPACE_CREATE = "workspace.create"
    WORKSPACE_VIEW = "workspace.view"
    WORKSPACE_UPDATE = "workspace.update"
    WORKSPACE_ARCHIVE = "workspace.archive"
    PROJECT_CREATE = "project.create"
    PROJECT_VIEW = "project.view"
    PROJECT_UPDATE = "project.update"
    PROJECT_ACTIVATE = "project.activate"
    PROJECT_ARCHIVE = "project.archive"
    MEMBERSHIP_MANAGE = "membership.manage"
    PACKAGE_BIND = "package.bind"
    PACKAGE_REGISTRY_VIEW = "package.registry.view"
    PACKAGE_REGISTRY_MANAGE = "package.registry.manage"
    AUDIT_READ = "audit.read"
    FDS_REGISTRY_VIEW = "fds.registry.view"
    FDS_REGISTRY_MANAGE = "fds.registry.manage"
    FDS_INSTALLATION_VIEW = "fds.installation.view"
    FDS_INSTALLATION_MANAGE = "fds.installation.manage"
    FDS_DOMAIN_LOCK_VIEW = "fds.domain-lock.view"
    FDS_DOMAIN_LOCK_HISTORY_VIEW = "fds.domain-lock.history.view"
    FDS_DOMAIN_LOCK_MANAGE = "fds.domain-lock.manage"
    FDS_IMPACT_VIEW = "fds.impact.view"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ORG_OWNER: frozenset(Permission),
    Role.ORG_ADMIN: frozenset(
        permission
        for permission in Permission
        if permission not in {Permission.ORGANIZATION_ARCHIVE, Permission.ORGANIZATION_CREATE}
    ),
    Role.WORKSPACE_ADMIN: frozenset(
        {
            Permission.WORKSPACE_VIEW,
            Permission.WORKSPACE_UPDATE,
            Permission.WORKSPACE_ARCHIVE,
            Permission.PROJECT_CREATE,
            Permission.PROJECT_VIEW,
            Permission.PROJECT_UPDATE,
            Permission.PROJECT_ACTIVATE,
            Permission.PROJECT_ARCHIVE,
            Permission.MEMBERSHIP_MANAGE,
            Permission.PACKAGE_BIND,
            Permission.AUDIT_READ,
            Permission.FDS_REGISTRY_VIEW,
            Permission.FDS_INSTALLATION_VIEW,
            Permission.FDS_DOMAIN_LOCK_VIEW,
            Permission.FDS_DOMAIN_LOCK_HISTORY_VIEW,
            Permission.FDS_DOMAIN_LOCK_MANAGE,
            Permission.FDS_IMPACT_VIEW,
        }
    ),
    Role.PROJECT_OWNER: frozenset(
        {
            Permission.PROJECT_VIEW,
            Permission.PROJECT_UPDATE,
            Permission.PROJECT_ACTIVATE,
            Permission.PROJECT_ARCHIVE,
            Permission.MEMBERSHIP_MANAGE,
            Permission.PACKAGE_BIND,
            Permission.AUDIT_READ,
            Permission.FDS_REGISTRY_VIEW,
            Permission.FDS_INSTALLATION_VIEW,
            Permission.FDS_DOMAIN_LOCK_VIEW,
            Permission.FDS_DOMAIN_LOCK_HISTORY_VIEW,
            Permission.FDS_DOMAIN_LOCK_MANAGE,
            Permission.FDS_IMPACT_VIEW,
        }
    ),
    Role.PROJECT_EDITOR: frozenset(
        {
            Permission.PROJECT_VIEW,
            Permission.PROJECT_UPDATE,
            Permission.PROJECT_ACTIVATE,
            Permission.FDS_DOMAIN_LOCK_VIEW,
        }
    ),
    Role.PROJECT_VIEWER: frozenset({Permission.PROJECT_VIEW, Permission.FDS_DOMAIN_LOCK_VIEW}),
    Role.PACKAGE_OPERATOR: frozenset(
        {
            Permission.PROJECT_VIEW,
            Permission.PACKAGE_BIND,
            Permission.PACKAGE_REGISTRY_VIEW,
            Permission.PACKAGE_REGISTRY_MANAGE,
            Permission.FDS_REGISTRY_VIEW,
            Permission.FDS_REGISTRY_MANAGE,
            Permission.FDS_IMPACT_VIEW,
        }
    ),
    Role.AUDITOR: frozenset(
        {
            Permission.ORGANIZATION_VIEW,
            Permission.WORKSPACE_VIEW,
            Permission.PROJECT_VIEW,
            Permission.AUDIT_READ,
            Permission.PACKAGE_REGISTRY_VIEW,
            Permission.FDS_REGISTRY_VIEW,
            Permission.FDS_INSTALLATION_VIEW,
            Permission.FDS_DOMAIN_LOCK_VIEW,
            Permission.FDS_DOMAIN_LOCK_HISTORY_VIEW,
            Permission.FDS_IMPACT_VIEW,
        }
    ),
}

ROLE_SCOPE_TYPES: dict[Role, frozenset[ScopeType]] = {
    Role.ORG_OWNER: frozenset({ScopeType.PLATFORM, ScopeType.ORGANIZATION}),
    Role.ORG_ADMIN: frozenset({ScopeType.ORGANIZATION}),
    Role.WORKSPACE_ADMIN: frozenset({ScopeType.WORKSPACE}),
    Role.PROJECT_OWNER: frozenset({ScopeType.PROJECT}),
    Role.PROJECT_EDITOR: frozenset({ScopeType.PROJECT}),
    Role.PROJECT_VIEWER: frozenset({ScopeType.PROJECT}),
    Role.PACKAGE_OPERATOR: frozenset(
        {ScopeType.PLATFORM, ScopeType.ORGANIZATION, ScopeType.PROJECT}
    ),
    Role.AUDITOR: frozenset(
        {ScopeType.PLATFORM, ScopeType.ORGANIZATION, ScopeType.WORKSPACE, ScopeType.PROJECT}
    ),
}


class AuthorizationPort(Protocol):
    policy_version: str

    def decide(
        self,
        principal: Principal,
        memberships: tuple[Membership, ...],
        permission: Permission,
        *,
        resource_ref: str,
        scope_type: ScopeType,
        scope_id: UUID | None,
        ancestor_scope_ids: frozenset[UUID] = frozenset(),
    ) -> AuthorizationDecision: ...


class AuthorizationService:
    policy_version = "identity-access-v1"

    @staticmethod
    def role_allowed_on_scope(role: Role, scope_type: ScopeType) -> bool:
        return scope_type in ROLE_SCOPE_TYPES[role]

    def decide(
        self,
        principal: Principal,
        memberships: tuple[Membership, ...],
        permission: Permission,
        *,
        resource_ref: str,
        scope_type: ScopeType,
        scope_id: UUID | None,
        ancestor_scope_ids: frozenset[UUID] = frozenset(),
    ) -> AuthorizationDecision:
        if principal.state != PrincipalState.ACTIVE:
            return self._decision(
                principal,
                permission,
                resource_ref,
                scope_type,
                scope_id,
                False,
                "PRINCIPAL_DISABLED",
            )
        for membership in memberships:
            if membership.state != MembershipState.ACTIVE:
                continue
            if permission not in ROLE_PERMISSIONS[membership.role]:
                continue
            if membership.scope_type == ScopeType.PLATFORM:
                return self._decision(
                    principal,
                    permission,
                    resource_ref,
                    scope_type,
                    scope_id,
                    True,
                    "PLATFORM_GRANT",
                )
            if membership.scope_id == scope_id and membership.scope_type == scope_type:
                return self._decision(
                    principal, permission, resource_ref, scope_type, scope_id, True, "DIRECT_GRANT"
                )
            if membership.scope_id in ancestor_scope_ids:
                return self._decision(
                    principal,
                    permission,
                    resource_ref,
                    scope_type,
                    scope_id,
                    True,
                    "EXPLICIT_ANCESTOR_GRANT",
                )
        return self._decision(
            principal, permission, resource_ref, scope_type, scope_id, False, "NO_APPLICABLE_GRANT"
        )

    def _decision(
        self,
        principal: Principal,
        permission: Permission,
        resource_ref: str,
        scope_type: ScopeType,
        scope_id: UUID | None,
        allowed: bool,
        reason: str,
    ) -> AuthorizationDecision:
        return AuthorizationDecision(
            principal_id=principal.principal_id,
            subject_ref=principal.subject_ref,
            action=permission.value,
            resource_ref=resource_ref,
            scope_type=scope_type,
            scope_id=scope_id,
            allowed=allowed,
            reason=reason,
            policy_version=self.policy_version,
        )
