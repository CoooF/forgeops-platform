from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from forgeops.fds_sdk.canonical import canonical_json
from forgeops.platform_core.semantic_runtime.entities import SemanticPayloadDefinition

ROOT = Path(__file__).resolve().parents[3]
FDS_EXAMPLES = ROOT / "contracts" / "fds" / "examples"
SEMANTIC_EXAMPLES = ROOT / "contracts" / "semantic" / "examples"
TARGET_VERSIONS = {"platform": "0.1.0", "fds": "0.1.0", "scenarioSdk": "0.1.0"}
EVALUATION_TIME = "2026-01-15T10:00:00Z"


def read_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text()))


def semantic_fixture(name: str) -> dict[str, Any]:
    return read_json(SEMANTIC_EXAMPLES / name)


def knowledge_fixture(name: str) -> str:
    return (SEMANTIC_EXAMPLES / name).read_text()


def sha256_bytes(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def semantic_content_digest(definition: dict[str, Any]) -> str:
    parsed = SemanticPayloadDefinition.model_validate(definition)
    return sha256_bytes(canonical_json(parsed).encode("utf-8"))


def component_manifest(
    *,
    package_id: str,
    package_version: str,
    component_kind: str,
    content_digest: str,
    capability: str,
) -> dict[str, Any]:
    manifest = deepcopy(read_json(FDS_EXAMPLES / "core-semantics.component.json"))
    suffix = content_digest.removeprefix("sha256:")
    manifest["packageId"] = package_id
    manifest["packageVersion"] = package_version
    manifest["componentKind"] = component_kind
    manifest["contentDigest"] = content_digest
    manifest["artifact"]["contentDigest"] = content_digest
    manifest["artifact"]["signature"] = f"local-sha256:{suffix}"
    manifest["artifact"]["artifactRef"] = (
        f"local://semantic-fixtures/{package_id}/{package_version}"
    )
    manifest["provenance"]["sourceRef"] = (
        f"local://semantic-fixtures/{package_id}/{package_version}"
    )
    manifest["provenance"]["provenanceDigest"] = sha256_bytes(
        f"provenance:{package_id}:{package_version}".encode()
    )
    manifest["providedCapabilities"] = [capability]
    manifest["providedNamespaces"] = [f"{package_id}.namespace"]
    manifest["applicableDomainCapabilities"] = []
    return manifest


def domain_manifest(components: list[dict[str, Any]]) -> dict[str, Any]:
    manifest = deepcopy(read_json(FDS_EXAMPLES / "reference-domain-a.domain.json"))
    manifest["packageId"] = "org.forgeops.synthetic.catalog-domain"
    manifest["domainNamespace"] = "org.forgeops.synthetic.catalog-domain"
    manifest["providedCapabilities"] = ["domain.synthetic-catalog"]
    manifest["providedNamespaces"] = ["org.forgeops.synthetic.catalog-domain"]
    digest = sha256_bytes(
        canonical_json(
            [
                {
                    "packageId": item["packageId"],
                    "packageVersion": item["packageVersion"],
                    "contentDigest": item["contentDigest"],
                }
                for item in components
            ]
        ).encode()
    )
    manifest["contentDigest"] = digest
    manifest["artifact"]["contentDigest"] = digest
    manifest["artifact"]["signature"] = f"local-sha256:{digest.removeprefix('sha256:')}"
    manifest["artifact"]["artifactRef"] = "local://semantic-fixtures/catalog-domain"
    manifest["provenance"]["sourceRef"] = "local://semantic-fixtures/catalog-domain"
    manifest["provenance"]["provenanceDigest"] = sha256_bytes(b"catalog-domain-provenance")
    manifest["components"] = [
        {
            "package": {
                "packageId": item["packageId"],
                "versionConstraint": f"=={item['packageVersion']}",
                "expectedKind": "COMPONENT",
                "expectedCapability": item["providedCapabilities"][0],
                "contentDigest": item["contentDigest"],
            },
            "componentKind": item["componentKind"],
        }
        for item in components
    ]
    manifest["competencyQuestionRefs"] = ["urn:forgeops:synthetic:catalog:cq-1"]
    return manifest


def ontology_v2() -> dict[str, Any]:
    definition = deepcopy(semantic_fixture("neutral-ontology-v1.json"))
    definition["namespaces"][0]["version"] = "2.0.0"
    definition["concepts"][0]["description"] = "领域无关的合成目录项, 第二版本收紧了说明。"
    definition["concepts"] = [
        item
        for item in definition["concepts"]
        if item["semanticId"] != "urn:forgeops:synthetic:catalog:tag"
    ]
    definition["relations"] = [
        item
        for item in definition["relations"]
        if item["semanticId"] != "urn:forgeops:synthetic:catalog:tagged-with"
    ]
    return definition


def headers(
    actor: str = "local-owner", *, key: str | None = None, version: int | None = None
) -> dict[str, str]:
    result = {"X-ForgeOps-Actor": actor, "X-Trace-ID": f"trace-semantic-{actor}"}
    if key is not None:
        result["Idempotency-Key"] = key
    if version is not None:
        result["If-Match"] = str(version)
    return result


def expect(response: Any, status: int) -> dict[str, Any]:
    if response.status_code != status:
        raise AssertionError(f"expected HTTP {status}, got {response.status_code}: {response.text}")
    return cast(dict[str, Any], response.json())


def register_fds(client: TestClient, manifest: dict[str, Any], key: str) -> dict[str, Any]:
    return expect(
        client.post(
            "/v1/fds/package-versions",
            headers=headers(key=key),
            json={"manifest": manifest},
        ),
        201,
    )


def build_scope(client: TestClient, suffix: str = "semantic") -> dict[str, Any]:
    organization = expect(
        client.post(
            "/v1/organizations",
            headers=headers(key=f"{suffix}-organization"),
            json={"name": f"Synthetic {suffix}", "slug": f"synthetic-{suffix}"},
        ),
        201,
    )
    workspace = expect(
        client.post(
            f"/v1/organizations/{organization['organizationId']}/workspaces",
            headers=headers(key=f"{suffix}-workspace"),
            json={"name": f"Synthetic {suffix} workspace", "slug": f"synthetic-{suffix}-ws"},
        ),
        201,
    )
    project = expect(
        client.post(
            f"/v1/workspaces/{workspace['workspaceId']}/projects",
            headers=headers(key=f"{suffix}-project"),
            json={
                "name": f"Synthetic {suffix} project",
                "slug": f"synthetic-{suffix}-project",
                "description": "LOCAL_SYNTHETIC semantic engineering",
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
    return {"organization": organization, "workspace": workspace, "project": project}


def setup_semantic_graph(client: TestClient, suffix: str = "semantic") -> dict[str, Any]:
    scope = build_scope(client, suffix)
    ontology = semantic_fixture("neutral-ontology-v1.json")
    terminology = semantic_fixture("neutral-terminology-v1.json")
    mapping = semantic_fixture("neutral-mapping-v1.json")
    usable_content = knowledge_fixture("neutral-knowledge-usable.txt")
    expired_content = knowledge_fixture("neutral-knowledge-expired.txt")
    purpose_content = knowledge_fixture("neutral-knowledge-purpose.txt")
    withdrawn_content = "Withdrawn local-synthetic reference content.\n"
    definitions = [
        (
            "ontology",
            component_manifest(
                package_id="org.forgeops.synthetic.catalog-ontology",
                package_version="1.0.0",
                component_kind="ONTOLOGY",
                content_digest=semantic_content_digest(ontology),
                capability="semantic.synthetic-ontology",
            ),
            ontology,
        ),
        (
            "terminology",
            component_manifest(
                package_id="org.forgeops.synthetic.catalog-terminology",
                package_version="1.0.0",
                component_kind="TERMINOLOGY",
                content_digest=semantic_content_digest(terminology),
                capability="semantic.synthetic-terminology",
            ),
            terminology,
        ),
        (
            "mapping",
            component_manifest(
                package_id="org.forgeops.synthetic.catalog-mapping",
                package_version="1.0.0",
                component_kind="DATA_MAPPING",
                content_digest=semantic_content_digest(mapping),
                capability="semantic.synthetic-mapping",
            ),
            mapping,
        ),
    ]
    knowledge_inputs = [
        ("usable", "org.forgeops.synthetic.knowledge-usable", usable_content),
        ("expired", "org.forgeops.synthetic.knowledge-expired", expired_content),
        ("purpose", "org.forgeops.synthetic.knowledge-purpose", purpose_content),
        ("withdrawn", "org.forgeops.synthetic.knowledge-withdrawn", withdrawn_content),
    ]
    component_manifests = [item[1] for item in definitions]
    for name, package_id, content in knowledge_inputs:
        component_manifests.append(
            component_manifest(
                package_id=package_id,
                package_version="1.0.0",
                component_kind="KNOWLEDGE",
                content_digest=sha256_bytes(content.encode()),
                capability=f"knowledge.synthetic-{name}",
            )
        )
    registered_components = {
        item["packageId"]: register_fds(
            client, item, f"{suffix}-fds-{item['packageId']}-{item['packageVersion']}"
        )
        for item in component_manifests
    }
    domain = register_fds(client, domain_manifest(component_manifests), f"{suffix}-fds-domain")
    installation = expect(
        client.post(
            f"/v1/organizations/{scope['organization']['organizationId']}/domain-installations",
            headers=headers(key=f"{suffix}-installation"),
            json={
                "rootPackageVersionId": domain["packageVersionId"],
                "targetVersions": TARGET_VERSIONS,
                "includeOptional": False,
            },
        ),
        201,
    )
    domain_lock = expect(
        client.post(
            f"/v1/projects/{scope['project']['projectId']}/domain-locks",
            headers=headers(key=f"{suffix}-domain-lock"),
            json={
                "installationId": installation["installationId"],
                "purpose": "LOCAL_SYNTHETIC deterministic context",
            },
        ),
        201,
    )
    semantic_payloads: dict[str, dict[str, Any]] = {}
    for name, manifest, definition in definitions:
        package = registered_components[manifest["packageId"]]
        payload = expect(
            client.post(
                "/v1/semantic/payloads",
                headers=headers(key=f"{suffix}-payload-{name}"),
                json={
                    "packageVersionId": package["packageVersionId"],
                    "definition": definition,
                },
            ),
            201,
        )
        semantic_payloads[name] = expect(
            client.post(
                f"/v1/semantic/payloads/{payload['semanticPayloadId']}:publish",
                headers=headers(key=f"{suffix}-publish-{name}", version=payload["version"]),
                json={"reason": "owner-approved local synthetic fixture"},
            ),
            200,
        )
    knowledge_versions: dict[str, dict[str, Any]] = {}
    usable_asset_id: str | None = None
    for name, package_id, content in knowledge_inputs:
        asset = expect(
            client.post(
                f"/v1/organizations/{scope['organization']['organizationId']}/knowledge-assets",
                headers=headers(key=f"{suffix}-asset-{name}"),
                json={
                    "title": f"Synthetic {name} reference",
                    "description": f"Domain-neutral {name} knowledge fixture",
                    "assetType": "TEXT",
                    "language": "en",
                    "owner": "local-owner",
                    "reviewer": "local-reviewer",
                },
            ),
            201,
        )
        if name == "usable":
            usable_asset_id = asset["assetId"]
        package_manifest = next(
            item for item in component_manifests if item["packageId"] == package_id
        )
        package = registered_components[package_id]
        valid_to = "2025-06-01T00:00:00Z" if name == "expired" else None
        purposes = ["OTHER_PURPOSE"] if name == "purpose" else ["OWNER_REVIEW"]
        version = expect(
            client.post(
                f"/v1/knowledge-assets/{asset['assetId']}/versions",
                headers=headers(key=f"{suffix}-knowledge-version-{name}"),
                json={
                    "packageVersionId": package["packageVersionId"],
                    "versionLabel": "1.0.0",
                    "title": f"Synthetic {name} reference v1",
                    "description": f"Immutable {name} local-synthetic content",
                    "sourceRef": package_manifest["provenance"]["sourceRef"],
                    "provenanceDigest": package_manifest["provenance"]["provenanceDigest"],
                    "licenseId": "LOCAL-SYNTHETIC-ONLY",
                    "licenseTerms": "Local synthetic engineering only; no redistribution.",
                    "contentClassification": "SYNTHETIC_INTERNAL",
                    "allowedPurposes": purposes,
                    "validFrom": "2025-01-01T00:00:00Z",
                    "validTo": valid_to,
                    "contentType": "text/plain",
                    "content": content,
                },
            ),
            201,
        )
        published = expect(
            client.post(
                f"/v1/knowledge-versions/{version['knowledgeVersionId']}:publish",
                headers=headers(
                    key=f"{suffix}-publish-knowledge-{name}", version=version["version"]
                ),
                json={"reason": "owner-approved local synthetic fixture"},
            ),
            200,
        )
        if name == "withdrawn":
            published = expect(
                client.post(
                    f"/v1/knowledge-versions/{version['knowledgeVersionId']}:withdraw",
                    headers=headers(
                        key=f"{suffix}-withdraw-knowledge-{name}",
                        version=published["version"],
                    ),
                    json={"reason": "synthetic withdrawal rejection fixture"},
                ),
                200,
            )
        knowledge_versions[name] = published
    assert usable_asset_id is not None
    return {
        **scope,
        "components": registered_components,
        "componentManifests": component_manifests,
        "domain": domain,
        "installation": installation,
        "domainLock": domain_lock,
        "semanticPayloads": semantic_payloads,
        "knowledgeVersions": knowledge_versions,
        "usableAssetId": usable_asset_id,
    }


def context_request(
    state: dict[str, Any], *, max_items: int = 30, max_chars: int = 20_000
) -> dict[str, Any]:
    return {
        "purpose": "OWNER_REVIEW",
        "requestedTerms": ["目录项"],
        "semanticIds": [
            "urn:forgeops:synthetic:catalog:collection",
            "urn:forgeops:synthetic:catalog:contains",
        ],
        "mappingIds": ["catalog.mapping.item-primary"],
        "knowledgeVersionIds": [
            item["knowledgeVersionId"] for item in state["knowledgeVersions"].values()
        ],
        "budget": {"maxItems": max_items, "maxChars": max_chars},
        "locale": "zh-CN",
        "evaluationTime": EVALUATION_TIME,
    }
