from __future__ import annotations

import base64
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient

from forgeops.api import create_app, database_engine
from forgeops.config import Settings


@pytest.fixture
def identity_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'identity.db'}"
    monkeypatch.setenv("FORGEOPS_DATABASE_URL", database_url)
    command.upgrade(Config("alembic.ini"), "head")
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        yield client


def headers(actor: str = "local-owner", key: str | None = None) -> dict[str, str]:
    result = {"X-ForgeOps-Actor": actor, "X-Trace-ID": f"trace-{actor}"}
    if key:
        result["Idempotency-Key"] = key
    return result


def create_hierarchy(
    client: TestClient, *, suffix: str = "one"
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    organization = client.post(
        "/v1/organizations",
        headers=headers(key=f"org-{suffix}"),
        json={"name": f"Organization {suffix}", "slug": f"organization-{suffix}"},
    )
    assert organization.status_code == 201, organization.text
    workspace = client.post(
        f"/v1/organizations/{organization.json()['organizationId']}/workspaces",
        headers=headers(key=f"workspace-{suffix}"),
        json={"name": f"Workspace {suffix}", "slug": f"workspace-{suffix}"},
    )
    assert workspace.status_code == 201, workspace.text
    project = client.post(
        f"/v1/workspaces/{workspace.json()['workspaceId']}/projects",
        headers=headers(key=f"project-{suffix}"),
        json={
            "name": f"Project {suffix}",
            "slug": f"project-{suffix}",
            "description": "SYNTHETIC project scope",
        },
    )
    assert project.status_code == 201, project.text
    return organization.json(), workspace.json(), project.json()


def grant_project_role(
    client: TestClient,
    organization_id: str,
    project_id: str,
    principal_ref: str,
    role: str,
) -> dict[str, Any]:
    response = client.post(
        f"/v1/organizations/{organization_id}/memberships",
        headers=headers(key=f"grant-{project_id}-{principal_ref}-{role}"),
        json={
            "principalRef": principal_ref,
            "scopeType": "PROJECT",
            "scopeId": project_id,
            "role": role,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def package_submission(load_fixture: Any) -> dict[str, Any]:
    manifest, artifact = load_fixture("steel-cord-scheduling")
    return {
        "manifest": manifest,
        "artifactPayloadBase64": base64.b64encode(artifact).decode(),
    }


def approve_package(client: TestClient, load_fixture: Any) -> dict[str, Any]:
    installed = client.post(
        "/v1/scenario-package-installations",
        headers=headers(),
        json=package_submission(load_fixture),
    )
    assert installed.status_code == 201, installed.text
    installation_id = installed.json()["installationId"]
    assert (
        client.post(
            f"/v1/scenario-package-installations/{installation_id}:mark-tested",
            headers=headers(),
        ).status_code
        == 200
    )
    approved = client.post(
        f"/v1/scenario-package-installations/{installation_id}:approve", headers=headers()
    )
    assert approved.status_code == 200
    granted = client.post(
        f"/v1/scenario-package-installations/{installation_id}/permission-grants",
        headers=headers(),
        json={"permissions": approved.json()["manifest"]["permissions"]},
    )
    assert granted.status_code == 200
    return granted.json()


def test_authentication_is_not_authorization(identity_client: TestClient) -> None:
    assert identity_client.get("/v1/me").status_code == 401
    unknown = identity_client.get("/v1/me", headers=headers("forged-owner"))
    assert unknown.status_code == 401
    assert unknown.json()["error"]["code"] == "UNAUTHORIZED"
    disabled = identity_client.get("/v1/me", headers=headers("local-disabled"))
    assert disabled.status_code == 401
    assert disabled.json()["error"]["code"] == "PRINCIPAL_DISABLED"
    outsider = identity_client.post(
        "/v1/organizations",
        headers=headers("local-outsider", "forged-org"),
        json={"name": "Forged", "slug": "forged-org"},
    )
    assert outsider.status_code == 403
    assert outsider.json()["error"]["code"] == "FORBIDDEN"


def test_owner_hierarchy_idempotency_concurrency_and_restart(
    identity_client: TestClient,
) -> None:
    organization, workspace, project = create_hierarchy(identity_client)
    replay = identity_client.post(
        "/v1/organizations",
        headers=headers(key="org-one"),
        json={"name": "Different ignored replay", "slug": "different-replay"},
    )
    assert replay.status_code == 201
    assert replay.json()["organizationId"] == organization["organizationId"]
    updated = identity_client.patch(
        f"/v1/projects/{project['projectId']}",
        headers=headers(),
        json={"description": "updated synthetic scope", "expectedVersion": 1},
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2
    conflict = identity_client.patch(
        f"/v1/projects/{project['projectId']}",
        headers=headers(),
        json={"name": "stale update", "expectedVersion": 1},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "CONCURRENCY_CONFLICT"

    database_url = str(database_engine(cast(FastAPI, identity_client.app)).url)
    with TestClient(create_app(Settings(database_url=database_url))) as restarted:
        organizations = restarted.get("/v1/organizations", headers=headers()).json()["items"]
        assert [item["organizationId"] for item in organizations] == [
            organization["organizationId"]
        ]
        projects = restarted.get(
            f"/v1/workspaces/{workspace['workspaceId']}/projects", headers=headers()
        ).json()["items"]
        assert projects[0]["version"] == 2
        assert projects[0]["description"] == "updated synthetic scope"


def test_scope_filter_viewer_denial_and_immediate_revocation(identity_client: TestClient) -> None:
    organization_one, workspace_one, project_one = create_hierarchy(identity_client, suffix="one")
    _, workspace_two, project_two = create_hierarchy(identity_client, suffix="two")
    membership = grant_project_role(
        identity_client,
        organization_one["organizationId"],
        project_one["projectId"],
        "local-viewer",
        "PROJECT_VIEWER",
    )
    viewer = headers("local-viewer")
    visible = identity_client.get(
        f"/v1/workspaces/{workspace_one['workspaceId']}/projects", headers=viewer
    )
    assert [item["projectId"] for item in visible.json()["items"]] == [project_one["projectId"]]
    assert (
        identity_client.get(f"/v1/projects/{project_two['projectId']}", headers=viewer).status_code
        == 404
    )
    denied = identity_client.patch(
        f"/v1/projects/{project_one['projectId']}",
        headers=viewer,
        json={"name": "forbidden", "expectedVersion": 1},
    )
    assert denied.status_code == 404
    assert denied.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    suspended = identity_client.post(
        f"/v1/memberships/{membership['membershipId']}:suspend",
        headers=headers(),
        json={"expectedVersion": membership["version"]},
    )
    assert suspended.status_code == 200
    assert (
        identity_client.get(f"/v1/projects/{project_one['projectId']}", headers=viewer).status_code
        == 404
    )
    assert (
        identity_client.get(
            f"/v1/workspaces/{workspace_two['workspaceId']}/projects", headers=viewer
        ).status_code
        == 404
    )


def test_last_owner_extra_fields_and_archived_scope_fail_closed(
    identity_client: TestClient,
) -> None:
    organization, workspace, project = create_hierarchy(identity_client)
    memberships = identity_client.get(
        f"/v1/organizations/{organization['organizationId']}/memberships", headers=headers()
    ).json()["items"]
    owner = next(item for item in memberships if item["role"] == "ORG_OWNER")
    blocked = identity_client.post(
        f"/v1/memberships/{owner['membershipId']}:revoke",
        headers=headers(),
        json={"expectedVersion": owner["version"]},
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "LAST_OWNER_REQUIRED"
    second_owner = identity_client.post(
        f"/v1/organizations/{organization['organizationId']}/memberships",
        headers=headers(key="second-organization-owner"),
        json={
            "principalRef": "local-editor",
            "scopeType": "ORGANIZATION",
            "scopeId": organization["organizationId"],
            "role": "ORG_OWNER",
        },
    )
    assert second_owner.status_code == 201
    first_revoked = identity_client.post(
        f"/v1/memberships/{owner['membershipId']}:revoke",
        headers=headers(),
        json={"expectedVersion": owner["version"]},
    )
    assert first_revoked.status_code == 200
    final_owner_blocked = identity_client.post(
        f"/v1/memberships/{second_owner.json()['membershipId']}:revoke",
        headers=headers(),
        json={"expectedVersion": second_owner.json()["version"]},
    )
    assert final_owner_blocked.status_code == 409
    assert final_owner_blocked.json()["error"]["code"] == "LAST_OWNER_REQUIRED"
    strict = identity_client.post(
        f"/v1/workspaces/{workspace['workspaceId']}/projects",
        headers=headers(key="extra-field"),
        json={"name": "Strict", "slug": "strict-project", "clientRole": "ORG_OWNER"},
    )
    assert strict.status_code == 422
    archived = identity_client.post(
        f"/v1/projects/{project['projectId']}:archive",
        headers=headers(),
        json={"expectedVersion": project["version"]},
    )
    assert archived.status_code == 200
    denied = identity_client.patch(
        f"/v1/projects/{project['projectId']}",
        headers=headers(),
        json={"name": "cannot write", "expectedVersion": archived.json()["version"]},
    )
    assert denied.status_code == 409
    assert denied.json()["error"]["code"] == "ILLEGAL_STATE_TRANSITION"


def test_membership_scope_grant_is_unique_even_with_a_new_idempotency_key(
    identity_client: TestClient,
) -> None:
    organization, _, project = create_hierarchy(identity_client)
    grant_project_role(
        identity_client,
        organization["organizationId"],
        project["projectId"],
        "local-viewer",
        "PROJECT_VIEWER",
    )
    duplicate = identity_client.post(
        f"/v1/organizations/{organization['organizationId']}/memberships",
        headers=headers(key="different-key-same-grant"),
        json={
            "principalRef": "local-viewer",
            "scopeType": "PROJECT",
            "scopeId": project["projectId"],
            "role": "PROJECT_VIEWER",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_project_package_binding_uses_real_project_and_preserves_legacy(
    identity_client: TestClient, load_fixture: Any
) -> None:
    organization, _, project = create_hierarchy(identity_client)
    installation = approve_package(identity_client, load_fixture)
    installation_id = installation["installationId"]
    forged = identity_client.post(
        f"/v1/scenario-package-installations/{installation_id}/bindings",
        headers=headers(),
        json={"bindingRef": f"project://{project['projectId']}"},
    )
    assert forged.status_code == 422
    assert forged.json()["error"]["code"] == "INPUT_INVALID"
    bound = identity_client.post(
        f"/v1/projects/{project['projectId']}/package-bindings",
        headers=headers(key="project-binding"),
        json={"installationId": installation_id},
    )
    assert bound.status_code == 201, bound.text
    assert bound.json()["projectId"] == project["projectId"]
    assert bound.json()["packageKind"] == "SCENARIO"
    viewer_membership = grant_project_role(
        identity_client,
        organization["organizationId"],
        project["projectId"],
        "local-viewer",
        "PROJECT_VIEWER",
    )
    denied = identity_client.post(
        f"/v1/projects/{project['projectId']}/package-bindings",
        headers=headers("local-viewer", "viewer-binding"),
        json={"installationId": installation_id},
    )
    assert denied.status_code == 404
    assert viewer_membership["role"] == "PROJECT_VIEWER"
    bindings = identity_client.get(
        f"/v1/projects/{project['projectId']}/package-bindings",
        headers=headers("local-viewer"),
    ).json()["items"]
    assert bindings[0]["installationId"] == installation_id
    audit = identity_client.get(
        f"/v1/projects/{project['projectId']}/audit-events", headers=headers()
    )
    assert audit.status_code == 200
    assert any(
        event["eventType"] == "project.package-binding.created.v1"
        for event in audit.json()["items"]
    )
