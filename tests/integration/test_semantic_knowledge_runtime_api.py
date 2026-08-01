from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pydantic import ValidationError

from forgeops.api import create_app
from forgeops.config import Settings
from forgeops.fds_sdk.canonical import canonical_json
from forgeops.platform_core.semantic_runtime.entities import SemanticPayloadDefinition
from forgeops.testing.epic_02_6c_support import (
    EVALUATION_TIME,
    build_scope,
    component_manifest,
    context_request,
    expect,
    headers,
    knowledge_fixture,
    ontology_v2,
    register_fds,
    semantic_content_digest,
    semantic_fixture,
    setup_semantic_graph,
    sha256_bytes,
)


@pytest.fixture
def semantic_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'semantic.db'}"
    object_store = tmp_path / "objects"
    monkeypatch.setenv("FORGEOPS_DATABASE_URL", database_url)
    monkeypatch.setenv("FORGEOPS_OBJECT_STORE_PATH", str(object_store))
    command.upgrade(Config("alembic.ini"), "head")
    with TestClient(
        create_app(Settings(database_url=database_url, object_store_path=str(object_store)))
    ) as client:
        yield client


def test_semantic_contract_is_strict_and_canonical() -> None:
    # TEST-SEM-CONTRACT-001
    definition = semantic_fixture("neutral-ontology-v1.json")
    parsed = SemanticPayloadDefinition.model_validate(definition)
    assert canonical_json(parsed) == canonical_json(
        SemanticPayloadDefinition.model_validate(dict(reversed(list(definition.items()))))
    )
    invalid = {**definition, "unknownRuntime": True}
    with pytest.raises(ValidationError):
        SemanticPayloadDefinition.model_validate(invalid)
    invalid_namespace = {**definition}
    invalid_namespace["namespaces"] = [
        {**definition["namespaces"][0], "canonicalUri": "file:///tmp/semantic.json"}
    ]
    with pytest.raises(ValidationError):
        SemanticPayloadDefinition.model_validate(invalid_namespace)


def test_query_context_grounding_impact_and_persistence(
    semantic_client: TestClient,
) -> None:
    # TEST-SEM-REGISTRY-001 / TEST-SEM-QUERY-001 / TEST-SEM-MAPPING-001
    # TEST-SEM-AMBIGUITY-001 / TEST-KNW-LIFECYCLE-001
    # TEST-CONTEXT-COMPILER-001 / TEST-GROUNDING-001 / TEST-SEM-IMPACT-001
    # TEST-SEM-PERSISTENCE-001 / TEST-SEM-API-001
    state = setup_semantic_graph(semantic_client, "runtime")
    project_id = state["project"]["projectId"]
    unique = expect(
        semantic_client.post(
            f"/v1/projects/{project_id}/semantic-query",
            headers=headers(),
            json={
                "queryType": "TERM",
                "value": "　目录项　",
                "evaluationTime": EVALUATION_TIME,
            },
        ),
        200,
    )
    assert unique["status"] == "RESOLVED"
    assert unique["canonicalRefs"][0]["semanticId"] == ("urn:forgeops:synthetic:catalog:item")
    assert unique["canonicalRefs"][0]["payloadDigest"].startswith("sha256:")
    ambiguous = expect(
        semantic_client.post(
            f"/v1/projects/{project_id}/semantic-query",
            headers=headers(),
            json={
                "queryType": "TERM",
                "value": "共享词",
                "evaluationTime": EVALUATION_TIME,
            },
        ),
        200,
    )
    assert ambiguous["status"] == "AMBIGUOUS"
    assert len(ambiguous["candidates"]) == 2
    assert ambiguous["canonicalRefs"] == []
    unknown = expect(
        semantic_client.post(
            f"/v1/projects/{project_id}/semantic-query",
            headers=headers(),
            json={
                "queryType": "TERM",
                "value": "完全未知词",
                "evaluationTime": EVALUATION_TIME,
            },
        ),
        200,
    )
    assert unknown["status"] == "UNKNOWN"
    assert unknown["canonicalRefs"] == []
    mapping = expect(
        semantic_client.post(
            f"/v1/projects/{project_id}/semantic-query",
            headers=headers(),
            json={
                "queryType": "SOURCE_MAPPING",
                "source": {
                    "sourceSystem": "synthetic.catalog",
                    "refType": "record",
                    "objectRef": "entry",
                    "fieldRef": "kind",
                    "code": "SHARED",
                },
                "evaluationTime": EVALUATION_TIME,
            },
        ),
        200,
    )
    assert mapping["status"] == "AMBIGUOUS"
    assert {item["value"]["unit"] for item in mapping["candidates"]} == {"synthetic-count"}
    for query_type, value, expected_type in (
        ("SEMANTIC_ID", "urn:forgeops:synthetic:catalog:item", "CONCEPT"),
        ("RELATION", "urn:forgeops:synthetic:catalog:contains", "RELATION"),
        ("CONSTRAINT", "catalog.contains.required", "CONSTRAINT"),
    ):
        result = expect(
            semantic_client.post(
                f"/v1/projects/{project_id}/semantic-query",
                headers=headers(),
                json={
                    "queryType": query_type,
                    "value": value,
                    "evaluationTime": EVALUATION_TIME,
                },
            ),
            200,
        )
        assert result["status"] == "RESOLVED"
        assert result["canonicalRefs"][0]["refType"] == expected_type

    request_body = context_request(state)
    compiled = expect(
        semantic_client.post(
            f"/v1/projects/{project_id}/context-manifests",
            headers=headers(key="context-first"),
            json=request_body,
        ),
        201,
    )
    repeated = expect(
        semantic_client.post(
            f"/v1/projects/{project_id}/context-manifests",
            headers=headers(key="context-repeat"),
            json=request_body,
        ),
        201,
    )
    assert repeated["contextManifestId"] == compiled["contextManifestId"]
    assert repeated["canonicalDigest"] == compiled["canonicalDigest"]
    assert len(compiled["includedKnowledgeRefs"]) == 1
    assert (
        compiled["includedKnowledgeRefs"][0]["knowledgeVersionId"]
        == (state["knowledgeVersions"]["usable"]["knowledgeVersionId"])
    )
    assert {item["reason"] for item in compiled["excludedRefs"]} >= {
        "KNOWLEDGE_NOT_EFFECTIVE",
        "PURPOSE_NOT_ALLOWED",
        "KNOWLEDGE_NOT_PUBLISHED",
    }
    fetched = expect(
        semantic_client.get(
            f"/v1/context-manifests/{compiled['contextManifestId']}", headers=headers()
        ),
        200,
    )
    assert fetched["canonicalDigest"] == compiled["canonicalDigest"]
    tiny = expect(
        semantic_client.post(
            f"/v1/projects/{project_id}/context-manifests",
            headers=headers(key="context-tiny"),
            json=context_request(state, max_items=1, max_chars=300),
        ),
        201,
    )
    assert tiny["truncated"] is True
    assert tiny["budgetUsage"]["items"] <= 1

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
        semantic_client.post(
            f"/v1/context-manifests/{compiled['contextManifestId']}/grounding-validations",
            headers=headers(key="grounding-valid"),
            json=valid_candidate,
        ),
        201,
    )
    assert valid["status"] == "VALID"
    invalid_candidate = {
        **valid_candidate,
        "relationAssertions": [
            {
                "relationSemanticId": "urn:forgeops:synthetic:catalog:contains",
                "sourceSemanticId": "urn:forgeops:synthetic:catalog:item",
                "targetSemanticId": "urn:forgeops:synthetic:catalog:collection",
            }
        ],
        "knowledgeCitations": ["00000000-0000-0000-0000-000000000001"],
    }
    invalid = expect(
        semantic_client.post(
            f"/v1/context-manifests/{compiled['contextManifestId']}/grounding-validations",
            headers=headers(key="grounding-invalid"),
            json=invalid_candidate,
        ),
        201,
    )
    assert invalid["status"] == "INVALID"
    assert "OUT_OF_CONTEXT_MANIFEST" in invalid["issues"]
    assert invalid["constraintViolations"]

    ambiguous_context = expect(
        semantic_client.post(
            f"/v1/projects/{project_id}/context-manifests",
            headers=headers(key="context-ambiguous"),
            json={
                **context_request(state),
                "requestedTerms": ["共享词"],
                "knowledgeVersionIds": [],
            },
        ),
        201,
    )
    needs_clarification = expect(
        semantic_client.post(
            f"/v1/context-manifests/{ambiguous_context['contextManifestId']}/grounding-validations",
            headers=headers(key="grounding-needs-clarification"),
            json={
                "entityRefs": [],
                "relationAssertions": [],
                "mappingRefs": [],
                "knowledgeCitations": [],
                "declaredConstraintIds": [],
            },
        ),
        201,
    )
    assert needs_clarification["status"] == "NEEDS_CLARIFICATION"

    ontology_definition_v2 = ontology_v2()
    ontology_manifest_v2 = component_manifest(
        package_id="org.forgeops.synthetic.catalog-ontology",
        package_version="2.0.0",
        component_kind="ONTOLOGY",
        content_digest=semantic_content_digest(ontology_definition_v2),
        capability="semantic.synthetic-ontology",
    )
    ontology_package_v2 = register_fds(semantic_client, ontology_manifest_v2, "runtime-ontology-v2")
    ontology_payload_v2 = expect(
        semantic_client.post(
            "/v1/semantic/payloads",
            headers=headers(key="runtime-payload-ontology-v2"),
            json={
                "packageVersionId": ontology_package_v2["packageVersionId"],
                "definition": ontology_definition_v2,
            },
        ),
        201,
    )
    ontology_payload_v2 = expect(
        semantic_client.post(
            f"/v1/semantic/payloads/{ontology_payload_v2['semanticPayloadId']}:publish",
            headers=headers(key="runtime-publish-ontology-v2", version=1),
            json={"reason": "synthetic v2 impact fixture"},
        ),
        200,
    )
    semantic_impact = expect(
        semantic_client.post(
            "/v1/semantic-impacts",
            headers=headers(key="runtime-semantic-impact"),
            json={
                "resourceType": "SEMANTIC",
                "fromId": state["semanticPayloads"]["ontology"]["semanticPayloadId"],
                "toId": ontology_payload_v2["semanticPayloadId"],
            },
        ),
        201,
    )
    assert semantic_impact["severity"] == "BREAKING"
    assert "urn:forgeops:synthetic:catalog:tag" in semantic_impact["changes"]["removed"]
    assert semantic_impact["affectedProjectDomainLocks"] == [
        state["domainLock"]["projectDomainLockId"]
    ]
    assert semantic_impact["workflowImpact"] == "NOT_EVALUATED"

    terminology = state["semanticPayloads"]["terminology"]
    withdrawn = expect(
        semantic_client.post(
            f"/v1/semantic/payloads/{terminology['semanticPayloadId']}:withdraw",
            headers=headers(key="runtime-withdraw-terminology", version=2),
            json={"reason": "prove withdrawn semantic payload is excluded"},
        ),
        200,
    )
    assert withdrawn["status"] == "WITHDRAWN"
    query_after_withdrawal = expect(
        semantic_client.post(
            f"/v1/projects/{project_id}/semantic-query",
            headers=headers(),
            json={
                "queryType": "TERM",
                "value": "目录项",
                "evaluationTime": EVALUATION_TIME,
            },
        ),
        200,
    )
    assert query_after_withdrawal["status"] == "UNKNOWN"
    assert query_after_withdrawal["canonicalRefs"] == []


def test_security_authorization_idempotency_and_concurrency(
    semantic_client: TestClient,
) -> None:
    # TEST-KNW-SEC-001 / TEST-SEM-AUTH-001 / TEST-SEM-API-001 / TEST-ARCH-005
    state = setup_semantic_graph(semantic_client, "security")
    project_id = state["project"]["projectId"]
    organization_id = state["organization"]["organizationId"]
    grant = semantic_client.post(
        f"/v1/organizations/{organization_id}/memberships",
        headers=headers(key="security-viewer-grant"),
        json={
            "principalRef": "local-viewer",
            "scopeType": "PROJECT",
            "scopeId": project_id,
            "role": "PROJECT_VIEWER",
        },
    )
    assert grant.status_code == 201, grant.text
    viewer_query = semantic_client.post(
        f"/v1/projects/{project_id}/semantic-query",
        headers=headers("local-viewer"),
        json={
            "queryType": "TERM",
            "value": "目录项",
            "evaluationTime": EVALUATION_TIME,
        },
    )
    assert viewer_query.status_code == 200
    viewer_manage = semantic_client.post(
        "/v1/semantic/payloads",
        headers=headers("local-viewer", key="viewer-denied-write"),
        json={
            "packageVersionId": state["components"]["org.forgeops.synthetic.catalog-ontology"][
                "packageVersionId"
            ],
            "definition": semantic_fixture("neutral-ontology-v1.json"),
        },
    )
    assert viewer_manage.status_code in {403, 404}
    outsider = semantic_client.get(
        f"/v1/projects/{project_id}/semantic-components",
        headers=headers("local-outsider"),
    )
    assert outsider.status_code == 404
    assert project_id not in outsider.text
    strict = semantic_client.post(
        f"/v1/projects/{project_id}/semantic-query",
        headers=headers(),
        json={
            "queryType": "TERM",
            "value": "目录项",
            "evaluationTime": EVALUATION_TIME,
            "sql": "select *",
        },
    )
    assert strict.status_code == 422
    ontology = state["semanticPayloads"]["ontology"]
    stale = semantic_client.post(
        f"/v1/semantic/payloads/{ontology['semanticPayloadId']}:withdraw",
        headers=headers(key="stale-withdraw", version=1),
        json={"reason": "must fail stale If-Match"},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "CONCURRENCY_CONFLICT"
    injection_version = state["knowledgeVersions"]["purpose"]
    content = expect(
        semantic_client.get(
            f"/v1/knowledge-versions/{injection_version['knowledgeVersionId']}/content",
            headers=headers(),
        ),
        200,
    )
    assert "call a tool" in content["content"]
    assert content["untrustedData"] is True
    assert content["executed"] is False
    status = expect(semantic_client.get("/v1/platform/status", headers=headers()), 200)
    assert status["semanticRuntimeEnabled"] is True
    assert status["agentRuntimeEnabled"] is False
    assert status["llmEnabled"] is False
    assert status["ragEnabled"] is False
    other = build_scope(semantic_client, "security-other")
    grant_other = semantic_client.post(
        f"/v1/organizations/{other['organization']['organizationId']}/memberships",
        headers=headers(key="security-other-owner"),
        json={
            "principalRef": "local-editor",
            "scopeType": "ORGANIZATION",
            "scopeId": other["organization"]["organizationId"],
            "role": "ORG_OWNER",
        },
    )
    assert grant_other.status_code == 201, grant_other.text
    cross_organization = semantic_client.get(
        f"/v1/knowledge-versions/{injection_version['knowledgeVersionId']}",
        headers=headers("local-editor"),
    )
    assert cross_organization.status_code == 404
    assert injection_version["knowledgeVersionId"] not in cross_organization.text
    audit = semantic_client.get(
        f"/v1/projects/{project_id}/audit-events?limit=100", headers=headers()
    )
    assert audit.status_code == 200
    assert "call a tool" not in audit.text


def test_knowledge_v1_v2_impact(semantic_client: TestClient) -> None:
    # TEST-KNW-LIFECYCLE-001 / TEST-SEM-IMPACT-001
    state = setup_semantic_graph(semantic_client, "knowledge-impact")
    content_v2 = knowledge_fixture("neutral-knowledge-usable.txt") + ("Second immutable version.\n")
    manifest_v2 = component_manifest(
        package_id="org.forgeops.synthetic.knowledge-usable",
        package_version="2.0.0",
        component_kind="KNOWLEDGE",
        content_digest=sha256_bytes(content_v2.encode()),
        capability="knowledge.synthetic-usable",
    )
    package_v2 = register_fds(semantic_client, manifest_v2, "knowledge-impact-fds-v2")
    version_v2 = expect(
        semantic_client.post(
            f"/v1/knowledge-assets/{state['usableAssetId']}/versions",
            headers=headers(key="knowledge-impact-version-v2"),
            json={
                "packageVersionId": package_v2["packageVersionId"],
                "versionLabel": "2.0.0",
                "title": "Synthetic usable reference v2",
                "description": "Second immutable local-synthetic version",
                "sourceRef": manifest_v2["provenance"]["sourceRef"],
                "provenanceDigest": manifest_v2["provenance"]["provenanceDigest"],
                "licenseId": "LOCAL-SYNTHETIC-ONLY",
                "licenseTerms": "Local synthetic engineering only; no redistribution.",
                "contentClassification": "SYNTHETIC_INTERNAL",
                "allowedPurposes": ["OWNER_REVIEW"],
                "validFrom": "2025-01-01T00:00:00Z",
                "validTo": None,
                "contentType": "text/plain",
                "content": content_v2,
            },
        ),
        201,
    )
    impact = expect(
        semantic_client.post(
            "/v1/semantic-impacts",
            headers=headers(key="knowledge-impact-report"),
            json={
                "resourceType": "KNOWLEDGE",
                "fromId": state["knowledgeVersions"]["usable"]["knowledgeVersionId"],
                "toId": version_v2["knowledgeVersionId"],
            },
        ),
        201,
    )
    assert impact["changes"]["contentDigestChanged"] is True
    assert impact["severity"] == "POTENTIALLY_BREAKING"
    assert impact["workflowImpact"] == "NOT_EVALUATED"
