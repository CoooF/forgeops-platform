from __future__ import annotations

from typing import Annotated, Any, cast
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, Query, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from forgeops.platform_core.identity_access.entities import MembershipState, Role, ScopeType
from forgeops.platform_core.identity_access.service import ActorContext, IdentityAccessService


def require_identity_actor(
    request: Request,
    x_forgeops_actor: Annotated[str | None, Header()] = None,
) -> ActorContext:
    identity = cast(IdentityAccessService, request.app.state.identity)
    return identity.authenticate(x_forgeops_actor, str(request.state.trace_id))


Actor = Annotated[ActorContext, Depends(require_identity_actor)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class CreateOrganizationRequest(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(pattern=r"^[a-z][a-z0-9-]{2,62}[a-z0-9]$")


class CreateWorkspaceRequest(CreateOrganizationRequest):
    pass


class CreateProjectRequest(CreateOrganizationRequest):
    description: str = Field(default="", max_length=1000)


class PatchResourceRequest(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    slug: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9-]{2,62}[a-z0-9]$")
    expected_version: int = Field(alias="expectedVersion", ge=1)


class PatchBasicResourceRequest(PatchResourceRequest):
    @model_validator(mode="after")
    def require_change(self) -> PatchBasicResourceRequest:
        if self.name is None and self.slug is None:
            raise ValueError("at least one mutable field is required")
        return self


class PatchProjectRequest(PatchResourceRequest):
    description: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def require_project_change(self) -> PatchProjectRequest:
        if self.name is None and self.slug is None and self.description is None:
            raise ValueError("at least one mutable field is required")
        return self


class VersionRequest(ApiModel):
    expected_version: int = Field(alias="expectedVersion", ge=1)


class CreateMembershipRequest(ApiModel):
    principal_ref: str = Field(alias="principalRef", min_length=1, max_length=256)
    scope_type: ScopeType = Field(alias="scopeType")
    scope_id: UUID = Field(alias="scopeId")
    role: Role


class CreateProjectBindingRequest(ApiModel):
    installation_id: UUID = Field(alias="installationId")


def page(items: tuple[Any, ...], *, limit: int, offset: int) -> dict[str, Any]:
    selected = items[offset : offset + limit]
    return {
        "items": [
            item.model_dump(mode="json", by_alias=True) if isinstance(item, BaseModel) else item
            for item in selected
        ],
        "total": len(items),
        "limit": limit,
        "offset": offset,
    }


def register_identity_routes(app: FastAPI, identity: IdentityAccessService) -> None:
    def key(value: str | None) -> str:
        return value or f"generated-{uuid4()}"

    @app.get("/v1/me", tags=["identity-access"])
    def me(actor: Actor) -> dict[str, object]:
        return identity.me(actor)

    @app.get("/v1/organizations", tags=["identity-access"])
    def list_organizations(actor: Actor, limit: Limit = 50, offset: Offset = 0) -> dict[str, Any]:
        return page(identity.list_organizations(actor), limit=limit, offset=offset)

    @app.post("/v1/organizations", status_code=201, tags=["identity-access"])
    def create_organization(
        body: CreateOrganizationRequest,
        actor: Actor,
        request: Request,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> dict[str, Any]:
        return identity.create_organization(
            actor,
            name=body.name,
            slug=body.slug,
            idempotency_key=key(idempotency_key),
            trace_id=str(request.state.trace_id),
        ).model_dump(mode="json", by_alias=True)

    @app.get("/v1/organizations/{organization_id}", tags=["identity-access"])
    def get_organization(organization_id: UUID, actor: Actor, request: Request) -> dict[str, Any]:
        return identity.get_organization(
            actor, organization_id, str(request.state.trace_id)
        ).model_dump(mode="json", by_alias=True)

    @app.patch("/v1/organizations/{organization_id}", tags=["identity-access"])
    def update_organization(
        organization_id: UUID,
        body: PatchBasicResourceRequest,
        actor: Actor,
        request: Request,
    ) -> dict[str, Any]:
        return identity.update_organization(
            actor,
            organization_id,
            name=body.name,
            slug=body.slug,
            expected_version=body.expected_version,
            trace_id=str(request.state.trace_id),
        ).model_dump(mode="json", by_alias=True)

    @app.post("/v1/organizations/{organization_id}:archive", tags=["identity-access"])
    def archive_organization(
        organization_id: UUID, body: VersionRequest, actor: Actor, request: Request
    ) -> dict[str, Any]:
        return identity.archive_organization(
            actor,
            organization_id,
            body.expected_version,
            str(request.state.trace_id),
        ).model_dump(mode="json", by_alias=True)

    @app.get("/v1/organizations/{organization_id}/workspaces", tags=["identity-access"])
    def list_workspaces(
        organization_id: UUID,
        actor: Actor,
        request: Request,
        limit: Limit = 50,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        return page(
            identity.list_workspaces(actor, organization_id, str(request.state.trace_id)),
            limit=limit,
            offset=offset,
        )

    @app.post(
        "/v1/organizations/{organization_id}/workspaces",
        status_code=201,
        tags=["identity-access"],
    )
    def create_workspace(
        organization_id: UUID,
        body: CreateWorkspaceRequest,
        actor: Actor,
        request: Request,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> dict[str, Any]:
        return identity.create_workspace(
            actor,
            organization_id,
            name=body.name,
            slug=body.slug,
            idempotency_key=key(idempotency_key),
            trace_id=str(request.state.trace_id),
        ).model_dump(mode="json", by_alias=True)

    @app.get("/v1/workspaces/{workspace_id}", tags=["identity-access"])
    def get_workspace(workspace_id: UUID, actor: Actor, request: Request) -> dict[str, Any]:
        return identity.get_workspace(actor, workspace_id, str(request.state.trace_id)).model_dump(
            mode="json", by_alias=True
        )

    @app.patch("/v1/workspaces/{workspace_id}", tags=["identity-access"])
    def update_workspace(
        workspace_id: UUID,
        body: PatchBasicResourceRequest,
        actor: Actor,
        request: Request,
    ) -> dict[str, Any]:
        return identity.update_workspace(
            actor,
            workspace_id,
            name=body.name,
            slug=body.slug,
            expected_version=body.expected_version,
            trace_id=str(request.state.trace_id),
        ).model_dump(mode="json", by_alias=True)

    @app.post("/v1/workspaces/{workspace_id}:archive", tags=["identity-access"])
    def archive_workspace(
        workspace_id: UUID, body: VersionRequest, actor: Actor, request: Request
    ) -> dict[str, Any]:
        return identity.archive_workspace(
            actor, workspace_id, body.expected_version, str(request.state.trace_id)
        ).model_dump(mode="json", by_alias=True)

    @app.get("/v1/workspaces/{workspace_id}/projects", tags=["identity-access"])
    def list_projects(
        workspace_id: UUID,
        actor: Actor,
        request: Request,
        limit: Limit = 50,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        return page(
            identity.list_projects(actor, workspace_id, str(request.state.trace_id)),
            limit=limit,
            offset=offset,
        )

    @app.post(
        "/v1/workspaces/{workspace_id}/projects",
        status_code=201,
        tags=["identity-access"],
    )
    def create_project(
        workspace_id: UUID,
        body: CreateProjectRequest,
        actor: Actor,
        request: Request,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> dict[str, Any]:
        return identity.create_project(
            actor,
            workspace_id,
            name=body.name,
            slug=body.slug,
            description=body.description,
            idempotency_key=key(idempotency_key),
            trace_id=str(request.state.trace_id),
        ).model_dump(mode="json", by_alias=True)

    @app.get("/v1/projects/{project_id}", tags=["identity-access"])
    def get_project(project_id: UUID, actor: Actor, request: Request) -> dict[str, Any]:
        return identity.get_project(actor, project_id, str(request.state.trace_id)).model_dump(
            mode="json", by_alias=True
        )

    @app.patch("/v1/projects/{project_id}", tags=["identity-access"])
    def update_project(
        project_id: UUID,
        body: PatchProjectRequest,
        actor: Actor,
        request: Request,
    ) -> dict[str, Any]:
        return identity.update_project(
            actor,
            project_id,
            name=body.name,
            slug=body.slug,
            description=body.description,
            expected_version=body.expected_version,
            trace_id=str(request.state.trace_id),
        ).model_dump(mode="json", by_alias=True)

    @app.post("/v1/projects/{project_id}:activate", tags=["identity-access"])
    def activate_project(
        project_id: UUID, body: VersionRequest, actor: Actor, request: Request
    ) -> dict[str, Any]:
        return identity.activate_project(
            actor, project_id, body.expected_version, str(request.state.trace_id)
        ).model_dump(mode="json", by_alias=True)

    @app.post("/v1/projects/{project_id}:archive", tags=["identity-access"])
    def archive_project(
        project_id: UUID, body: VersionRequest, actor: Actor, request: Request
    ) -> dict[str, Any]:
        return identity.archive_project(
            actor, project_id, body.expected_version, str(request.state.trace_id)
        ).model_dump(mode="json", by_alias=True)

    @app.get("/v1/organizations/{organization_id}/memberships", tags=["identity-access"])
    def list_memberships(
        organization_id: UUID,
        actor: Actor,
        request: Request,
        limit: Limit = 50,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        return page(
            identity.list_memberships(actor, organization_id, str(request.state.trace_id)),
            limit=limit,
            offset=offset,
        )

    @app.post(
        "/v1/organizations/{organization_id}/memberships",
        status_code=201,
        tags=["identity-access"],
    )
    def create_membership(
        organization_id: UUID,
        body: CreateMembershipRequest,
        actor: Actor,
        request: Request,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> dict[str, Any]:
        return identity.create_membership(
            actor,
            organization_id,
            principal_ref=body.principal_ref,
            scope_type=body.scope_type,
            scope_id=body.scope_id,
            role=body.role,
            idempotency_key=key(idempotency_key),
            trace_id=str(request.state.trace_id),
        ).model_dump(mode="json", by_alias=True)

    def transition_membership(
        membership_id: UUID,
        body: VersionRequest,
        actor: ActorContext,
        request: Request,
        state: MembershipState,
    ) -> dict[str, Any]:
        return identity.transition_membership(
            actor,
            membership_id,
            state,
            body.expected_version,
            str(request.state.trace_id),
        ).model_dump(mode="json", by_alias=True)

    @app.post("/v1/memberships/{membership_id}:suspend", tags=["identity-access"])
    def suspend_membership(
        membership_id: UUID, body: VersionRequest, actor: Actor, request: Request
    ) -> dict[str, Any]:
        return transition_membership(membership_id, body, actor, request, MembershipState.SUSPENDED)

    @app.post("/v1/memberships/{membership_id}:revoke", tags=["identity-access"])
    def revoke_membership(
        membership_id: UUID, body: VersionRequest, actor: Actor, request: Request
    ) -> dict[str, Any]:
        return transition_membership(membership_id, body, actor, request, MembershipState.REVOKED)

    @app.get("/v1/projects/{project_id}/package-bindings", tags=["identity-access"])
    def list_project_bindings(
        project_id: UUID,
        actor: Actor,
        request: Request,
        limit: Limit = 50,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        return page(
            identity.list_project_bindings(actor, project_id, str(request.state.trace_id)),
            limit=limit,
            offset=offset,
        )

    @app.get("/v1/projects/{project_id}/memberships", tags=["identity-access"])
    def project_memberships(
        project_id: UUID,
        actor: Actor,
        request: Request,
        limit: Limit = 50,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        return page(
            identity.project_memberships(actor, project_id, str(request.state.trace_id)),
            limit=limit,
            offset=offset,
        )

    @app.get("/v1/projects/{project_id}/permissions", tags=["identity-access"])
    def project_permissions(project_id: UUID, actor: Actor, request: Request) -> dict[str, Any]:
        return {
            "permissions": list(
                identity.project_permissions(actor, project_id, str(request.state.trace_id))
            )
        }

    @app.get("/v1/projects/{project_id}/bindable-installations", tags=["identity-access"])
    def bindable_installations(
        project_id: UUID,
        actor: Actor,
        request: Request,
        limit: Limit = 50,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        return page(
            identity.bindable_installations(actor, project_id, str(request.state.trace_id)),
            limit=limit,
            offset=offset,
        )

    @app.post(
        "/v1/projects/{project_id}/package-bindings",
        status_code=201,
        tags=["identity-access"],
    )
    def create_project_binding(
        project_id: UUID,
        body: CreateProjectBindingRequest,
        actor: Actor,
        request: Request,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> dict[str, Any]:
        return identity.create_project_binding(
            actor,
            project_id,
            installation_id=body.installation_id,
            idempotency_key=key(idempotency_key),
            trace_id=str(request.state.trace_id),
        ).model_dump(mode="json", by_alias=True)

    @app.post("/v1/project-package-bindings/{binding_id}:disable", tags=["identity-access"])
    def disable_project_binding(
        binding_id: UUID, body: VersionRequest, actor: Actor, request: Request
    ) -> dict[str, Any]:
        return identity.disable_project_binding(
            actor, binding_id, body.expected_version, str(request.state.trace_id)
        ).model_dump(mode="json", by_alias=True)

    @app.get("/v1/projects/{project_id}/audit-events", tags=["identity-access"])
    def project_audit_events(
        project_id: UUID,
        actor: Actor,
        request: Request,
        limit: Limit = 50,
    ) -> dict[str, Any]:
        events = identity.project_audit_events(
            actor, project_id, str(request.state.trace_id), limit
        )
        return page(events, limit=limit, offset=0)
