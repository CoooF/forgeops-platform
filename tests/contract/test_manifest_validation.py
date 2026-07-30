from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from forgeops.platform_contracts.errors import ErrorCode
from forgeops.scenario_sdk.manifest import ScenarioManifest
from forgeops.scenario_sdk.validation import ManifestValidator


@pytest.mark.parametrize("package_id", ["steel-cord-scheduling", "equipment-anomaly-diagnosis"])
def test_reference_contract_fixture_is_valid(package_id: str, load_fixture: Any) -> None:
    manifest, artifact = load_fixture(package_id)
    report = ManifestValidator().validate(manifest, artifact)
    assert report.valid, report.issues
    assert report.manifest is not None
    assert report.manifest.solver_adapters == ()


def test_missing_field_is_rejected_with_stable_reason(load_fixture: Any) -> None:
    manifest, artifact = load_fixture("steel-cord-scheduling")
    del manifest["packageId"]
    report = ManifestValidator().validate(manifest, artifact)
    assert report.valid is False
    assert report.issues[0].code == ErrorCode.MANIFEST_MISSING_FIELD
    assert report.issues[0].path == "$.packageId"


def test_unknown_permission_is_rejected(load_fixture: Any) -> None:
    manifest, artifact = load_fixture("steel-cord-scheduling")
    manifest["permissions"].append("proposal.write")
    report = ManifestValidator().validate(manifest, artifact)
    assert {item.code for item in report.issues} == {ErrorCode.UNKNOWN_PERMISSION}


def test_incompatible_sdk_is_rejected(load_fixture: Any) -> None:
    manifest, artifact = load_fixture("steel-cord-scheduling")
    manifest["scenarioSdk"] = ">=2.0.0,<3.0.0"
    report = ManifestValidator().validate(manifest, artifact)
    assert report.issues[0].code == ErrorCode.SDK_INCOMPATIBLE


def test_digest_and_signature_failures_are_distinct(load_fixture: Any) -> None:
    manifest, artifact = load_fixture("steel-cord-scheduling")
    mismatch = ManifestValidator().validate(manifest, b"tampered")
    assert mismatch.issues[0].code == ErrorCode.ARTIFACT_DIGEST_MISMATCH

    manifest["artifact"]["signature"] = "local-sha256:" + "0" * 64
    invalid_signature = ManifestValidator().validate(manifest, artifact)
    assert invalid_signature.issues[0].code == ErrorCode.ARTIFACT_SIGNATURE_INVALID


def test_worker_network_and_secret_requests_are_rejected(load_fixture: Any) -> None:
    manifest, artifact = load_fixture("steel-cord-scheduling")
    manifest["resourceBudget"]["networkAccess"] = True
    manifest["resourceBudget"]["secretRefs"] = ["secret://forbidden"]
    report = ManifestValidator().validate(manifest, artifact)
    assert len(report.issues) == 2
    assert all(item.code == ErrorCode.UNKNOWN_PERMISSION for item in report.issues)


def test_runtime_javascript_is_not_a_declarative_extension(load_fixture: Any) -> None:
    manifest, artifact = load_fixture("steel-cord-scheduling")
    manifest["uiExtensions"][0]["runtimeScript"] = "https://third-party.invalid/plugin.js"
    report = ManifestValidator().validate(manifest, artifact)
    assert report.valid is False
    assert report.issues[0].code == ErrorCode.MANIFEST_INVALID


def test_breaking_schema_upgrade_is_rejected(load_fixture: Any) -> None:
    raw, artifact = load_fixture("steel-cord-scheduling")
    previous = ScenarioManifest.model_validate(deepcopy(raw))
    current = deepcopy(raw)
    current["packageVersion"] = "0.2.0"
    current["domainSchemas"][0]["jsonSchema"]["properties"].pop("items")
    report = ManifestValidator().validate(current, artifact, previous_manifest=previous)
    assert any(item.code == ErrorCode.SCHEMA_BREAKING_CHANGE for item in report.issues)
