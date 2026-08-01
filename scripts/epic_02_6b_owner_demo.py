from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from forgeops.api import create_app
from forgeops.config import Settings

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "contracts/fds/examples"
ACTOR_HEADERS = {
    "X-ForgeOps-Actor": "local-owner",
    "X-Trace-ID": "epic-02-6b-owner-demo",
}
TARGET_VERSIONS = {"platform": "0.1.0", "fds": "0.1.0", "scenarioSdk": "0.1.0"}


def fixture(name: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((EXAMPLES / name).read_text()))


def version_two_domain() -> dict[str, Any]:
    manifest = deepcopy(fixture("reference-domain-a.domain.json"))
    digest = "sha256:" + "9" * 64
    manifest["packageVersion"] = "0.2.0"
    manifest["contentDigest"] = digest
    manifest["artifact"]["contentDigest"] = digest
    manifest["artifact"]["signature"] = "local-sha256:" + "9" * 64
    manifest["artifact"]["artifactRef"] = "local://owner-demo/reference-domain-a-v2"
    manifest["provenance"]["sourceRef"] = "local://owner-demo/reference-domain-a-v2"
    return manifest


def headers(key: str | None = None, *, actor: str = "local-owner") -> dict[str, str]:
    result = {**ACTOR_HEADERS, "X-ForgeOps-Actor": actor}
    if key is not None:
        result["Idempotency-Key"] = key
    return result


def expect(response: Any, status: int) -> dict[str, Any]:
    if response.status_code != status:
        raise RuntimeError(
            f"owner demo expected HTTP {status}, got {response.status_code}: {response.text}"
        )
    return cast(dict[str, Any], response.json())


def register(client: TestClient, manifest: dict[str, Any], key: str) -> dict[str, Any]:
    return expect(
        client.post(
            "/v1/fds/package-versions",
            headers=headers(key),
            json={"manifest": manifest},
        ),
        201,
    )


def install(client: TestClient, organization_id: str, root_id: str, key: str) -> dict[str, Any]:
    return expect(
        client.post(
            f"/v1/organizations/{organization_id}/domain-installations",
            headers=headers(key),
            json={
                "rootPackageVersionId": root_id,
                "targetVersions": TARGET_VERSIONS,
                "includeOptional": False,
            },
        ),
        201,
    )


def run_demo(database_url: str) -> dict[str, Any]:
    settings = Settings(database_url=database_url)
    with TestClient(create_app(settings)) as client:
        organization = expect(
            client.post(
                "/v1/organizations",
                headers=headers("owner-demo-organization"),
                json={"name": "Owner Demo Organization", "slug": "owner-demo-organization"},
            ),
            201,
        )
        workspace = expect(
            client.post(
                f"/v1/organizations/{organization['organizationId']}/workspaces",
                headers=headers("owner-demo-workspace"),
                json={"name": "Owner Demo Workspace", "slug": "owner-demo-workspace"},
            ),
            201,
        )
        project = expect(
            client.post(
                f"/v1/workspaces/{workspace['workspaceId']}/projects",
                headers=headers("owner-demo-project"),
                json={
                    "name": "Owner Demo Project",
                    "slug": "owner-demo-project",
                    "description": "SYNTHETIC Registry governance evidence",
                },
            ),
            201,
        )
        project = expect(
            client.post(
                f"/v1/projects/{project['projectId']}:activate",
                headers=headers(),
                json={"expectedVersion": project["version"]},
            ),
            200,
        )
        component = register(
            client, fixture("core-semantics.component.json"), "owner-demo-component"
        )
        domain_v1 = register(
            client, fixture("reference-domain-a.domain.json"), "owner-demo-domain-v1"
        )
        domain_v2 = register(client, version_two_domain(), "owner-demo-domain-v2")
        installation_v1 = install(
            client,
            organization["organizationId"],
            domain_v1["packageVersionId"],
            "owner-demo-install-v1",
        )
        installation_v2 = install(
            client,
            organization["organizationId"],
            domain_v2["packageVersionId"],
            "owner-demo-install-v2",
        )
        first_lock = expect(
            client.post(
                f"/v1/projects/{project['projectId']}/domain-locks",
                headers=headers("owner-demo-lock-v1"),
                json={
                    "installationId": installation_v1["installationId"],
                    "purpose": "owner demo first selection",
                },
            ),
            201,
        )
        second_lock = expect(
            client.post(
                f"/v1/projects/{project['projectId']}/domain-locks",
                headers=headers("owner-demo-lock-v2"),
                json={
                    "installationId": installation_v2["installationId"],
                    "purpose": "owner demo version switch",
                },
            ),
            201,
        )
        history = expect(
            client.get(f"/v1/projects/{project['projectId']}/domain-locks", headers=headers()),
            200,
        )
        expect(
            client.post(
                f"/v1/organizations/{organization['organizationId']}/memberships",
                headers=headers("owner-demo-viewer"),
                json={
                    "principalRef": "local-viewer",
                    "scopeType": "PROJECT",
                    "scopeId": project["projectId"],
                    "role": "PROJECT_VIEWER",
                },
            ),
            201,
        )
        viewer_current_status = client.get(
            f"/v1/projects/{project['projectId']}/domain-locks/current",
            headers=headers(actor="local-viewer"),
        ).status_code
        viewer_history_status = client.get(
            f"/v1/projects/{project['projectId']}/domain-locks",
            headers=headers(actor="local-viewer"),
        ).status_code
        outsider_status = client.get(
            f"/v1/projects/{project['projectId']}/domain-locks/current",
            headers=headers(actor="local-outsider"),
        ).status_code
        withdrawn = expect(
            client.post(
                f"/v1/fds/package-versions/{component['packageVersionId']}:withdraw",
                headers={**headers("owner-demo-withdraw"), "If-Match": "1"},
                json={"reason": "owner demo transitive withdrawal"},
            ),
            200,
        )
        impact = expect(
            client.get(
                f"/v1/fds/package-versions/{component['packageVersionId']}/impacts",
                headers=headers(),
            ),
            200,
        )
        blocked = client.post(
            f"/v1/projects/{project['projectId']}/domain-locks",
            headers=headers("owner-demo-blocked-lock"),
            json={
                "installationId": installation_v2["installationId"],
                "purpose": "must fail after transitive withdrawal",
            },
        )
        blocked_payload = expect(blocked, 409)
        current_after_withdrawal = expect(
            client.get(
                f"/v1/projects/{project['projectId']}/domain-locks/current",
                headers=headers(),
            ),
            200,
        )

    with TestClient(create_app(settings)) as restarted:
        persisted_current = expect(
            restarted.get(
                f"/v1/projects/{project['projectId']}/domain-locks/current",
                headers=headers(),
            ),
            200,
        )
        persisted_history = expect(
            restarted.get(f"/v1/projects/{project['projectId']}/domain-locks", headers=headers()),
            200,
        )

    return {
        "scope": "LOCAL_SYNTHETIC_REGISTRY_ENGINEERING",
        "registry": {
            "registeredVersions": 3,
            "trustBoundary": component["trustBoundary"],
            "withdrawnState": withdrawn["governance"]["state"],
        },
        "installation": {
            "count": 2,
            "states": [
                installation_v1["installationState"]["state"],
                installation_v2["installationState"]["state"],
            ],
            "lockDigests": [
                installation_v1["immutableFacts"]["lockDigest"],
                installation_v2["immutableFacts"]["lockDigest"],
            ],
            "authorizationEffect": installation_v1["immutableFacts"]["authorizationEffect"],
            "runtimeStateCreated": installation_v1["immutableFacts"]["runtimeStateCreated"],
            "semanticRuntimeReady": installation_v1["immutableFacts"]["semanticRuntimeReady"],
        },
        "projectDomainLock": {
            "firstStatus": next(
                item["lockState"]["status"]
                for item in history["items"]
                if item["projectDomainLockId"] == first_lock["projectDomainLockId"]
            ),
            "currentStatus": second_lock["lockState"]["status"],
            "historyCount": history["total"],
            "currentHealthAfterWithdrawal": current_after_withdrawal["derivedHealth"]["health"],
            "persistedAcrossRestart": (
                persisted_current["projectDomainLockId"] == second_lock["projectDomainLockId"]
                and persisted_history["total"] == 2
            ),
        },
        "withdrawalImpact": {
            "installationCount": len(impact["installations"]),
            "projectDomainLockCount": len(impact["projectDomainLocks"]),
            "newUseStatus": blocked.status_code,
            "newUseErrorCode": blocked_payload["error"]["code"],
        },
        "authorization": {
            "viewerCurrentStatus": viewer_current_status,
            "viewerHistoryStatus": viewer_history_status,
            "outsiderStatus": outsider_status,
            "crossScopeSuccessfulReads": 0,
        },
        "notImplemented": [
            "semantic or knowledge runtime",
            "workflow or Agent runtime",
            "enterprise signature, license, or publisher verification",
            "real data, external model, network, or control-system action",
        ],
    }


def main() -> None:
    descriptor, raw_path = tempfile.mkstemp(prefix="forgeops-epic-02-6b-", suffix=".db")
    os.close(descriptor)
    database_path = Path(raw_path).resolve()
    database_path.unlink()
    database_url = f"sqlite+pysqlite:///{database_path}"
    previous = os.environ.get("FORGEOPS_DATABASE_URL")
    os.environ["FORGEOPS_DATABASE_URL"] = database_url
    try:
        command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
        result = run_demo(database_url)
        print(json.dumps(result, indent=2, sort_keys=True))
    finally:
        if previous is None:
            os.environ.pop("FORGEOPS_DATABASE_URL", None)
        else:
            os.environ["FORGEOPS_DATABASE_URL"] = previous
        database_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
