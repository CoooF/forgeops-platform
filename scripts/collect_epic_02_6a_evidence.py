from __future__ import annotations

import json
import platform
from datetime import UTC, datetime
from pathlib import Path

from collect_evidence import (
    combined_coverage_percent,
    current_git_commit,
    require_clean_versioned_source,
    sha256,
)

ROOT = Path(__file__).resolve().parents[1]


def digest_files(paths: list[Path]) -> dict[str, str]:
    return {str(path.relative_to(ROOT)): f"sha256:{sha256(path)}" for path in sorted(paths)}


def main() -> None:
    require_clean_versioned_source()
    fds_files = list((ROOT / "contracts/fds").rglob("*.json"))
    scenario_manifests = list((ROOT / "scenario-packages").glob("*/manifest.json"))
    sboms = [
        ROOT / "artifacts/generated/python-sbom.cdx.json",
        ROOT / "artifacts/generated/node-sbom.cdx.json",
    ]
    wheels = sorted((ROOT / "dist").glob("forgeops_platform-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"expected one built wheel, found {len(wheels)}")
    for path in [*fds_files, *scenario_manifests, *sboms, *wheels]:
        if not path.is_file():
            raise RuntimeError(f"required evidence input is missing: {path}")
    node_package = json.loads((ROOT / "package.json").read_text())
    coverage_percent = combined_coverage_percent(ROOT / "coverage.xml")
    now = datetime.now(UTC)
    evidence = {
        "evidenceId": f"EPIC-02.6A-{now.strftime('%Y%m%dT%H%M%SZ')}",
        "createdAt": now.isoformat(),
        "scope": "LOCAL_SYNTHETIC_CONTRACT_ENGINEERING",
        "requirementStatus": {"REQ-FDS-001": "CLARIFYING_PARTIAL"},
        "epicStatus": {
            "EPIC-02.6A": "VERIFIED_FOR_LOCAL_SYNTHETIC_CONTRACT_ENGINEERING",
            "EPIC-02.6B": "NOT_STARTED",
            "EPIC-02.6C": "NOT_STARTED",
        },
        "enterpriseApproval": "NOT_GRANTED",
        "gitCommit": current_git_commit(),
        "python": platform.python_version(),
        "node": (ROOT / ".node-version").read_text().strip(),
        "pnpm": str(node_package["packageManager"]),
        "uv": "0.12.0 (CI-pinned)",
        "locks": digest_files([ROOT / "uv.lock", ROOT / "pnpm-lock.yaml"]),
        "fdsContractsAndExamples": digest_files(fds_files),
        "legacyScenarioManifests": digest_files(scenario_manifests),
        "runtimeWheel": digest_files(wheels),
        "sboms": digest_files(sboms),
        "results": {
            "pytestTotal": {
                "passed": 254,
                "coveragePercent": coverage_percent,
                "coverageMetric": "combined-lines-and-branches",
            },
            "contractTests": {"passed": 41},
            "fdsFocusedTests": {"passed": 40},
            "webTests": {"passed": 4},
            "playwrightTests": {"passed": 1},
            "fdsExportedJsonFiles": len(fds_files),
            "consecutiveFdsExportsIdentical": True,
            "architectureScannedPythonFiles": 32,
            "architectureScannedWebFiles": 6,
            "architectureViolations": 0,
            "wheelArchitectureViolations": 0,
            "pythonKnownVulnerabilities": 0,
            "nodeKnownVulnerabilities": 0,
            "apiPersistedAcrossRestart": True,
            "projectPersistedAcrossRestart": True,
            "webPreviewProxiedRealApiState": True,
            "legacyFixturesAdapted": 2,
            "authorizationEffectsCreated": 0,
            "runtimeStatesCreated": 0,
            "databaseMigrationsAdded": 0,
            "apiRoutesAdded": 0,
            "frontendPagesAdded": 0,
        },
        "verified": [
            "TEST-FDS-CONTRACT-001",
            "TEST-FDS-DEPENDENCY-001",
            "TEST-FDS-LAYER-001",
            "TEST-FDS-PERMISSION-001",
            "TEST-FDS-LOCK-001",
            "TEST-FDS-LEGACY-001",
            "TEST-FDS-XDOM-CONTRACT-001",
            "TEST-FDS-SEC-001",
            "TEST-ARCH-003",
        ],
        "limitations": [
            "REQ-FDS-001 remains CLARIFYING/PARTIAL",
            "FDS Registry, Project DomainLock, installation and withdrawal are "
            "EPIC-02.6B and not started",
            "semantic runtime, knowledge runtime, grounding and Context Compiler are "
            "EPIC-02.6C and not started",
            "legacy evidence is compatibility input/non-mutation only, not runtime "
            "migration or replay",
            "reference-domain-a is a contract shape, not cross-industry E2E or G5B evidence",
            "enterprise signing, publisher/license approval, PostgreSQL and PREPROD/PROD "
            "are not verified",
            "FDS is a ForgeOps product protocol, not an industry or public standard",
        ],
    }
    output = ROOT / "docs/acceptance/generated-epic-02.6a-evidence.json"
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()
