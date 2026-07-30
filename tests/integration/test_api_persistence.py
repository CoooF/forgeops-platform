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
from sqlalchemy import text

from forgeops.api import create_app, database_engine
from forgeops.config import Settings


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'forgeops.db'}"
    monkeypatch.setenv("FORGEOPS_DATABASE_URL", database_url)
    configuration = Config("alembic.ini")
    command.upgrade(configuration, "head")
    app = create_app(
        Settings(database_url=database_url, object_store_path=str(tmp_path / "objects"))
    )
    with TestClient(app) as test_client:
        yield test_client


def submission(load_fixture: Any) -> dict[str, Any]:
    manifest, artifact = load_fixture("steel-cord-scheduling")
    return {
        "manifest": manifest,
        "artifactPayloadBase64": base64.b64encode(artifact).decode(),
    }


def test_health_auth_and_real_persistent_state(client: TestClient, load_fixture: Any) -> None:
    assert client.get("/health/live").json() == {"status": "live"}
    assert client.get("/health/ready").status_code == 200
    assert client.get("/v1/platform/status").status_code == 401

    headers = {"X-ForgeOps-Actor": "local-integration-owner", "X-Trace-ID": "trace-api-0001"}
    status = client.get("/v1/platform/status", headers=headers)
    assert status.json()["dataMode"] == "SYNTHETIC_ONLY"
    assert status.json()["enterpriseApproval"] == "NOT_GRANTED"

    installed = client.post(
        "/v1/scenario-package-installations", json=submission(load_fixture), headers=headers
    )
    assert installed.status_code == 201, installed.text
    installation_id = installed.json()["installationId"]
    listed = client.get("/v1/scenario-package-installations", headers=headers)
    assert [item["installationId"] for item in listed.json()] == [installation_id]

    second_app = create_app(
        Settings(
            database_url=str(database_engine(cast(FastAPI, client.app)).url),
            object_store_path=".local/test",
        )
    )
    with TestClient(second_app) as restarted:
        persisted = restarted.get("/v1/scenario-package-installations", headers=headers)
        assert [item["installationId"] for item in persisted.json()] == [installation_id]


def test_api_exposes_failure_paths_and_audit(client: TestClient, load_fixture: Any) -> None:
    headers = {"X-ForgeOps-Actor": "local-owner", "X-Trace-ID": "trace-api-0002"}
    body = submission(load_fixture)
    body["manifest"]["permissions"].append("proposal.write")
    denied = client.post("/v1/scenario-package-installations", json=body, headers=headers)
    assert denied.status_code == 422
    assert denied.json()["error"]["code"] == "UNKNOWN_PERMISSION"
    audit = client.get("/v1/audit-events", headers=headers).json()
    assert audit[0]["eventType"] == "scenario.package.compatibility.failed.v1"
    assert audit[0]["traceId"] == "trace-api-0002"


def test_api_logical_uninstall_persists_without_deleting_history(
    client: TestClient, load_fixture: Any
) -> None:
    headers = {"X-ForgeOps-Actor": "local-owner", "X-Trace-ID": "trace-api-uninstall"}
    installed = client.post(
        "/v1/scenario-package-installations", json=submission(load_fixture), headers=headers
    ).json()
    installation_id = installed["installationId"]
    permissions = installed["manifest"]["permissions"]
    assert (
        client.post(
            f"/v1/scenario-package-installations/{installation_id}:mark-tested", headers=headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/v1/scenario-package-installations/{installation_id}:approve", headers=headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/v1/scenario-package-installations/{installation_id}/permission-grants",
            json={"permissions": permissions},
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/v1/scenario-package-installations/{installation_id}/bindings",
            json={"bindingRef": "binding://local-contract-worker"},
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/v1/scenario-package-installations/{installation_id}/releases",
            json={"environment": "TEST", "actionAdapter": "MOCK"},
            headers=headers,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/v1/scenario-package-installations/{installation_id}/releases/TEST:disable",
            headers=headers,
        ).status_code
        == 200
    )

    uninstalled = client.post(
        f"/v1/scenario-package-installations/{installation_id}:uninstall", headers=headers
    )
    assert uninstalled.status_code == 200
    assert uninstalled.json()["uninstalledAt"] is not None
    assert uninstalled.json()["manifest"]["packageId"] == "steel-cord-scheduling"
    denied = client.get(
        f"/v1/scenario-package-installations/{installation_id}/run-eligibility/TEST",
        headers=headers,
    )
    assert denied.status_code == 409
    assert denied.json()["error"]["code"] == "PACKAGE_UNINSTALLED"

    second_app = create_app(
        Settings(
            database_url=str(database_engine(cast(FastAPI, client.app)).url),
            object_store_path=".local/test",
        )
    )
    with TestClient(second_app) as restarted:
        historical = restarted.get("/v1/scenario-package-installations", headers=headers).json()
        assert len(historical) == 1
        assert historical[0]["installationId"] == installation_id
        assert historical[0]["uninstalledAt"] is not None
        assert historical[0]["manifest"]["packageId"] == "steel-cord-scheduling"


def test_audit_table_rejects_update_and_delete(client: TestClient, load_fixture: Any) -> None:
    headers = {"X-ForgeOps-Actor": "local-owner", "X-Trace-ID": "trace-api-0003"}
    client.post(
        "/v1/scenario-package-installations", json=submission(load_fixture), headers=headers
    )
    engine = database_engine(cast(FastAPI, client.app))
    with engine.begin() as connection:
        with pytest.raises(Exception, match="append-only"):
            connection.execute(text("UPDATE audit_events SET result = 'MUTATED'"))
    with engine.begin() as connection:
        with pytest.raises(Exception, match="append-only"):
            connection.execute(text("DELETE FROM audit_events"))
