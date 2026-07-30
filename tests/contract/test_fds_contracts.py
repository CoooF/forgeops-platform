from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from forgeops.fds_sdk.models import (
    ComponentManifest,
    DomainManifest,
    OrganizationOverlayManifest,
    ScenarioDescriptor,
)
from forgeops.fds_sdk.validation import FdsManifestValidator
from forgeops.platform_contracts.errors import ErrorCode

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "contracts/fds/examples"


def load(name: str) -> dict[str, Any]:
    return json.loads((EXAMPLES / name).read_text())


@pytest.mark.parametrize(
    ("name", "model_type"),
    [
        ("manufacturing-shape.domain.json", DomainManifest),
        ("synthetic-organization.overlay.json", OrganizationOverlayManifest),
        ("contract-shape.scenario.json", ScenarioDescriptor),
        ("core-semantics.component.json", ComponentManifest),
        ("reference-domain-a.domain.json", DomainManifest),
    ],
)
def test_fds_example_has_a_strict_normalized_contract(name: str, model_type: type[Any]) -> None:
    report = FdsManifestValidator().validate(load(name))
    assert report.valid, report.issues
    assert isinstance(report.manifest, model_type)
    assert report.normalized_manifest is not None
    assert report.manifest_digest is not None
    assert json.loads(report.normalized_manifest)["packageId"] == report.manifest.package_id


@pytest.mark.parametrize(
    "model_type",
    [DomainManifest, OrganizationOverlayManifest, ScenarioDescriptor, ComponentManifest],
)
def test_each_manifest_schema_forbids_unknown_fields(model_type: type[Any]) -> None:
    schema = model_type.model_json_schema(by_alias=True)
    assert schema["additionalProperties"] is False
    assert schema["properties"]["apiVersion"]["const"] == "forgeops.ai/fds/v1alpha1"


def test_unknown_field_and_missing_field_are_stable() -> None:
    raw = load("manufacturing-shape.domain.json")
    raw["apiKey"] = "must-not-enter-contracts"
    raw.pop("license")
    report = FdsManifestValidator().validate(raw)
    assert [(issue.code, issue.path) for issue in report.issues] == [
        (ErrorCode.MANIFEST_INVALID, "$.apiKey"),
        (ErrorCode.MANIFEST_MISSING_FIELD, "$.license"),
    ]
    assert report.manifest is None


@pytest.mark.parametrize(
    ("field", "value", "expected_code"),
    [
        ("kind", "REGISTRY", ErrorCode.UNKNOWN_PACKAGE_KIND),
        ("componentKind", "MODEL_MEMORY", ErrorCode.UNKNOWN_COMPONENT_KIND),
    ],
)
def test_unknown_package_and_component_kinds_fail_closed(
    field: str, value: str, expected_code: ErrorCode
) -> None:
    raw = load("core-semantics.component.json")
    raw[field] = value
    report = FdsManifestValidator().validate(raw)
    assert report.issues[0].code == expected_code
    assert report.manifest is None


@pytest.mark.parametrize(
    ("mutate", "expected_code"),
    [
        (
            lambda raw: raw["permissions"].append("secret.read"),
            ErrorCode.UNKNOWN_PERMISSION,
        ),
        (
            lambda raw: raw.update(
                contentDigest="sha256:" + "9" * 64,
            ),
            ErrorCode.ARTIFACT_DIGEST_MISMATCH,
        ),
        (
            lambda raw: raw["artifact"].update(signature="local-sha256:" + "9" * 64),
            ErrorCode.ARTIFACT_SIGNATURE_INVALID,
        ),
        (
            lambda raw: raw["compatibility"].update(platform="not-a-range"),
            ErrorCode.MANIFEST_INVALID,
        ),
    ],
)
def test_permissions_digest_attestation_and_version_constraints_are_strict(
    mutate: Any, expected_code: ErrorCode
) -> None:
    raw = load("core-semantics.component.json")
    mutate(raw)
    report = FdsManifestValidator().validate(raw)
    assert expected_code in {issue.code for issue in report.issues}
    assert report.manifest is None


def test_executable_component_requires_both_isolated_boundaries() -> None:
    raw = load("core-semantics.component.json")
    raw["artifact"]["executable"] = True
    report = FdsManifestValidator().validate(raw)
    assert [issue.code for issue in report.issues] == [
        ErrorCode.EXECUTABLE_BOUNDARY_REQUIRED,
        ErrorCode.EXECUTABLE_BOUNDARY_REQUIRED,
    ]


def test_private_publication_and_overlay_defaults_are_enforced() -> None:
    domain = load("manufacturing-shape.domain.json")
    domain["contentClassification"] = "ORGANIZATION_PRIVATE"
    assert FdsManifestValidator().validate(domain).issues[0].code == (
        ErrorCode.PRIVATE_CONTENT_PUBLICATION_DENIED
    )

    overlay = load("synthetic-organization.overlay.json")
    overlay["visibility"] = "PUBLIC"
    overlay["overridesDomainCapabilities"] = []
    codes = {issue.code for issue in FdsManifestValidator().validate(overlay).issues}
    assert codes == {ErrorCode.OVERLAY_TARGET_MISSING, ErrorCode.VISIBILITY_VIOLATION}


def test_native_domain_and_scenario_minimums_are_not_optional() -> None:
    domain = load("reference-domain-a.domain.json")
    domain["competencyQuestionRefs"] = []
    assert FdsManifestValidator().validate(domain).issues[0].code == ErrorCode.MANIFEST_INVALID

    scenario = load("contract-shape.scenario.json")
    scenario["requiredDomainCapabilities"] = []
    scenario["inputContractDigest"] = None
    codes = {issue.code for issue in FdsManifestValidator().validate(scenario).issues}
    assert codes == {
        ErrorCode.MANIFEST_INVALID,
        ErrorCode.SCENARIO_DOMAIN_CAPABILITY_MISSING,
    }


def test_normalization_ignores_contract_set_order() -> None:
    first = load("contract-shape.scenario.json")
    second = deepcopy(first)
    second["dependencies"].reverse()
    second["prohibitedUses"].reverse()
    first_report = FdsManifestValidator().validate(first)
    second_report = FdsManifestValidator().validate(second)
    assert first_report.normalized_manifest == second_report.normalized_manifest
    assert first_report.manifest_digest == second_report.manifest_digest


def test_negative_fixture_catalog_uses_stable_error_codes() -> None:
    catalog = load("negative-cases.json")
    assert catalog["classification"] == "SYNTHETIC_CONTRACT_ONLY"
    assert catalog["containsBusinessKnowledge"] is False
    assert catalog["containsRealData"] is False
    codes = {ErrorCode(case["expectedCode"]) for case in catalog["cases"]}
    assert {
        ErrorCode.DEPENDENCY_MISSING,
        ErrorCode.DEPENDENCY_CYCLE,
        ErrorCode.DEPENDENCY_CONFLICT,
        ErrorCode.PERMISSION_EXPANSION,
        ErrorCode.LOCK_DIGEST_MISMATCH,
    }.issubset(codes)
