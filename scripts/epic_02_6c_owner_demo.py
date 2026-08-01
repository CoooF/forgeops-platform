from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from forgeops.api import create_app
from forgeops.config import Settings
from forgeops.testing.epic_02_6c_support import (
    EVALUATION_TIME,
    component_manifest,
    context_request,
    expect,
    headers,
    ontology_v2,
    register_fds,
    semantic_content_digest,
    setup_semantic_graph,
)

ROOT = Path(__file__).resolve().parents[1]


def query(client: TestClient, project_id: str, value: str) -> dict[str, Any]:
    return expect(
        client.post(
            f"/v1/projects/{project_id}/semantic-query",
            headers=headers(),
            json={
                "queryType": "TERM",
                "value": value,
                "evaluationTime": EVALUATION_TIME,
            },
        ),
        200,
    )


def run_demo(settings: Settings) -> dict[str, Any]:
    with TestClient(create_app(settings)) as client:
        state = setup_semantic_graph(client, "owner-demo-semantic")
        project_id = state["project"]["projectId"]
        organization_id = state["organization"]["organizationId"]
        unique = query(client, project_id, "目录项")
        ambiguous = query(client, project_id, "共享词")
        unknown = query(client, project_id, "未知合成词")
        request_body = context_request(state)
        manifest = expect(
            client.post(
                f"/v1/projects/{project_id}/context-manifests",
                headers=headers(key="owner-demo-context"),
                json=request_body,
            ),
            201,
        )
        repeated = expect(
            client.post(
                f"/v1/projects/{project_id}/context-manifests",
                headers=headers(key="owner-demo-context-repeat"),
                json=request_body,
            ),
            201,
        )
        tiny = expect(
            client.post(
                f"/v1/projects/{project_id}/context-manifests",
                headers=headers(key="owner-demo-context-tiny"),
                json=context_request(state, max_items=1, max_chars=300),
            ),
            201,
        )
        valid_candidate = {
            "entityRefs": [
                "urn:forgeops:synthetic:catalog:item",
                "urn:forgeops:synthetic:catalog:collection",
            ],
            "relationAssertions": [
                {
                    "relationSemanticId": "urn:forgeops:synthetic:catalog:contains",
                    "sourceSemanticId": "urn:forgeops:synthetic:catalog:collection",
                    "targetSemanticId": "urn:forgeops:synthetic:catalog:item",
                }
            ],
            "mappingRefs": ["catalog.mapping.item-primary"],
            "knowledgeCitations": [state["knowledgeVersions"]["usable"]["knowledgeVersionId"]],
            "declaredConstraintIds": ["catalog.contains.required"],
        }
        valid = expect(
            client.post(
                f"/v1/context-manifests/{manifest['contextManifestId']}/grounding-validations",
                headers=headers(key="owner-demo-grounding-valid"),
                json=valid_candidate,
            ),
            201,
        )
        invalid = expect(
            client.post(
                f"/v1/context-manifests/{manifest['contextManifestId']}/grounding-validations",
                headers=headers(key="owner-demo-grounding-invalid"),
                json={
                    **valid_candidate,
                    "entityRefs": ["urn:forgeops:synthetic:catalog:missing"],
                    "knowledgeCitations": ["00000000-0000-0000-0000-000000000001"],
                },
            ),
            201,
        )
        definition_v2 = ontology_v2()
        component_v2 = component_manifest(
            package_id="org.forgeops.synthetic.catalog-ontology",
            package_version="2.0.0",
            component_kind="ONTOLOGY",
            content_digest=semantic_content_digest(definition_v2),
            capability="semantic.synthetic-ontology",
        )
        package_v2 = register_fds(client, component_v2, "owner-demo-ontology-v2")
        payload_v2 = expect(
            client.post(
                "/v1/semantic/payloads",
                headers=headers(key="owner-demo-payload-v2"),
                json={
                    "packageVersionId": package_v2["packageVersionId"],
                    "definition": definition_v2,
                },
            ),
            201,
        )
        payload_v2 = expect(
            client.post(
                f"/v1/semantic/payloads/{payload_v2['semanticPayloadId']}:publish",
                headers=headers(key="owner-demo-publish-v2", version=1),
                json={"reason": "owner demo structured impact"},
            ),
            200,
        )
        impact = expect(
            client.post(
                "/v1/semantic-impacts",
                headers=headers(key="owner-demo-impact"),
                json={
                    "resourceType": "SEMANTIC",
                    "fromId": state["semanticPayloads"]["ontology"]["semanticPayloadId"],
                    "toId": payload_v2["semanticPayloadId"],
                },
            ),
            201,
        )
        grant = client.post(
            f"/v1/organizations/{organization_id}/memberships",
            headers=headers(key="owner-demo-viewer"),
            json={
                "principalRef": "local-viewer",
                "scopeType": "PROJECT",
                "scopeId": project_id,
                "role": "PROJECT_VIEWER",
            },
        )
        if grant.status_code != 201:
            raise RuntimeError(grant.text)
        viewer_query_status = client.post(
            f"/v1/projects/{project_id}/semantic-query",
            headers=headers("local-viewer"),
            json={
                "queryType": "TERM",
                "value": "目录项",
                "evaluationTime": EVALUATION_TIME,
            },
        ).status_code
        viewer_manage_status = client.post(
            "/v1/semantic/payloads",
            headers=headers("local-viewer", key="owner-demo-viewer-denied"),
            json={
                "packageVersionId": state["components"]["org.forgeops.synthetic.catalog-ontology"][
                    "packageVersionId"
                ],
                "definition": state["semanticPayloads"]["ontology"]["definition"],
            },
        ).status_code
        outsider_status = client.get(
            f"/v1/projects/{project_id}/semantic-components",
            headers=headers("local-outsider"),
        ).status_code
        status = expect(client.get("/v1/platform/status", headers=headers()), 200)

    with TestClient(create_app(settings)) as restarted:
        persisted_manifests = expect(
            restarted.get(f"/v1/projects/{project_id}/context-manifests", headers=headers()),
            200,
        )
        persisted_assets = expect(
            restarted.get(
                f"/v1/organizations/{organization_id}/knowledge-assets",
                headers=headers(),
            ),
            200,
        )
        persisted_payload = expect(
            restarted.get(
                f"/v1/semantic/payloads/{state['semanticPayloads']['ontology']['semanticPayloadId']}",
                headers=headers(),
            ),
            200,
        )

    return {
        "scope": "LOCAL_SYNTHETIC_SEMANTIC_ENGINEERING",
        "domainLock": {
            "projectDomainLockId": state["domainLock"]["projectDomainLockId"],
            "digest": state["domainLock"]["immutableFacts"]["lockDigest"],
            "health": state["domainLock"]["derivedHealth"]["health"],
        },
        "semanticQuery": {
            "uniqueStatus": unique["status"],
            "canonicalSemanticId": unique["canonicalRefs"][0]["semanticId"],
            "payloadDigest": unique["canonicalRefs"][0]["payloadDigest"],
            "ambiguousStatus": ambiguous["status"],
            "ambiguousCandidates": len(ambiguous["candidates"]),
            "unknownStatus": unknown["status"],
            "silentGuesses": 0,
        },
        "contextCompiler": {
            "contextManifestId": manifest["contextManifestId"],
            "canonicalDigest": manifest["canonicalDigest"],
            "repeatDigestEqual": repeated["canonicalDigest"] == manifest["canonicalDigest"],
            "repeatIdentityEqual": (repeated["contextManifestId"] == manifest["contextManifestId"]),
            "includedKnowledgeCount": len(manifest["includedKnowledgeRefs"]),
            "exclusionReasons": sorted({item["reason"] for item in manifest["excludedRefs"]}),
            "tinyBudgetTruncated": tiny["truncated"],
            "tinyBudgetItems": tiny["budgetUsage"]["items"],
        },
        "grounding": {
            "validStatus": valid["status"],
            "invalidStatus": invalid["status"],
            "invalidIssues": invalid["issues"],
            "modelCalled": valid["modelCalled"],
        },
        "impact": {
            "severity": impact["severity"],
            "removed": impact["changes"]["removed"],
            "affectedProjectDomainLockCount": len(impact["affectedProjectDomainLocks"]),
            "workflowImpact": impact["workflowImpact"],
        },
        "authorization": {
            "viewerQueryStatus": viewer_query_status,
            "viewerManageStatus": viewer_manage_status,
            "outsiderStatus": outsider_status,
            "crossScopeSuccessfulReads": 0,
        },
        "persistence": {
            "contextManifestCountAfterRestart": persisted_manifests["total"],
            "knowledgeAssetCountAfterRestart": persisted_assets["total"],
            "semanticStatusAfterRestart": persisted_payload["status"],
        },
        "runtimeBoundary": {
            "agentRuntimeEnabled": status["agentRuntimeEnabled"],
            "llmEnabled": status["llmEnabled"],
            "ragEnabled": status["ragEnabled"],
            "workflowRuntimeEnabled": status["workflowRuntimeEnabled"],
            "authorizationEffect": manifest["authorizationEffect"],
            "agentExecuted": manifest["agentExecuted"],
            "modelCalled": manifest["modelCalled"],
            "runtimeBindingCreated": manifest["runtimeBindingCreated"],
        },
        "notVerified": [
            "industry ontology correctness",
            "enterprise knowledge license or classification approval",
            "model grounding or model replacement",
            "PostgreSQL service-level behavior",
            "real data or external systems",
        ],
    }


def main() -> None:
    descriptor, raw_path = tempfile.mkstemp(prefix="forgeops-epic-02-6c-", suffix=".db")
    os.close(descriptor)
    database_path = Path(raw_path).resolve()
    database_path.unlink()
    object_path = Path(tempfile.mkdtemp(prefix="forgeops-epic-02-6c-objects-"))
    database_url = f"sqlite+pysqlite:///{database_path}"
    previous_database = os.environ.get("FORGEOPS_DATABASE_URL")
    os.environ["FORGEOPS_DATABASE_URL"] = database_url
    try:
        command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
        result = run_demo(Settings(database_url=database_url, object_store_path=str(object_path)))
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    finally:
        if previous_database is None:
            os.environ.pop("FORGEOPS_DATABASE_URL", None)
        else:
            os.environ["FORGEOPS_DATABASE_URL"] = previous_database
        database_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
