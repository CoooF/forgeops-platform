from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from forgeops.fds_sdk.canonical import canonical_json
from forgeops.fds_sdk.legacy import LEGACY_LIMITATIONS, LegacyScenarioAdapter
from forgeops.fds_sdk.models import CompatibilityStatus
from forgeops.platform_contracts.errors import ErrorCode

ROOT = Path(__file__).resolve().parents[2]


def load_legacy(package_id: str) -> tuple[dict[str, object], bytes]:
    package_root = ROOT / "scenario-packages" / package_id
    return (
        json.loads((package_root / "manifest.json").read_text()),
        (package_root / "artifact.json").read_bytes(),
    )


@pytest.mark.parametrize("package_id", ["steel-cord-scheduling", "equipment-anomaly-diagnosis"])
def test_legacy_fixture_adapts_without_mutation_or_fabricated_facts(package_id: str) -> None:
    raw, artifact = load_legacy(package_id)
    before = deepcopy(raw)
    first = LegacyScenarioAdapter().adapt(raw, artifact)
    second = LegacyScenarioAdapter().adapt(deepcopy(raw), artifact)

    assert raw == before
    assert first == second
    assert first.report.status == CompatibilityStatus.COMPATIBLE_WITH_LIMITATIONS
    assert first.report.resolver_ready is False
    assert first.report.history_mutated is False
    assert first.report.limitations == LEGACY_LIMITATIONS
    assert first.descriptor is not None
    assert first.descriptor.package_id == raw["packageId"]
    assert first.descriptor.package_version == raw["packageVersion"]
    assert first.descriptor.content_digest == raw["artifact"]["contentDigest"]  # type: ignore[index]
    assert list(first.descriptor.permissions) == raw["permissions"]
    assert first.descriptor.required_domain_capabilities == ()
    assert first.descriptor.input_contract_digest is None
    assert first.descriptor.license.verified is False
    assert first.descriptor.legacy_source is not None
    assert len(first.descriptor.legacy_source.references) > 0
    assert canonical_json(first.report) == canonical_json(second.report)


def test_invalid_legacy_manifest_returns_report_without_partial_descriptor() -> None:
    raw, artifact = load_legacy("steel-cord-scheduling")
    raw["permissions"] = [*raw["permissions"], "external-system.write"]  # type: ignore[misc]
    result = LegacyScenarioAdapter().adapt(raw, artifact)
    assert result.descriptor is None
    assert result.report.status == CompatibilityStatus.INCOMPATIBLE
    assert result.report.issues[0].code == ErrorCode.UNKNOWN_PERMISSION
    assert result.report.report_digest.startswith("sha256:")
