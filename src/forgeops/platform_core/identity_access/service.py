from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from pydantic import Field

from forgeops.platform_contracts.domain import Environment, PackageLifecycleState, StrictModel
from forgeops.platform_contracts.errors import ErrorCode, ForgeOpsError
from forgeops.platform_core.audit import AuditEvent, AuditRepository
from forgeops.platform_core.identity_access.auth import AuthPort
from forgeops.platform_core.identity_access.entities import (
    AuthenticatedPrincipal,
    BindingState,
    Membership,
    MembershipState,
    Organization,
    OrganizationState,
    PackageKind,
    Principal,
    PrincipalState,
    Project,
    ProjectPackageBinding,
    ProjectState,
    Role,
    ScopeType,
    Workspace,
    WorkspaceState,
)
from forgeops.platform_core.identity_access.policy import AuthorizationService, Permission
from forgeops.platform_core.identity_access.repository import IdentityRepository
from forgeops.platform_core.scenario_registry.repository import InstallationRepository
from forgeops.platform_core.scenario_registry.service import ScenarioPackageService


class ActorContext(StrictModel):
    authenticated: AuthenticatedPrincipal
    principal: Principal
    memberships: tuple[Membership, ...] = Field(default=())


class IdentityAccessService:
    def __init__(
        self,
        repository: IdentityRepository,
        installations: InstallationRepository,
        packages: ScenarioPackageService,
        audit: AuditRepository,
        auth: AuthPort,
        environment: Environment,
        decision_observer: Callable[[str, str], None] | None = None,
    ) -> None:
        self._repository = repository
        self._installations = installations
        self._packages = packages
        self._audit = audit
        self._auth = auth
        self._environment = environment
        self._authorization = AuthorizationService()
        self._resolved_subjects: set[str] = set()
        self._decision_observer = decision_observer or (lambda _action, _result: None)

    def authenticate(self, credential: str | None, trace_id: str) -> ActorContext:
        authenticated = self._auth.authenticate(credential)
        if authenticated is None:
            self._decision_observer("principal.resolve", "denied")
            self._audit_event(
                "identity.principal.denied.v1",
                "anonymous",
                "principal://unknown",
                "DENIED",
                ErrorCode.UNAUTHORIZED.value,
                trace_id,
                scope_ref="platform://local",
            )
            raise ForgeOpsError(
                ErrorCode.UNAUTHORIZED,
                "local synthetic authentication is required",
                http_status=401,
            )
        principal = self._repository.get_principal_by_subject(authenticated.subject_ref)
        if principal is None:
            self._decision_observer("principal.resolve", "denied")
            self._audit_event(
                "identity.principal.denied.v1",
                authenticated.subject_ref,
                "principal://unknown",
                "DENIED",
                ErrorCode.UNAUTHORIZED.value,
                trace_id,
                scope_ref="platform://local",
            )
            raise ForgeOpsError(
                ErrorCode.UNAUTHORIZED,
                "principal is not provisioned",
                http_status=401,
            )
        if principal.state != PrincipalState.ACTIVE:
            self._decision_observer("principal.resolve", "denied")
            self._audit_event(
                "identity.principal.denied.v1",
                principal.subject_ref,
                f"principal://{principal.principal_id}",
                "DENIED",
                ErrorCode.PRINCIPAL_DISABLED.value,
                trace_id,
                scope_ref="platform://local",
            )
            raise ForgeOpsError(
                ErrorCode.PRINCIPAL_DISABLED,
                "principal is disabled",
                http_status=401,
            )
        if principal.subject_ref not in self._resolved_subjects:
            self._audit_event(
                "identity.principal.resolved.v1",
                principal.subject_ref,
                f"principal://{principal.principal_id}",
                "SUCCESS",
                "LOCAL_SYNTHETIC_RESOLVED",
                trace_id,
                scope_ref="platform://local",
            )
            self._resolved_subjects.add(principal.subject_ref)
        self._decision_observer("principal.resolve", "allowed")
        return ActorContext(
            authenticated=authenticated,
            principal=principal,
            memberships=self._repository.list_memberships_for_principal(principal.principal_id),
        )

    def me(self, actor: ActorContext) -> dict[str, object]:
        return {
            "principal": actor.principal.model_dump(mode="json", by_alias=True),
            "authenticationMode": actor.authenticated.authentication_mode,
            "enterpriseIdentityConnected": False,
            "memberships": [
                membership.model_dump(mode="json", by_alias=True)
                for membership in actor.memberships
            ],
        }

    def authorize_platform(
        self, actor: ActorContext, permission: Permission, trace_id: str
    ) -> None:
        self._authorize(
            actor,
            permission,
            resource_ref="platform://local",
            scope_type=ScopeType.PLATFORM,
            scope_id=None,
            ancestor_scope_ids=frozenset(),
            trace_id=trace_id,
            conceal=False,
        )

    def list_organizations(self, actor: ActorContext) -> tuple[Organization, ...]:
        return tuple(
            organization
            for organization in self._repository.list_organizations()
            if self._can_discover_organization(actor, organization.organization_id)
        )

    def create_organization(
        self,
        actor: ActorContext,
        *,
        name: str,
        slug: str,
        idempotency_key: str,
        trace_id: str,
    ) -> Organization:
        self.authorize_platform(actor, Permission.ORGANIZATION_CREATE, trace_id)
        now = datetime.now(UTC)
        organization = Organization(
            name=name,
            slug=slug,
            created_at=now,
            updated_at=now,
            created_by=actor.principal.subject_ref,
            updated_by=actor.principal.subject_ref,
        )
        owner = Membership(
            principal_id=actor.principal.principal_id,
            scope_type=ScopeType.ORGANIZATION,
            scope_id=organization.organization_id,
            role=Role.ORG_OWNER,
            granted_by=actor.principal.subject_ref,
            granted_at=now,
            updated_at=now,
        )
        saved = self._repository.add_organization_with_owner(organization, owner, idempotency_key)
        self._audit_success(
            "organization.created.v1", actor, saved, trace_id, "ORGANIZATION_CREATED"
        )
        return saved

    def get_organization(
        self, actor: ActorContext, organization_id: UUID, trace_id: str
    ) -> Organization:
        organization = self._require_organization(organization_id, actor, trace_id)
        if not self._can_discover_organization(actor, organization_id):
            self._deny_hidden(actor, f"organization://{organization_id}", trace_id)
        return organization

    def update_organization(
        self,
        actor: ActorContext,
        organization_id: UUID,
        *,
        name: str | None,
        slug: str | None,
        expected_version: int,
        trace_id: str,
    ) -> Organization:
        organization = self._require_organization(organization_id, actor, trace_id)
        self._authorize_organization(actor, organization, Permission.ORGANIZATION_UPDATE, trace_id)
        self._require_state(
            organization.state == OrganizationState.ACTIVE,
            actor,
            organization,
            trace_id,
            "ORGANIZATION_NOT_ACTIVE",
        )
        updated = organization.model_copy(
            update={
                "name": name if name is not None else organization.name,
                "slug": slug if slug is not None else organization.slug,
                "updated_at": datetime.now(UTC),
                "updated_by": actor.principal.subject_ref,
            }
        )
        saved = self._repository.save_organization(updated, expected_version)
        self._audit_success(
            "organization.updated.v1", actor, saved, trace_id, "ORGANIZATION_UPDATED"
        )
        return saved

    def archive_organization(
        self,
        actor: ActorContext,
        organization_id: UUID,
        expected_version: int,
        trace_id: str,
    ) -> Organization:
        organization = self._require_organization(organization_id, actor, trace_id)
        self._authorize_organization(actor, organization, Permission.ORGANIZATION_ARCHIVE, trace_id)
        if organization.state == OrganizationState.ARCHIVED:
            return organization
        updated = organization.model_copy(
            update={
                "state": OrganizationState.ARCHIVED,
                "updated_at": datetime.now(UTC),
                "updated_by": actor.principal.subject_ref,
            }
        )
        saved = self._repository.save_organization(updated, expected_version)
        self._audit_success(
            "organization.archived.v1", actor, saved, trace_id, "ORGANIZATION_ARCHIVED"
        )
        return saved

    def list_workspaces(
        self, actor: ActorContext, organization_id: UUID, trace_id: str
    ) -> tuple[Workspace, ...]:
        self.get_organization(actor, organization_id, trace_id)
        return tuple(
            workspace
            for workspace in self._repository.list_workspaces(organization_id)
            if self._can_discover_workspace(actor, workspace)
        )

    def create_workspace(
        self,
        actor: ActorContext,
        organization_id: UUID,
        *,
        name: str,
        slug: str,
        idempotency_key: str,
        trace_id: str,
    ) -> Workspace:
        organization = self._require_organization(organization_id, actor, trace_id)
        self._authorize_organization(actor, organization, Permission.WORKSPACE_CREATE, trace_id)
        self._require_state(
            organization.state == OrganizationState.ACTIVE,
            actor,
            organization,
            trace_id,
            "ORGANIZATION_NOT_ACTIVE",
        )
        now = datetime.now(UTC)
        workspace = Workspace(
            organization_id=organization_id,
            name=name,
            slug=slug,
            created_at=now,
            updated_at=now,
            created_by=actor.principal.subject_ref,
            updated_by=actor.principal.subject_ref,
        )
        saved = self._repository.add_workspace(workspace, idempotency_key)
        self._audit_success("workspace.created.v1", actor, saved, trace_id, "WORKSPACE_CREATED")
        return saved

    def get_workspace(self, actor: ActorContext, workspace_id: UUID, trace_id: str) -> Workspace:
        workspace = self._require_workspace(workspace_id, actor, trace_id)
        if not self._can_discover_workspace(actor, workspace):
            self._deny_hidden(actor, f"workspace://{workspace_id}", trace_id)
        return workspace

    def update_workspace(
        self,
        actor: ActorContext,
        workspace_id: UUID,
        *,
        name: str | None,
        slug: str | None,
        expected_version: int,
        trace_id: str,
    ) -> Workspace:
        workspace, organization = self._workspace_context(workspace_id, actor, trace_id)
        self._authorize_workspace(actor, workspace, Permission.WORKSPACE_UPDATE, trace_id)
        self._require_state(
            organization.state == OrganizationState.ACTIVE
            and workspace.state == WorkspaceState.ACTIVE,
            actor,
            workspace,
            trace_id,
            "WORKSPACE_NOT_WRITABLE",
        )
        updated = workspace.model_copy(
            update={
                "name": name if name is not None else workspace.name,
                "slug": slug if slug is not None else workspace.slug,
                "updated_at": datetime.now(UTC),
                "updated_by": actor.principal.subject_ref,
            }
        )
        saved = self._repository.save_workspace(updated, expected_version)
        self._audit_success("workspace.updated.v1", actor, saved, trace_id, "WORKSPACE_UPDATED")
        return saved

    def archive_workspace(
        self,
        actor: ActorContext,
        workspace_id: UUID,
        expected_version: int,
        trace_id: str,
    ) -> Workspace:
        workspace, organization = self._workspace_context(workspace_id, actor, trace_id)
        self._authorize_workspace(actor, workspace, Permission.WORKSPACE_ARCHIVE, trace_id)
        self._require_state(
            organization.state == OrganizationState.ACTIVE,
            actor,
            workspace,
            trace_id,
            "ORGANIZATION_NOT_ACTIVE",
        )
        if workspace.state == WorkspaceState.ARCHIVED:
            return workspace
        updated = workspace.model_copy(
            update={
                "state": WorkspaceState.ARCHIVED,
                "updated_at": datetime.now(UTC),
                "updated_by": actor.principal.subject_ref,
            }
        )
        saved = self._repository.save_workspace(updated, expected_version)
        self._audit_success("workspace.archived.v1", actor, saved, trace_id, "WORKSPACE_ARCHIVED")
        return saved

    def list_projects(
        self, actor: ActorContext, workspace_id: UUID, trace_id: str
    ) -> tuple[Project, ...]:
        workspace = self.get_workspace(actor, workspace_id, trace_id)
        return tuple(
            project
            for project in self._repository.list_projects(workspace.workspace_id)
            if self._is_allowed_project(actor, project, Permission.PROJECT_VIEW)
        )

    def create_project(
        self,
        actor: ActorContext,
        workspace_id: UUID,
        *,
        name: str,
        slug: str,
        description: str,
        idempotency_key: str,
        trace_id: str,
    ) -> Project:
        workspace, organization = self._workspace_context(workspace_id, actor, trace_id)
        self._authorize_workspace(actor, workspace, Permission.PROJECT_CREATE, trace_id)
        self._require_state(
            organization.state == OrganizationState.ACTIVE
            and workspace.state == WorkspaceState.ACTIVE,
            actor,
            workspace,
            trace_id,
            "WORKSPACE_NOT_WRITABLE",
        )
        now = datetime.now(UTC)
        project = Project(
            workspace_id=workspace_id,
            name=name,
            slug=slug,
            description=description,
            created_at=now,
            updated_at=now,
            created_by=actor.principal.subject_ref,
            updated_by=actor.principal.subject_ref,
        )
        saved = self._repository.add_project(project, idempotency_key)
        self._audit_success("project.created.v1", actor, saved, trace_id, "PROJECT_CREATED")
        return saved

    def get_project(self, actor: ActorContext, project_id: UUID, trace_id: str) -> Project:
        project = self._require_project(project_id, actor, trace_id)
        self._authorize_project(actor, project, Permission.PROJECT_VIEW, trace_id)
        return project

    def update_project(
        self,
        actor: ActorContext,
        project_id: UUID,
        *,
        name: str | None,
        slug: str | None,
        description: str | None,
        expected_version: int,
        trace_id: str,
    ) -> Project:
        project, workspace, organization = self._project_context(project_id, actor, trace_id)
        self._authorize_project(actor, project, Permission.PROJECT_UPDATE, trace_id)
        self._require_project_writable(actor, project, workspace, organization, trace_id)
        updated = project.model_copy(
            update={
                "name": name if name is not None else project.name,
                "slug": slug if slug is not None else project.slug,
                "description": description if description is not None else project.description,
                "updated_at": datetime.now(UTC),
                "updated_by": actor.principal.subject_ref,
            }
        )
        saved = self._repository.save_project(updated, expected_version)
        self._audit_success("project.updated.v1", actor, saved, trace_id, "PROJECT_UPDATED")
        return saved

    def activate_project(
        self, actor: ActorContext, project_id: UUID, expected_version: int, trace_id: str
    ) -> Project:
        project, workspace, organization = self._project_context(project_id, actor, trace_id)
        self._authorize_project(actor, project, Permission.PROJECT_ACTIVATE, trace_id)
        self._require_project_writable(actor, project, workspace, organization, trace_id)
        self._require_state(
            project.state == ProjectState.DRAFT,
            actor,
            project,
            trace_id,
            "PROJECT_ACTIVATION_REQUIRES_DRAFT",
        )
        saved = self._repository.save_project(
            project.model_copy(
                update={
                    "state": ProjectState.ACTIVE,
                    "updated_at": datetime.now(UTC),
                    "updated_by": actor.principal.subject_ref,
                }
            ),
            expected_version,
        )
        self._audit_success("project.activated.v1", actor, saved, trace_id, "PROJECT_ACTIVATED")
        return saved

    def archive_project(
        self, actor: ActorContext, project_id: UUID, expected_version: int, trace_id: str
    ) -> Project:
        project, workspace, organization = self._project_context(project_id, actor, trace_id)
        self._authorize_project(actor, project, Permission.PROJECT_ARCHIVE, trace_id)
        self._require_state(
            organization.state == OrganizationState.ACTIVE
            and workspace.state == WorkspaceState.ACTIVE,
            actor,
            project,
            trace_id,
            "PROJECT_PARENT_NOT_WRITABLE",
        )
        if project.state == ProjectState.ARCHIVED:
            return project
        saved = self._repository.save_project(
            project.model_copy(
                update={
                    "state": ProjectState.ARCHIVED,
                    "updated_at": datetime.now(UTC),
                    "updated_by": actor.principal.subject_ref,
                }
            ),
            expected_version,
        )
        self._audit_success("project.archived.v1", actor, saved, trace_id, "PROJECT_ARCHIVED")
        return saved

    def list_memberships(
        self, actor: ActorContext, organization_id: UUID, trace_id: str
    ) -> tuple[dict[str, object], ...]:
        organization = self._require_organization(organization_id, actor, trace_id)
        allowed = self._try_authorize_organization(
            actor, organization, Permission.MEMBERSHIP_MANAGE
        )
        if not allowed:
            allowed = self._try_authorize_organization(actor, organization, Permission.AUDIT_READ)
        if not allowed:
            self._deny_hidden(actor, f"organization://{organization_id}", trace_id)
        result: list[dict[str, object]] = []
        for membership in self._repository.list_memberships_for_organization(organization_id):
            principal = self._repository.get_principal(membership.principal_id)
            if principal is None:
                continue
            result.append(
                {
                    **membership.model_dump(mode="json", by_alias=True),
                    "principal": {
                        "subjectRef": principal.subject_ref,
                        "displayName": principal.display_name,
                        "state": principal.state.value,
                    },
                }
            )
        return tuple(result)

    def create_membership(
        self,
        actor: ActorContext,
        organization_id: UUID,
        *,
        principal_ref: str,
        scope_type: ScopeType,
        scope_id: UUID,
        role: Role,
        idempotency_key: str,
        trace_id: str,
    ) -> Membership:
        organization = self._require_organization(organization_id, actor, trace_id)
        self._require_state(
            organization.state == OrganizationState.ACTIVE,
            actor,
            organization,
            trace_id,
            "ORGANIZATION_NOT_ACTIVE",
        )
        if scope_type == ScopeType.PLATFORM:
            raise ForgeOpsError(
                ErrorCode.FORBIDDEN,
                "platform memberships cannot be granted through organization APIs",
                http_status=403,
            )
        scope_org_id = self._repository.organization_id_for_scope(scope_type, scope_id)
        if scope_org_id != organization_id:
            self._deny_hidden(actor, f"{scope_type.value.lower()}://{scope_id}", trace_id)
        self._authorize_scope(actor, scope_type, scope_id, Permission.MEMBERSHIP_MANAGE, trace_id)
        if not self._authorization.role_allowed_on_scope(role, scope_type):
            raise ForgeOpsError(
                ErrorCode.INPUT_INVALID,
                "role is not valid for the requested scope type",
                details={"role": role.value, "scopeType": scope_type.value},
                http_status=422,
            )
        principal = self._repository.get_principal_by_subject(principal_ref)
        if principal is None:
            raise ForgeOpsError(
                ErrorCode.INPUT_INVALID, "target principal is not provisioned", http_status=422
            )
        now = datetime.now(UTC)
        membership = Membership(
            principal_id=principal.principal_id,
            scope_type=scope_type,
            scope_id=scope_id,
            role=role,
            granted_by=actor.principal.subject_ref,
            granted_at=now,
            updated_at=now,
        )
        saved = self._repository.add_membership(membership, idempotency_key)
        self._audit_event(
            "membership.granted.v1",
            actor.principal.subject_ref,
            f"membership://{saved.membership_id}",
            "SUCCESS",
            "ROLE_GRANTED",
            trace_id,
            scope_ref=f"{scope_type.value.lower()}://{scope_id}",
            details={"role": role.value, "targetPrincipalId": str(principal.principal_id)},
        )
        return saved

    def transition_membership(
        self,
        actor: ActorContext,
        membership_id: UUID,
        target: MembershipState,
        expected_version: int,
        trace_id: str,
    ) -> Membership:
        membership = self._repository.get_membership(membership_id)
        if membership is None or membership.scope_id is None:
            self._deny_hidden(actor, f"membership://{membership_id}", trace_id)
        assert membership is not None and membership.scope_id is not None
        self._authorize_scope(
            actor,
            membership.scope_type,
            membership.scope_id,
            Permission.MEMBERSHIP_MANAGE,
            trace_id,
        )
        if membership.state == MembershipState.REVOKED:
            self._require_state(False, actor, membership, trace_id, "MEMBERSHIP_ALREADY_REVOKED")
        if (
            membership.scope_type == ScopeType.ORGANIZATION
            and membership.role == Role.ORG_OWNER
            and membership.state == MembershipState.ACTIVE
            and self._repository.count_active_org_owners(membership.scope_id) <= 1
        ):
            self._audit_event(
                "membership.transition.denied.v1",
                actor.principal.subject_ref,
                f"membership://{membership_id}",
                "DENIED",
                ErrorCode.LAST_OWNER_REQUIRED.value,
                trace_id,
                scope_ref=f"organization://{membership.scope_id}",
            )
            raise ForgeOpsError(
                ErrorCode.LAST_OWNER_REQUIRED,
                "the final active ORG_OWNER cannot be suspended or revoked",
                http_status=409,
            )
        updated = membership.model_copy(update={"state": target, "updated_at": datetime.now(UTC)})
        saved = self._repository.save_membership(updated, expected_version)
        self._audit_event(
            f"membership.{target.value.lower()}.v1",
            actor.principal.subject_ref,
            f"membership://{membership_id}",
            "SUCCESS",
            target.value,
            trace_id,
            scope_ref=f"{membership.scope_type.value.lower()}://{membership.scope_id}",
        )
        return saved

    def list_project_bindings(
        self, actor: ActorContext, project_id: UUID, trace_id: str
    ) -> tuple[dict[str, object], ...]:
        project = self.get_project(actor, project_id, trace_id)
        result: list[dict[str, object]] = []
        for binding in self._repository.list_project_bindings(project.project_id):
            installation = self._installations.get_by_id(binding.installation_id)
            result.append(
                {
                    **binding.model_dump(mode="json", by_alias=True),
                    "packageId": installation.package_id if installation else "unavailable",
                    "packageVersion": installation.package_version
                    if installation
                    else "unavailable",
                    "installationState": installation.state.value
                    if installation
                    else "UNAVAILABLE",
                }
            )
        return tuple(result)

    def project_memberships(
        self, actor: ActorContext, project_id: UUID, trace_id: str
    ) -> tuple[dict[str, object], ...]:
        project, workspace, organization = self._project_context(project_id, actor, trace_id)
        self._authorize_project(actor, project, Permission.PROJECT_VIEW, trace_id)
        relevant_scope_ids = {
            organization.organization_id,
            workspace.workspace_id,
            project.project_id,
        }
        result: list[dict[str, object]] = []
        for membership in self._repository.list_memberships_for_organization(
            organization.organization_id
        ):
            if membership.scope_id not in relevant_scope_ids:
                continue
            principal = self._repository.get_principal(membership.principal_id)
            if principal is None:
                continue
            result.append(
                {
                    **membership.model_dump(mode="json", by_alias=True),
                    "principal": {
                        "subjectRef": principal.subject_ref,
                        "displayName": principal.display_name,
                        "state": principal.state.value,
                    },
                }
            )
        return tuple(result)

    def project_permissions(
        self, actor: ActorContext, project_id: UUID, trace_id: str
    ) -> tuple[str, ...]:
        project = self.get_project(actor, project_id, trace_id)
        return tuple(
            permission.value
            for permission in Permission
            if self._is_allowed_project(actor, project, permission)
        )

    def bindable_installations(
        self, actor: ActorContext, project_id: UUID, trace_id: str
    ) -> tuple[dict[str, object], ...]:
        project = self._require_project(project_id, actor, trace_id)
        self._authorize_project(actor, project, Permission.PACKAGE_BIND, trace_id)
        eligible_states = {
            PackageLifecycleState.APPROVED,
            PackageLifecycleState.RELEASED_TO_ENV,
            PackageLifecycleState.ENABLED,
        }
        result: list[dict[str, object]] = []
        for installation in self._installations.list_installations():
            if installation.uninstalled_at is not None or installation.state not in eligible_states:
                continue
            if set(installation.granted_permissions) != set(installation.manifest.permissions):
                continue
            result.append(
                {
                    "installationId": str(installation.installation_id),
                    "packageId": installation.package_id,
                    "packageVersion": installation.package_version,
                    "state": installation.state.value,
                    "alreadyBound": self._repository.get_project_installation_binding(
                        project_id, installation.installation_id
                    )
                    is not None,
                }
            )
        return tuple(result)

    def create_project_binding(
        self,
        actor: ActorContext,
        project_id: UUID,
        *,
        installation_id: UUID,
        idempotency_key: str,
        trace_id: str,
    ) -> ProjectPackageBinding:
        project, workspace, organization = self._project_context(project_id, actor, trace_id)
        self._authorize_project(actor, project, Permission.PACKAGE_BIND, trace_id)
        self._require_project_writable(actor, project, workspace, organization, trace_id)
        installation = self._installations.get_by_id(installation_id)
        if installation is None:
            self._deny_hidden(actor, f"installation://{installation_id}", trace_id)
        assert installation is not None
        eligible_states = {
            PackageLifecycleState.APPROVED,
            PackageLifecycleState.RELEASED_TO_ENV,
            PackageLifecycleState.ENABLED,
        }
        if installation.uninstalled_at is not None or installation.state not in eligible_states:
            self._binding_denied(
                actor, project_id, installation_id, trace_id, "INSTALLATION_NOT_BINDABLE"
            )
        if set(installation.granted_permissions) != set(installation.manifest.permissions):
            self._binding_denied(
                actor, project_id, installation_id, trace_id, "PERMISSION_GRANT_REQUIRED"
            )
        existing = self._repository.get_project_installation_binding(project_id, installation_id)
        if existing is not None:
            if existing.state == BindingState.ACTIVE:
                return existing
            self._binding_denied(
                actor, project_id, installation_id, trace_id, "HISTORICAL_BINDING_NOT_REUSABLE"
            )
        now = datetime.now(UTC)
        binding = ProjectPackageBinding(
            project_id=project_id,
            installation_id=installation_id,
            package_kind=PackageKind.SCENARIO,
            created_at=now,
            updated_at=now,
            created_by=actor.principal.subject_ref,
            updated_by=actor.principal.subject_ref,
        )
        self._packages.bind_project(
            installation_id,
            project_id,
            actor_ref=actor.principal.subject_ref,
            trace_id=trace_id,
        )
        saved = self._repository.add_project_binding(binding, idempotency_key)
        self._audit_event(
            "project.package-binding.created.v1",
            actor.principal.subject_ref,
            f"project-package-binding://{saved.binding_id}",
            "SUCCESS",
            "PROJECT_BINDING_RECORDED",
            trace_id,
            scope_ref=f"project://{project_id}",
            details={
                "projectId": str(project_id),
                "installationId": str(installation_id),
                "environment": self._environment.value,
                "packageKind": saved.package_kind.value,
            },
        )
        return saved

    def disable_project_binding(
        self,
        actor: ActorContext,
        binding_id: UUID,
        expected_version: int,
        trace_id: str,
    ) -> ProjectPackageBinding:
        binding = self._repository.get_binding(binding_id)
        if binding is None:
            self._deny_hidden(actor, f"project-package-binding://{binding_id}", trace_id)
        assert binding is not None
        project = self._require_project(binding.project_id, actor, trace_id)
        self._authorize_project(actor, project, Permission.PACKAGE_BIND, trace_id)
        if binding.state != BindingState.ACTIVE:
            return binding
        updated = binding.model_copy(
            update={
                "state": BindingState.DISABLED,
                "updated_at": datetime.now(UTC),
                "updated_by": actor.principal.subject_ref,
            }
        )
        saved = self._repository.save_project_binding(updated, expected_version)
        self._audit_event(
            "project.package-binding.disabled.v1",
            actor.principal.subject_ref,
            f"project-package-binding://{binding_id}",
            "SUCCESS",
            "BINDING_DISABLED",
            trace_id,
            scope_ref=f"project://{binding.project_id}",
            details={"projectId": str(binding.project_id)},
        )
        return saved

    def project_audit_events(
        self, actor: ActorContext, project_id: UUID, trace_id: str, limit: int
    ) -> tuple[AuditEvent, ...]:
        project = self._require_project(project_id, actor, trace_id)
        self._authorize_project(actor, project, Permission.AUDIT_READ, trace_id)
        scope_ref = f"project://{project_id}"
        self._audit_event(
            "audit.project.read.v1",
            actor.principal.subject_ref,
            scope_ref,
            "SUCCESS",
            "SENSITIVE_AUDIT_READ",
            trace_id,
            scope_ref=scope_ref,
        )
        return tuple(
            event
            for event in self._audit.list_events(limit=min(max(limit * 5, 100), 500))
            if event.scope_ref == scope_ref
        )[:limit]

    def _require_organization(
        self, organization_id: UUID, actor: ActorContext, trace_id: str
    ) -> Organization:
        organization = self._repository.get_organization(organization_id)
        if organization is None:
            self._deny_hidden(actor, f"organization://{organization_id}", trace_id)
        assert organization is not None
        return organization

    def _require_workspace(
        self, workspace_id: UUID, actor: ActorContext, trace_id: str
    ) -> Workspace:
        workspace = self._repository.get_workspace(workspace_id)
        if workspace is None:
            self._deny_hidden(actor, f"workspace://{workspace_id}", trace_id)
        assert workspace is not None
        return workspace

    def _require_project(self, project_id: UUID, actor: ActorContext, trace_id: str) -> Project:
        project = self._repository.get_project(project_id)
        if project is None:
            self._deny_hidden(actor, f"project://{project_id}", trace_id)
        assert project is not None
        return project

    def _workspace_context(
        self, workspace_id: UUID, actor: ActorContext, trace_id: str
    ) -> tuple[Workspace, Organization]:
        workspace = self._require_workspace(workspace_id, actor, trace_id)
        organization = self._require_organization(workspace.organization_id, actor, trace_id)
        return workspace, organization

    def _project_context(
        self, project_id: UUID, actor: ActorContext, trace_id: str
    ) -> tuple[Project, Workspace, Organization]:
        project = self._require_project(project_id, actor, trace_id)
        workspace, organization = self._workspace_context(project.workspace_id, actor, trace_id)
        return project, workspace, organization

    def _authorize_organization(
        self,
        actor: ActorContext,
        organization: Organization,
        permission: Permission,
        trace_id: str,
    ) -> None:
        self._authorize(
            actor,
            permission,
            resource_ref=f"organization://{organization.organization_id}",
            scope_type=ScopeType.ORGANIZATION,
            scope_id=organization.organization_id,
            ancestor_scope_ids=frozenset(),
            trace_id=trace_id,
            conceal=True,
        )

    def _authorize_workspace(
        self, actor: ActorContext, workspace: Workspace, permission: Permission, trace_id: str
    ) -> None:
        self._authorize(
            actor,
            permission,
            resource_ref=f"workspace://{workspace.workspace_id}",
            scope_type=ScopeType.WORKSPACE,
            scope_id=workspace.workspace_id,
            ancestor_scope_ids=frozenset({workspace.organization_id}),
            trace_id=trace_id,
            conceal=True,
        )

    def _authorize_project(
        self, actor: ActorContext, project: Project, permission: Permission, trace_id: str
    ) -> None:
        workspace = self._repository.get_workspace(project.workspace_id)
        if workspace is None:
            self._deny_hidden(actor, f"project://{project.project_id}", trace_id)
        assert workspace is not None
        self._authorize(
            actor,
            permission,
            resource_ref=f"project://{project.project_id}",
            scope_type=ScopeType.PROJECT,
            scope_id=project.project_id,
            ancestor_scope_ids=frozenset({workspace.workspace_id, workspace.organization_id}),
            trace_id=trace_id,
            conceal=True,
        )

    def _authorize_scope(
        self,
        actor: ActorContext,
        scope_type: ScopeType,
        scope_id: UUID,
        permission: Permission,
        trace_id: str,
    ) -> None:
        if scope_type == ScopeType.ORGANIZATION:
            organization = self._require_organization(scope_id, actor, trace_id)
            self._authorize_organization(actor, organization, permission, trace_id)
        elif scope_type == ScopeType.WORKSPACE:
            workspace = self._require_workspace(scope_id, actor, trace_id)
            self._authorize_workspace(actor, workspace, permission, trace_id)
        elif scope_type == ScopeType.PROJECT:
            project = self._require_project(scope_id, actor, trace_id)
            self._authorize_project(actor, project, permission, trace_id)
        else:
            self.authorize_platform(actor, permission, trace_id)

    def _authorize(
        self,
        actor: ActorContext,
        permission: Permission,
        *,
        resource_ref: str,
        scope_type: ScopeType,
        scope_id: UUID | None,
        ancestor_scope_ids: frozenset[UUID],
        trace_id: str,
        conceal: bool,
    ) -> None:
        decision = self._authorization.decide(
            actor.principal,
            actor.memberships,
            permission,
            resource_ref=resource_ref,
            scope_type=scope_type,
            scope_id=scope_id,
            ancestor_scope_ids=ancestor_scope_ids,
        )
        self._decision_observer(permission.value, "allowed" if decision.allowed else "denied")
        if decision.allowed:
            return
        self._audit_event(
            "policy.decision.v1",
            actor.principal.subject_ref,
            resource_ref,
            "DENIED",
            decision.reason,
            trace_id,
            scope_ref=(
                f"{scope_type.value.lower()}://{scope_id}"
                if scope_id is not None
                else "platform://local"
            ),
            details={
                "action": permission.value,
                "allowed": False,
                "policyVersion": decision.policy_version,
            },
        )
        raise ForgeOpsError(
            ErrorCode.RESOURCE_NOT_FOUND if conceal else ErrorCode.FORBIDDEN,
            "resource is not available" if conceal else "permission denied",
            http_status=404 if conceal else 403,
        )

    def _try_authorize_organization(
        self, actor: ActorContext, organization: Organization, permission: Permission
    ) -> bool:
        return self._authorization.decide(
            actor.principal,
            actor.memberships,
            permission,
            resource_ref=f"organization://{organization.organization_id}",
            scope_type=ScopeType.ORGANIZATION,
            scope_id=organization.organization_id,
        ).allowed

    def _is_allowed_project(
        self, actor: ActorContext, project: Project, permission: Permission
    ) -> bool:
        workspace = self._repository.get_workspace(project.workspace_id)
        if workspace is None:
            return False
        return self._authorization.decide(
            actor.principal,
            actor.memberships,
            permission,
            resource_ref=f"project://{project.project_id}",
            scope_type=ScopeType.PROJECT,
            scope_id=project.project_id,
            ancestor_scope_ids=frozenset({workspace.workspace_id, workspace.organization_id}),
        ).allowed

    def _can_discover_organization(self, actor: ActorContext, organization_id: UUID) -> bool:
        for membership in actor.memberships:
            if membership.state != MembershipState.ACTIVE:
                continue
            if membership.scope_type == ScopeType.PLATFORM:
                return True
            if membership.scope_id is None:
                continue
            if (
                self._repository.organization_id_for_scope(
                    membership.scope_type, membership.scope_id
                )
                == organization_id
            ):
                return True
        return False

    def _can_discover_workspace(self, actor: ActorContext, workspace: Workspace) -> bool:
        if self._can_discover_organization(actor, workspace.organization_id):
            for membership in actor.memberships:
                if membership.state != MembershipState.ACTIVE:
                    continue
                if membership.scope_type in {ScopeType.PLATFORM, ScopeType.ORGANIZATION}:
                    return True
                if (
                    membership.scope_type == ScopeType.WORKSPACE
                    and membership.scope_id == workspace.workspace_id
                ):
                    return True
                if membership.scope_type == ScopeType.PROJECT and membership.scope_id is not None:
                    project = self._repository.get_project(membership.scope_id)
                    if project and project.workspace_id == workspace.workspace_id:
                        return True
        return False

    def _require_project_writable(
        self,
        actor: ActorContext,
        project: Project,
        workspace: Workspace,
        organization: Organization,
        trace_id: str,
    ) -> None:
        self._require_state(
            organization.state == OrganizationState.ACTIVE
            and workspace.state == WorkspaceState.ACTIVE
            and project.state != ProjectState.ARCHIVED,
            actor,
            project,
            trace_id,
            "PROJECT_NOT_WRITABLE",
        )

    def _binding_denied(
        self,
        actor: ActorContext,
        project_id: UUID,
        installation_id: UUID,
        trace_id: str,
        reason: str,
    ) -> None:
        self._audit_event(
            "project.package-binding.denied.v1",
            actor.principal.subject_ref,
            f"installation://{installation_id}",
            "DENIED",
            reason,
            trace_id,
            scope_ref=f"project://{project_id}",
            details={"projectId": str(project_id), "installationId": str(installation_id)},
        )
        raise ForgeOpsError(
            ErrorCode.ILLEGAL_STATE_TRANSITION,
            "package installation is not eligible for project binding",
            details={"reason": reason},
            http_status=409,
        )

    def _require_state(
        self,
        condition: bool,
        actor: ActorContext,
        resource: object,
        trace_id: str,
        reason: str,
    ) -> None:
        if condition:
            return
        resource_ref, scope_ref = self._resource_refs(resource)
        self._audit_event(
            "resource.transition.denied.v1",
            actor.principal.subject_ref,
            resource_ref,
            "DENIED",
            reason,
            trace_id,
            scope_ref=scope_ref,
        )
        raise ForgeOpsError(
            ErrorCode.ILLEGAL_STATE_TRANSITION,
            "resource state does not permit this operation",
            details={"reason": reason},
            http_status=409,
        )

    def _deny_hidden(self, actor: ActorContext, resource_ref: str, trace_id: str) -> None:
        self._audit_event(
            "policy.decision.v1",
            actor.principal.subject_ref,
            resource_ref,
            "DENIED",
            "RESOURCE_NOT_VISIBLE",
            trace_id,
            scope_ref="concealed://resource",
            details={"allowed": False, "policyVersion": self._authorization.policy_version},
        )
        raise ForgeOpsError(
            ErrorCode.RESOURCE_NOT_FOUND, "resource is not available", http_status=404
        )

    def _audit_success(
        self, event_type: str, actor: ActorContext, resource: object, trace_id: str, reason: str
    ) -> None:
        resource_ref, scope_ref = self._resource_refs(resource)
        self._audit_event(
            event_type,
            actor.principal.subject_ref,
            resource_ref,
            "SUCCESS",
            reason,
            trace_id,
            scope_ref=scope_ref,
            details={"version": getattr(resource, "version", 1)},
        )

    @staticmethod
    def _resource_refs(resource: object) -> tuple[str, str]:
        if isinstance(resource, Organization):
            ref = f"organization://{resource.organization_id}"
            return ref, ref
        if isinstance(resource, Workspace):
            return (
                f"workspace://{resource.workspace_id}",
                f"organization://{resource.organization_id}",
            )
        if isinstance(resource, Project):
            ref = f"project://{resource.project_id}"
            return ref, ref
        if isinstance(resource, Membership):
            scope = f"{resource.scope_type.value.lower()}://{resource.scope_id}"
            return f"membership://{resource.membership_id}", scope
        return "resource://unknown", "platform://local"

    def _audit_event(
        self,
        event_type: str,
        actor_ref: str,
        resource_ref: str,
        result: str,
        reason_code: str,
        trace_id: str,
        *,
        scope_ref: str,
        details: dict[str, object] | None = None,
    ) -> None:
        self._audit.append(
            AuditEvent(
                event_type=event_type,
                actor_ref=actor_ref,
                resource_ref=resource_ref,
                result=result,
                reason_code=reason_code,
                trace_id=trace_id,
                scope_ref=scope_ref,
                policy_version=self._authorization.policy_version,
                requirement_ids=("REQ-IAM-001", "REQ-POL-001", "REQ-OPS-001"),
                test_ids=("TEST-IAM-001", "TEST-POL-001"),
                details=details or {},
            )
        )
