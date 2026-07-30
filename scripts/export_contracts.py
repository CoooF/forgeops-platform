from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from forgeops.api import create_app
from forgeops.fds_sdk.legacy import LegacyScenarioAdapter
from forgeops.fds_sdk.models import (
    FDS_MANIFEST_ADAPTER,
    CompatibilityReport,
    ComponentManifest,
    DependencyLock,
    DomainManifest,
    OrganizationOverlayManifest,
    PackageRef,
    ScenarioDescriptor,
    TargetVersions,
)
from forgeops.fds_sdk.resolver import DependencyResolver
from forgeops.fds_sdk.validation import FdsManifestValidator
from forgeops.scenario_sdk.manifest import ScenarioManifest

ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, payload: Any) -> None:
    if isinstance(payload, BaseModel):
        payload = payload.model_dump(by_alias=True, mode="json", exclude_none=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def export_fds_contracts() -> None:
    schema_models: dict[str, type[BaseModel]] = {
        "domain-manifest.schema.json": DomainManifest,
        "organization-overlay-manifest.schema.json": OrganizationOverlayManifest,
        "scenario-descriptor.schema.json": ScenarioDescriptor,
        "component-manifest.schema.json": ComponentManifest,
        "dependency-lock.schema.json": DependencyLock,
        "compatibility-report.schema.json": CompatibilityReport,
    }
    for filename, model in schema_models.items():
        write_json(ROOT / "contracts/fds" / filename, model.model_json_schema(by_alias=True))
    write_json(
        ROOT / "contracts/fds/fds-manifest.schema.json",
        FDS_MANIFEST_ADAPTER.json_schema(by_alias=True),
    )

    example_root = ROOT / "contracts/fds/examples"
    candidates = []
    manifest_paths = sorted(
        path
        for suffix in ("*.domain.json", "*.overlay.json", "*.scenario.json", "*.component.json")
        for path in example_root.glob(suffix)
    )
    for path in manifest_paths:
        report = FdsManifestValidator().validate(json.loads(path.read_text()))
        if not report.valid or report.manifest is None:
            raise RuntimeError(f"invalid FDS export fixture {path}: {report.issues}")
        candidates.append(report.manifest)
    resolution = DependencyResolver().resolve(
        PackageRef(
            package_id="org.forgeops.scenario.contract-shape",
            version_constraint="==0.1.0",
        ),
        candidates,
        TargetVersions(platform="0.1.0", fds="0.1.0", scenario_sdk="0.1.0"),
    )
    if not resolution.valid or resolution.lock is None:
        raise RuntimeError(f"FDS example graph did not resolve: {resolution.issues}")
    write_json(example_root / "dependency-lock.example.json", resolution.lock)

    for package_id in ("steel-cord-scheduling", "equipment-anomaly-diagnosis"):
        package_root = ROOT / "scenario-packages" / package_id
        result = LegacyScenarioAdapter().adapt(
            json.loads((package_root / "manifest.json").read_text()),
            (package_root / "artifact.json").read_bytes(),
        )
        write_json(example_root / f"{package_id}.compatibility-report.example.json", result.report)


def main() -> None:
    write_json(ROOT / "contracts/openapi/forgeops.openapi.json", create_app().openapi())
    write_json(
        ROOT / "contracts/jsonschema/scenario-manifest.schema.json",
        ScenarioManifest.model_json_schema(by_alias=True),
    )
    export_fds_contracts()


if __name__ == "__main__":
    main()
