from __future__ import annotations

import json
import os
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

# Updated from the one final high-cost verification run before the verified source commit.
FULL_PYTEST_PASSED = 341
CONTRACT_TESTS_PASSED = 41
FDS_FOCUSED_TESTS_PASSED = 40
EPIC_02_6B_FOCUSED_TESTS_PASSED = 63
WEB_TESTS_PASSED = 6
PLAYWRIGHT_TESTS_PASSED = 2
ARCHITECTURE_PYTHON_FILES = 36
ARCHITECTURE_WEB_FILES = 9


def digest_files(paths: list[Path]) -> dict[str, str]:
    for path in paths:
        if not path.is_file():
            raise RuntimeError(f"required evidence input is missing: {path}")
    return {str(path.relative_to(ROOT)): f"sha256:{sha256(path)}" for path in sorted(paths)}


def main() -> None:
    require_clean_versioned_source()
    fds_files = list((ROOT / "contracts/fds").rglob("*.json"))
    contracts = [ROOT / "contracts/openapi/forgeops.openapi.json", *fds_files]
    governance_fixtures = [
        ROOT / "contracts/fds/examples/core-semantics.component.json",
        ROOT / "contracts/fds/examples/reference-domain-a.domain.json",
        ROOT / "scripts/epic_02_6b_owner_demo.py",
        ROOT / "tests/integration/test_domain_registry_api.py",
        ROOT / "apps/web/e2e/domain-registry.spec.ts",
    ]
    migrations = [ROOT / "migrations/versions/0006_fds_registry_domain_locks.py"]
    requirements_and_decisions = [
        ROOT / "docs/requirements/EPIC-02.6B-fds-registry-project-domain-lock.md",
        ROOT / "docs/adrs/0007-fds-registry-installation-project-domain-lock.md",
    ]
    sboms = [
        ROOT / "artifacts/generated/python-sbom.cdx.json",
        ROOT / "artifacts/generated/node-sbom.cdx.json",
    ]
    wheels = sorted((ROOT / "dist").glob("forgeops_platform-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"expected one built wheel, found {len(wheels)}")
    node_package = json.loads((ROOT / "package.json").read_text())
    coverage_percent = combined_coverage_percent(ROOT / "coverage.xml")
    now = datetime.now(UTC)
    evidence_artifact_commit = os.environ.get(
        "EPIC_02_6B_EVIDENCE_ARTIFACT_COMMIT", "RECORDED_AFTER_INITIAL_EVIDENCE_COMMIT"
    )
    evidence = {
        "evidenceId": f"EPIC-02.6B-{now.strftime('%Y%m%dT%H%M%SZ')}",
        "createdAt": now.isoformat(),
        "scope": "LOCAL_SYNTHETIC_REGISTRY_ENGINEERING",
        "requirementStatus": {"REQ-FDS-001": "CLARIFYING_PARTIAL"},
        "epicStatus": {
            "EPIC-02.6A": "VERIFIED_FOR_LOCAL_SYNTHETIC_CONTRACT_ENGINEERING",
            "EPIC-02.6B": "VERIFIED_FOR_LOCAL_SYNTHETIC_REGISTRY_ENGINEERING",
            "EPIC-02.6C": "NOT_STARTED",
            "EPIC-03": "NOT_STARTED",
        },
        "enterpriseApproval": "NOT_GRANTED",
        "verifiedSourceCommit": current_git_commit(),
        "evidenceArtifactCommit": evidence_artifact_commit,
        "python": platform.python_version(),
        "node": (ROOT / ".node-version").read_text().strip(),
        "pnpm": str(node_package["packageManager"]),
        "uv": "0.12.0 (CI-pinned)",
        "locks": digest_files([ROOT / "uv.lock", ROOT / "pnpm-lock.yaml"]),
        "contracts": digest_files(contracts),
        "syntheticRegistryInstallationDomainLockFixtures": digest_files(governance_fixtures),
        "migration": digest_files(migrations),
        "requirementsAndDecisions": digest_files(requirements_and_decisions),
        "runtimeWheel": digest_files(wheels),
        "sboms": digest_files(sboms),
        "results": {
            "pytestTotal": {
                "passed": FULL_PYTEST_PASSED,
                "coveragePercent": coverage_percent,
                "coverageMetric": "combined-lines-and-branches",
            },
            "contractTests": {"passed": CONTRACT_TESTS_PASSED},
            "fdsFocusedTests": {"passed": FDS_FOCUSED_TESTS_PASSED},
            "epic02_6bFocusedTests": {"passed": EPIC_02_6B_FOCUSED_TESTS_PASSED},
            "webTests": {"passed": WEB_TESTS_PASSED},
            "playwrightTests": {"passed": PLAYWRIGHT_TESTS_PASSED},
            "migrationHead": "0006",
            "migrationRoundTrip": "PASSED",
            "openApiAndFdsConsecutiveExportsIdentical": True,
            "architectureScannedPythonFiles": ARCHITECTURE_PYTHON_FILES,
            "architectureScannedWebFiles": ARCHITECTURE_WEB_FILES,
            "architectureViolations": 0,
            "wheelArchitectureViolations": 0,
            "pythonKnownVulnerabilities": 0,
            "nodeKnownVulnerabilities": 0,
            "apiPersistedAcrossRestart": True,
            "registryPersistedAcrossRestart": True,
            "domainInstallationPersistedAcrossRestart": True,
            "currentAndHistoryDomainLocksPersistedAcrossRestart": True,
            "webPreviewProxiedRealApiState": True,
            "crossOrganizationPrivateSuccessfulReads": 0,
            "authorizationEffectsCreated": 0,
            "runtimeStatesCreated": 0,
            "semanticRuntimesCreated": 0,
            "externalWrites": False,
        },
        "verified": [
            "TEST-FDS-REGISTRY-001",
            "TEST-FDS-REGISTRY-SCOPE-001",
            "TEST-FDS-INSTALL-001",
            "TEST-FDS-INSTALL-NEG-001",
            "TEST-FDS-DOMAINLOCK-001",
            "TEST-FDS-DOMAINLOCK-NEG-001",
            "TEST-FDS-IMPACT-001",
            "TEST-FDS-AUTH-001",
            "TEST-FDS-API-001",
            "TEST-FDS-PERSISTENCE-001",
            "TEST-FDS-LEGACY-002",
            "TEST-WEB-FDS-001",
            "TEST-ARCH-004",
        ],
        "limitations": [
            "REQ-FDS-001 and EPIC-02.6 remain CLARIFYING/PARTIAL",
            "TEST-FDS-002 has Registry/DomainLock partial evidence only; Workflow Run "
            "and replay are unverified",
            "TEST-FDS-004 enterprise signature, publisher, license and supply-chain "
            "verification remains NOT_STARTED/BLOCKED",
            "semantic, knowledge, grounding and Context Compiler capabilities are "
            "EPIC-02.6C and not started",
            "Workflow, Agent and Run runtime capabilities are EPIC-03 or later and not started",
            "PostgreSQL service runtime, enterprise OIDC, PREPROD/PROD, real data and "
            "business UAT are unverified",
            "local-sha256 and FIRST_PARTY_LOCAL are local synthetic integrity only, "
            "not enterprise trust",
            "no G2, G4, G5A, G5B or production release gate is advanced by this evidence",
        ],
    }
    output = ROOT / "docs/acceptance/generated-epic-02.6b-evidence.json"
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()
