from __future__ import annotations

import json
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from forgeops.api import create_app, database_engine
from forgeops.config import Settings
from forgeops.platform_adapters.postgres.models import (
    FdsInstallationRow,
    ProjectDomainLockRow,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "contracts" / "fds" / "examples"
TARGET_VERSIONS = {"platform": "0.1.0", "fds": "0.1.0", "scenarioSdk": "0.1.0"}


@pytest.fixture
def domain_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'domain-registry.db'}"
    monkeypatch.setenv("FORGEOPS_DATABASE_URL", database_url)
    command.upgrade(Config("alembic.ini"), "head")
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        yield client


def fixture(name: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((EXAMPLES / name).read_text()))


def headers(
    actor: str = "local-owner", *, key: str | None = None, version: int | None = None
) -> dict[str, str]:
    result = {"X-ForgeOps-Actor": actor, "X-Trace-ID": f"trace-fds-{actor}"}
    if key is not None:
        result["Idempotency-Key"] = key
    if version is not None:
        result["If-Match"] = str(version)
    return result


def create_scope(
    client: TestClient, suffix: str, *, activate: bool = True
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    organization_response = client.post(
        "/v1/organizations",
        headers=headers(key=f"organization-{suffix}"),
        json={"name": f"Synthetic Organization {suffix}", "slug": f"synthetic-org-{suffix}"},
    )
    assert organization_response.status_code == 201, organization_response.text
    organization = organization_response.json()
    workspace_response = client.post(
        f"/v1/organizations/{organization['organizationId']}/workspaces",
        headers=headers(key=f"workspace-{suffix}"),
        json={"name": f"Synthetic Workspace {suffix}", "slug": f"synthetic-ws-{suffix}"},
    )
    assert workspace_response.status_code == 201, workspace_response.text
    workspace = workspace_response.json()
    project_response = client.post(
        f"/v1/workspaces/{workspace['workspaceId']}/projects",
        headers=headers(key=f"project-{suffix}"),
        json={
            "name": f"Synthetic Project {suffix}",
            "slug": f"synthetic-project-{suffix}",
            "description": "SYNTHETIC contract-only project",
        },
    )
    assert project_response.status_code == 201, project_response.text
    project = project_response.json()
    if activate:
        activated = client.post(
            f"/v1/projects/{project['projectId']}:activate",
            headers=headers(),
            json={"expectedVersion": project["version"]},
        )
        assert activated.status_code == 200, activated.text
        project = activated.json()
    return organization, workspace, project


def grant(
    client: TestClient,
    organization_id: str,
    principal_ref: str,
    scope_type: str,
    scope_id: str,
    role: str,
) -> dict[str, Any]:
    response = client.post(
        f"/v1/organizations/{organization_id}/memberships",
        headers=headers(key=f"grant-{principal_ref}-{scope_id}-{role}"),
        json={
            "principalRef": principal_ref,
            "scopeType": scope_type,
            "scopeId": scope_id,
            "role": role,
        },
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


def register(
    client: TestClient,
    manifest: dict[str, Any],
    *,
    key: str,
    owner_organization_id: str | None = None,
    actor: str = "local-owner",
) -> dict[str, Any]:
    body: dict[str, Any] = {"manifest": manifest}
    if owner_organization_id is not None:
        body["ownerOrganizationId"] = owner_organization_id
    response = client.post("/v1/fds/package-versions", headers=headers(actor, key=key), json=body)
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


def register_root_graph(client: TestClient) -> tuple[dict[str, Any], dict[str, Any]]:
    component = register(
        client, fixture("core-semantics.component.json"), key="register-component-v1"
    )
    domain = register(client, fixture("reference-domain-a.domain.json"), key="register-domain-v1")
    return component, domain


def installation_body(root: dict[str, Any]) -> dict[str, Any]:
    return {
        "rootPackageVersionId": root["packageVersionId"],
        "targetVersions": TARGET_VERSIONS,
        "includeOptional": False,
    }


def install(
    client: TestClient, organization_id: str, root: dict[str, Any], *, key: str
) -> dict[str, Any]:
    response = client.post(
        f"/v1/organizations/{organization_id}/domain-installations",
        headers=headers(key=key),
        json=installation_body(root),
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


def version_two_domain() -> dict[str, Any]:
    manifest = deepcopy(fixture("reference-domain-a.domain.json"))
    manifest["packageVersion"] = "0.2.0"
    digest = "sha256:" + "9" * 64
    manifest["contentDigest"] = digest
    manifest["artifact"]["contentDigest"] = digest
    manifest["artifact"]["signature"] = "local-sha256:" + "9" * 64
    manifest["artifact"]["artifactRef"] = "local://fds-fixtures/reference-domain-a-v2/artifact"
    manifest["provenance"]["sourceRef"] = "local://fds-fixtures/reference-domain-a-v2"
    return manifest


def test_fds_registry_four_kinds_strict_idempotent_and_private_scope(
    domain_client: TestClient,
) -> None:
    organization_one, _, _ = create_scope(domain_client, "one")
    organization_two, _, _ = create_scope(domain_client, "two")
    component, domain = register_root_graph(domain_client)
    scenario = register(
        domain_client,
        fixture("contract-shape.scenario.json"),
        key="register-scenario-v1",
    )
    overlay = register(
        domain_client,
        fixture("synthetic-organization.overlay.json"),
        key="register-overlay-v1",
        owner_organization_id=organization_one["organizationId"],
    )
    assert {
        component["immutableFacts"]["kind"],
        domain["immutableFacts"]["kind"],
        scenario["immutableFacts"]["kind"],
        overlay["immutableFacts"]["kind"],
    } == {"COMPONENT", "DOMAIN", "SCENARIO", "ORGANIZATION_OVERLAY"}
    assert overlay["trustBoundary"] == "NOT_ENTERPRISE_VERIFIED"
    assert overlay["runtimeCapabilityEnabled"] is False

    replay = domain_client.post(
        "/v1/fds/package-versions",
        headers=headers(key="register-component-v1"),
        json={"manifest": fixture("core-semantics.component.json")},
    )
    assert replay.status_code == 201
    assert replay.json()["packageVersionId"] == component["packageVersionId"]
    conflicting_key = domain_client.post(
        "/v1/fds/package-versions",
        headers=headers(key="register-component-v1"),
        json={"manifest": version_two_domain()},
    )
    assert conflicting_key.status_code == 409
    assert conflicting_key.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"

    digest_conflict = fixture("core-semantics.component.json")
    digest_conflict["contentDigest"] = "sha256:" + "7" * 64
    digest_conflict["artifact"]["contentDigest"] = "sha256:" + "7" * 64
    digest_conflict["artifact"]["signature"] = "local-sha256:" + "7" * 64
    conflict = domain_client.post(
        "/v1/fds/package-versions",
        headers=headers(key="immutable-conflict"),
        json={"manifest": digest_conflict},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "PACKAGE_VERSION_DIGEST_CONFLICT"

    invalid = fixture("core-semantics.component.json")
    invalid["unknownField"] = True
    rejected = domain_client.post(
        "/v1/fds/package-versions",
        headers=headers(key="invalid-manifest"),
        json={"manifest": invalid},
    )
    assert rejected.status_code == 422
    listed = domain_client.get("/v1/fds/package-versions", headers=headers()).json()
    assert listed["total"] == 4

    grant(
        domain_client,
        organization_two["organizationId"],
        "local-editor",
        "ORGANIZATION",
        organization_two["organizationId"],
        "ORG_OWNER",
    )
    concealed = domain_client.get(
        f"/v1/fds/package-versions/{overlay['packageVersionId']}",
        headers=headers("local-editor"),
    )
    assert concealed.status_code == 404
    assert concealed.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    cross_scope_list = domain_client.get(
        "/v1/fds/package-versions?visibility=ORGANIZATION_PRIVATE",
        headers=headers("local-editor"),
    )
    assert cross_scope_list.status_code == 200
    assert cross_scope_list.json()["total"] == 0
    concealed_reregistration = domain_client.post(
        "/v1/fds/package-versions",
        headers=headers("local-editor", key="cross-org-overlay-reregister"),
        json={
            "manifest": fixture("synthetic-organization.overlay.json"),
            "ownerOrganizationId": organization_two["organizationId"],
        },
    )
    assert concealed_reregistration.status_code == 404
    assert concealed_reregistration.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert overlay["packageVersionId"] not in concealed_reregistration.text


def test_installation_lock_switch_persistence_diff_and_viewer_read_only(
    domain_client: TestClient,
) -> None:
    organization, _, project = create_scope(domain_client, "lock")
    _, domain_v1 = register_root_graph(domain_client)
    domain_v2 = register(domain_client, version_two_domain(), key="register-domain-v2")
    preview = domain_client.post(
        f"/v1/organizations/{organization['organizationId']}/domain-installations:preview",
        headers=headers(),
        json=installation_body(domain_v1),
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["immutableFacts"]["runtimeStateCreated"] is False
    assert preview.json()["immutableFacts"]["authorizationEffect"] == "NONE"
    installation_v1 = install(
        domain_client, organization["organizationId"], domain_v1, key="install-v1"
    )
    replay = install(domain_client, organization["organizationId"], domain_v1, key="install-v1")
    assert replay["installationId"] == installation_v1["installationId"]
    natural_replay = install(
        domain_client,
        organization["organizationId"],
        domain_v1,
        key="install-v1-natural-replay",
    )
    assert natural_replay["installationId"] == installation_v1["installationId"]
    installation_v2 = install(
        domain_client, organization["organizationId"], domain_v2, key="install-v2"
    )
    reused_natural_key = domain_client.post(
        f"/v1/organizations/{organization['organizationId']}/domain-installations",
        headers=headers(key="install-v1-natural-replay"),
        json=installation_body(domain_v2),
    )
    assert reused_natural_key.status_code == 409
    assert reused_natural_key.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    diff = domain_client.post(
        f"/v1/domain-installations/{installation_v1['installationId']}:compare",
        headers=headers(),
        json={"toInstallationId": installation_v2["installationId"]},
    )
    assert diff.status_code == 200, diff.text
    assert [item["packageId"] for item in diff.json()["changed"]] == [
        "org.forgeops.domain.reference-a"
    ]
    assert diff.json()["semanticDifferenceStatus"] == "NOT_EVALUATED"

    first = domain_client.post(
        f"/v1/projects/{project['projectId']}/domain-locks",
        headers=headers(key="project-lock-v1"),
        json={
            "installationId": installation_v1["installationId"],
            "purpose": "first synthetic immutable selection",
        },
    )
    assert first.status_code == 201, first.text
    second = domain_client.post(
        f"/v1/projects/{project['projectId']}/domain-locks",
        headers=headers(key="project-lock-v2"),
        json={
            "installationId": installation_v2["installationId"],
            "purpose": "second synthetic immutable selection",
        },
    )
    assert second.status_code == 201, second.text
    current_replay = domain_client.post(
        f"/v1/projects/{project['projectId']}/domain-locks",
        headers=headers(key="project-lock-v2-natural-replay"),
        json={
            "installationId": installation_v2["installationId"],
            "purpose": "same current natural replay",
        },
    )
    assert current_replay.status_code == 201
    assert current_replay.json()["projectDomainLockId"] == second.json()["projectDomainLockId"]
    current_replay_conflict = domain_client.post(
        f"/v1/projects/{project['projectId']}/domain-locks",
        headers=headers(key="project-lock-v2-natural-replay"),
        json={
            "installationId": installation_v2["installationId"],
            "purpose": "same key but different purpose",
        },
    )
    assert current_replay_conflict.status_code == 409
    assert current_replay_conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    history = domain_client.get(
        f"/v1/projects/{project['projectId']}/domain-locks", headers=headers()
    ).json()["items"]
    assert [item["lockState"]["status"] for item in history] == [
        "CURRENT",
        "SUPERSEDED",
    ]
    assert history[1]["projectDomainLockId"] == first.json()["projectDomainLockId"]
    assert (
        history[1]["immutableFacts"]["lockDigest"]
        == (installation_v1["immutableFacts"]["lockDigest"])
    )

    viewer_membership = grant(
        domain_client,
        organization["organizationId"],
        "local-viewer",
        "PROJECT",
        project["projectId"],
        "PROJECT_VIEWER",
    )
    viewer_current = domain_client.get(
        f"/v1/projects/{project['projectId']}/domain-locks/current",
        headers=headers("local-viewer"),
    )
    assert viewer_current.status_code == 200
    assert '"manifest":' not in json.dumps(viewer_current.json()).lower()
    viewer_history = domain_client.get(
        f"/v1/projects/{project['projectId']}/domain-locks",
        headers=headers("local-viewer"),
    )
    assert viewer_history.status_code == 404
    viewer_write = domain_client.post(
        f"/v1/projects/{project['projectId']}/domain-locks",
        headers=headers("local-viewer", key="viewer-write"),
        json={
            "installationId": installation_v1["installationId"],
            "purpose": "viewer must not switch",
        },
    )
    assert viewer_write.status_code == 404
    outsider = domain_client.get(
        f"/v1/projects/{project['projectId']}/domain-locks/current",
        headers=headers("local-outsider"),
    )
    assert outsider.status_code == 404
    denial_events = [
        item
        for item in domain_client.get("/v1/audit-events", headers=headers()).json()
        if item["eventType"] == "domain.policy.decision.v1"
        and item["actorRef"] in {"local-viewer", "local-outsider"}
    ]
    assert denial_events
    assert all(item["result"] == "DENIED" for item in denial_events)
    assert all(item["reasonCode"] == "RESOURCE_NOT_VISIBLE" for item in denial_events)
    assert all(item["scopeRef"] == "concealed://resource" for item in denial_events)
    assert all(item["policyVersion"] == "identity-access-v1" for item in denial_events)
    assert all(item["traceId"].startswith("trace-fds-") for item in denial_events)
    revoked = domain_client.post(
        f"/v1/memberships/{viewer_membership['membershipId']}:revoke",
        headers=headers(),
        json={"expectedVersion": viewer_membership["version"]},
    )
    assert revoked.status_code == 200
    revoked_viewer_current = domain_client.get(
        f"/v1/projects/{project['projectId']}/domain-locks/current",
        headers=headers("local-viewer"),
    )
    assert revoked_viewer_current.status_code == 404

    database_url = str(database_engine(cast(FastAPI, domain_client.app)).url)
    with TestClient(create_app(Settings(database_url=database_url))) as restarted:
        current = restarted.get(
            f"/v1/projects/{project['projectId']}/domain-locks/current", headers=headers()
        )
        assert current.status_code == 200
        assert current.json()["projectDomainLockId"] == second.json()["projectDomainLockId"]
        persisted_history = restarted.get(
            f"/v1/projects/{project['projectId']}/domain-locks", headers=headers()
        ).json()
        assert persisted_history["total"] == 2


def test_withdrawal_impact_blocks_new_use_and_preserves_history(
    domain_client: TestClient,
) -> None:
    organization, _, project = create_scope(domain_client, "impact")
    component, domain = register_root_graph(domain_client)
    installation = install(
        domain_client, organization["organizationId"], domain, key="impact-install"
    )
    locked = domain_client.post(
        f"/v1/projects/{project['projectId']}/domain-locks",
        headers=headers(key="impact-lock"),
        json={
            "installationId": installation["installationId"],
            "purpose": "synthetic impact baseline",
        },
    )
    assert locked.status_code == 201
    withdrawn = domain_client.post(
        f"/v1/fds/package-versions/{component['packageVersionId']}:withdraw",
        headers=headers(key="withdraw-transitive", version=1),
        json={"reason": "synthetic transitive withdrawal evidence"},
    )
    assert withdrawn.status_code == 200, withdrawn.text
    replay_after_withdrawal = domain_client.post(
        f"/v1/organizations/{organization['organizationId']}/domain-installations",
        headers=headers(key="impact-install"),
        json=installation_body(domain),
    )
    assert replay_after_withdrawal.status_code == 201
    assert replay_after_withdrawal.json()["installationId"] == installation["installationId"]
    impacts = domain_client.get(
        f"/v1/fds/package-versions/{component['packageVersionId']}/impacts",
        headers=headers(),
    )
    assert impacts.status_code == 200
    assert [item["installationId"] for item in impacts.json()["installations"]] == [
        installation["installationId"]
    ]
    assert [item["projectDomainLockId"] for item in impacts.json()["projectDomainLocks"]] == [
        locked.json()["projectDomainLockId"]
    ]
    current = domain_client.get(
        f"/v1/projects/{project['projectId']}/domain-locks/current", headers=headers()
    )
    assert current.json()["derivedHealth"]["health"] == "AT_RISK"
    assert (
        current.json()["immutableFacts"]["lockDigest"]
        == (installation["immutableFacts"]["lockDigest"])
    )

    new_install = domain_client.post(
        f"/v1/organizations/{organization['organizationId']}/domain-installations",
        headers=headers(key="blocked-install"),
        json=installation_body(domain),
    )
    assert new_install.status_code == 422
    assert new_install.json()["error"]["code"] == "DEPENDENCY_RESOLUTION_FAILED"
    new_lock = domain_client.post(
        f"/v1/projects/{project['projectId']}/domain-locks",
        headers=headers(key="blocked-lock"),
        json={
            "installationId": installation["installationId"],
            "purpose": "blocked after transitive withdrawal",
        },
    )
    assert new_lock.status_code == 409
    assert new_lock.json()["error"]["code"] == "WITHDRAWN_OR_QUARANTINED_DEPENDENCY"

    disabled = domain_client.post(
        f"/v1/domain-installations/{installation['installationId']}:disable",
        headers=headers(key="disable-current-install", version=1),
        json={"reason": "synthetic lifecycle check"},
    )
    assert disabled.status_code == 200
    uninstall = domain_client.post(
        f"/v1/domain-installations/{installation['installationId']}:logical-uninstall",
        headers=headers(key="uninstall-current-install", version=2),
        json={"reason": "must retain current lock history"},
    )
    assert uninstall.status_code == 409
    assert uninstall.json()["error"]["code"] == "UNINSTALL_BLOCKED_BY_CURRENT_LOCK"
    after = domain_client.get(
        f"/v1/projects/{project['projectId']}/domain-locks/current", headers=headers()
    ).json()
    assert "INSTALLATION_DISABLED" in after["derivedHealth"]["reasons"]

    audit = domain_client.get("/v1/audit-events", headers=headers()).json()
    event_types = {item["eventType"] for item in audit}
    assert {
        "domain.package.withdrawn.v1",
        "domain.package.impact.detected.v1",
        "domain.installation.created-disabled.v1",
        "project.domain-lock.created.v1",
    }.issubset(event_types)


def test_archived_cross_organization_tampered_and_double_current_fail_closed(
    domain_client: TestClient,
) -> None:
    organization_one, workspace_one, project_one = create_scope(domain_client, "negative-one")
    organization_two, _, project_two = create_scope(domain_client, "negative-two")
    _, domain = register_root_graph(domain_client)
    installation = install(
        domain_client, organization_one["organizationId"], domain, key="negative-install"
    )
    cross_scope = domain_client.post(
        f"/v1/projects/{project_two['projectId']}/domain-locks",
        headers=headers(key="cross-scope-lock"),
        json={
            "installationId": installation["installationId"],
            "purpose": "cross organization must fail",
        },
    )
    assert cross_scope.status_code == 404

    archived = domain_client.post(
        f"/v1/projects/{project_one['projectId']}:archive",
        headers=headers(),
        json={"expectedVersion": project_one["version"]},
    )
    assert archived.status_code == 200
    archived_lock = domain_client.post(
        f"/v1/projects/{project_one['projectId']}/domain-locks",
        headers=headers(key="archived-lock"),
        json={
            "installationId": installation["installationId"],
            "purpose": "archived project must fail",
        },
    )
    assert archived_lock.status_code == 409
    assert archived_lock.json()["error"]["code"] == "PROJECT_NOT_ACTIVE"

    active_lock = domain_client.post(
        f"/v1/projects/{project_two['projectId']}/domain-locks",
        headers=headers(key="local-lock"),
        json={
            "installationId": install(
                domain_client,
                organization_two["organizationId"],
                domain,
                key="second-org-install",
            )["installationId"],
            "purpose": "database uniqueness proof",
        },
    )
    assert active_lock.status_code == 201
    engine = database_engine(cast(FastAPI, domain_client.app))
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            current = (
                connection.execute(
                    select(ProjectDomainLockRow).where(
                        ProjectDomainLockRow.project_domain_lock_id
                        == UUID(active_lock.json()["projectDomainLockId"])
                    )
                )
                .mappings()
                .one()
            )
            duplicate = dict(current)
            duplicate["project_domain_lock_id"] = UUID("30000000-0000-4000-8000-000000000003")
            connection.execute(
                cast(Any, ProjectDomainLockRow.__table__).insert().values(**duplicate)
            )

    with engine.begin() as connection:
        connection.execute(
            cast(Any, FdsInstallationRow.__table__)
            .update()
            .where(FdsInstallationRow.installation_id == UUID(installation["installationId"]))
            .values(lock_digest="sha256:" + "0" * 64)
        )
    tampered_project_response = domain_client.post(
        f"/v1/workspaces/{workspace_one['workspaceId']}/projects",
        headers=headers(key="tampered-project"),
        json={
            "name": "Synthetic Tamper Project",
            "slug": "synthetic-tamper-project",
            "description": "SYNTHETIC integrity rejection project",
        },
    )
    assert tampered_project_response.status_code == 201
    tampered_project = tampered_project_response.json()
    tampered_project = domain_client.post(
        f"/v1/projects/{tampered_project['projectId']}:activate",
        headers=headers(),
        json={"expectedVersion": 1},
    ).json()
    tampered = domain_client.post(
        f"/v1/projects/{tampered_project['projectId']}/domain-locks",
        headers=headers(key="tampered-lock"),
        json={
            "installationId": installation["installationId"],
            "purpose": "tampered digest must fail",
        },
    )
    assert tampered.status_code == 409
    assert tampered.json()["error"]["code"] == "LOCK_DIGEST_MISMATCH"


def test_api_contract_headers_status_codes_and_openapi_stability(
    domain_client: TestClient,
) -> None:
    assert domain_client.get("/v1/fds/package-versions").status_code == 401
    missing_key = domain_client.post(
        "/v1/fds/package-versions",
        headers=headers(),
        json={"manifest": fixture("core-semantics.component.json")},
    )
    assert missing_key.status_code == 422
    component = register(
        domain_client,
        fixture("core-semantics.component.json"),
        key="api-component",
    )
    missing_match = domain_client.post(
        f"/v1/fds/package-versions/{component['packageVersionId']}:quarantine",
        headers=headers(key="missing-match"),
        json={"reason": "missing optimistic concurrency header"},
    )
    assert missing_match.status_code == 422
    invalid_match = domain_client.post(
        f"/v1/fds/package-versions/{component['packageVersionId']}:quarantine",
        headers={**headers(key="bad-match"), "If-Match": "invalid"},
        json={"reason": "invalid optimistic concurrency header"},
    )
    assert invalid_match.status_code == 422
    quarantined = domain_client.post(
        f"/v1/fds/package-versions/{component['packageVersionId']}:quarantine",
        headers=headers(key="quarantine-idempotency", version=1),
        json={"reason": "synthetic quarantine reason one"},
    )
    assert quarantined.status_code == 200
    changed_replay = domain_client.post(
        f"/v1/fds/package-versions/{component['packageVersionId']}:quarantine",
        headers=headers(key="quarantine-idempotency", version=2),
        json={"reason": "synthetic quarantine reason two"},
    )
    assert changed_replay.status_code == 409
    assert changed_replay.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    app = cast(FastAPI, domain_client.app)
    openapi_one = json.dumps(
        app.openapi(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    app.openapi_schema = None
    openapi_two = json.dumps(
        app.openapi(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    assert openapi_one == openapi_two
    assert "/v1/projects/{project_id}/domain-locks/current" in json.loads(openapi_one)["paths"]


def test_scenario_descriptor_registry_does_not_create_legacy_runtime_truth(
    domain_client: TestClient,
) -> None:
    registered = register(
        domain_client,
        fixture("contract-shape.scenario.json"),
        key="descriptor-only",
    )
    assert registered["immutableFacts"]["kind"] == "SCENARIO"
    legacy = domain_client.get("/v1/scenario-package-installations", headers=headers())
    assert legacy.status_code == 200
    assert legacy.json() == []
    engine = database_engine(cast(FastAPI, domain_client.app))
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM scenario_package_installations")
            ).scalar_one()
            == 0
        )
