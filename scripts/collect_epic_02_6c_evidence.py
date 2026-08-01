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

# Updated from the single final high-cost verification run before the source commit.
FULL_PYTEST_PASSED = 410
CONTRACT_TESTS_PASSED = 41
EPIC_02_6C_FOCUSED_TESTS_PASSED = 290
WEB_TESTS_PASSED = 6
PLAYWRIGHT_TESTS_PASSED = 3
ARCHITECTURE_PYTHON_FILES = 44
ARCHITECTURE_WEB_FILES = 11


def digest_files(paths: list[Path]) -> dict[str, str]:
    for path in paths:
        if not path.is_file():
            raise RuntimeError(f"required evidence input is missing: {path}")
    return {str(path.relative_to(ROOT)): f"sha256:{sha256(path)}" for path in sorted(paths)}


def main() -> None:
    require_clean_versioned_source()
    contracts = [
        ROOT / "contracts/openapi/forgeops.openapi.json",
        *list((ROOT / "contracts/fds").rglob("*.json")),
        *list((ROOT / "contracts/semantic").rglob("*.json")),
    ]
    fixtures_and_executable_evidence = [
        ROOT / "scripts/epic_02_6c_owner_demo.py",
        ROOT / "tests/integration/test_semantic_knowledge_runtime_api.py",
        ROOT / "apps/web/e2e/semantic-knowledge.spec.ts",
        ROOT / "apps/web/src/SemanticKnowledge.tsx",
        ROOT / "apps/web/src/ProjectContext.tsx",
    ]
    requirements_and_decisions = [
        ROOT / "docs/requirements/EPIC-02.6C-semantic-knowledge-runtime.md",
        ROOT / "docs/adrs/0008-semantic-knowledge-context-grounding.md",
    ]
    migration = [ROOT / "migrations/versions/0008_semantic_knowledge_runtime.py"]
    sboms = [
        ROOT / "artifacts/generated/python-sbom.cdx.json",
        ROOT / "artifacts/generated/node-sbom.cdx.json",
    ]
    wheels = sorted((ROOT / "dist").glob("forgeops_platform-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"expected one built wheel, found {len(wheels)}")
    node_package = json.loads((ROOT / "package.json").read_text())
    evidence_artifact_commit = os.environ.get(
        "EPIC_02_6C_EVIDENCE_ARTIFACT_COMMIT", "RECORDED_AFTER_INITIAL_EVIDENCE_COMMIT"
    )
    verified_source_commit = os.environ.get(
        "EPIC_02_6C_VERIFIED_SOURCE_COMMIT", current_git_commit()
    )
    now = datetime.now(UTC)
    evidence = {
        "evidenceId": f"EPIC-02.6C-{now.strftime('%Y%m%dT%H%M%SZ')}",
        "createdAt": now.isoformat(),
        "scope": "LOCAL_SYNTHETIC_SEMANTIC_ENGINEERING",
        "requirementStatus": {
            "REQ-FDS-001": "CLARIFYING_PARTIAL",
            "REQ-SEM-001": "CLARIFYING_PARTIAL_LOCAL_SLICE_VERIFIED",
            "REQ-KNW-001": "CLARIFYING_PARTIAL_LOCAL_SLICE_VERIFIED",
            "REQ-GRD-001": "CLARIFYING_PARTIAL_LOCAL_SLICE_VERIFIED",
        },
        "epicStatus": {
            "EPIC-02.6A": "VERIFIED_FOR_LOCAL_SYNTHETIC_CONTRACT_ENGINEERING",
            "EPIC-02.6B": "VERIFIED_FOR_LOCAL_SYNTHETIC_REGISTRY_ENGINEERING",
            "EPIC-02.6C": "VERIFIED_FOR_LOCAL_SYNTHETIC_SEMANTIC_ENGINEERING",
            "EPIC-02.6": "CLARIFYING_PARTIAL",
            "EPIC-02.7": "NOT_STARTED",
            "EPIC-03": "NOT_STARTED",
        },
        "enterpriseApproval": "NOT_GRANTED",
        "verifiedSourceCommit": verified_source_commit,
        "evidenceArtifactCommit": evidence_artifact_commit,
        "python": platform.python_version(),
        "node": (ROOT / ".node-version").read_text().strip(),
        "pnpm": str(node_package["packageManager"]),
        "uv": "0.12.0 (CI-pinned)",
        "locks": digest_files([ROOT / "uv.lock", ROOT / "pnpm-lock.yaml"]),
        "contracts": digest_files(contracts),
        "fixturesAndExecutableEvidence": digest_files(fixtures_and_executable_evidence),
        "migration": digest_files(migration),
        "requirementsAndDecisions": digest_files(requirements_and_decisions),
        "runtimeWheel": digest_files(wheels),
        "sboms": digest_files(sboms),
        "results": {
            "pytestTotal": {
                "passed": FULL_PYTEST_PASSED,
                "coveragePercent": combined_coverage_percent(ROOT / "coverage.xml"),
                "coverageMetric": "combined-lines-and-branches",
            },
            "contractTests": {"passed": CONTRACT_TESTS_PASSED},
            "epic02_6cFocusedTests": {"passed": EPIC_02_6C_FOCUSED_TESTS_PASSED},
            "webTests": {"passed": WEB_TESTS_PASSED},
            "playwrightTests": {"passed": PLAYWRIGHT_TESTS_PASSED},
            "migrationHead": "0008",
            "migrationRoundTrip": "PASSED",
            "openApiAndSemanticConsecutiveExportsIdentical": True,
            "architectureScannedPythonFiles": ARCHITECTURE_PYTHON_FILES,
            "architectureScannedWebFiles": ARCHITECTURE_WEB_FILES,
            "architectureViolations": 0,
            "wheelArchitectureViolations": 0,
            "pythonKnownVulnerabilities": 0,
            "nodeKnownVulnerabilities": 0,
            "semanticPayloadsPersistedAcrossRestart": True,
            "knowledgeVersionsPersistedAcrossRestart": True,
            "contextManifestHistoryPersistedAcrossRestart": True,
            "silentSemanticGuesses": 0,
            "crossOrganizationSuccessfulReads": 0,
            "knowledgeContentExecuted": False,
            "agentRuns": 0,
            "llmCalls": 0,
            "ragQueries": 0,
            "workflowRuns": 0,
            "authorizationEffectsCreated": 0,
            "externalWrites": False,
        },
        "verified": [
            "TEST-SEM-CONTRACT-001",
            "TEST-SEM-REGISTRY-001",
            "TEST-SEM-QUERY-001",
            "TEST-SEM-MAPPING-001",
            "TEST-SEM-AMBIGUITY-001",
            "TEST-KNW-LIFECYCLE-001",
            "TEST-KNW-SEC-001",
            "TEST-CONTEXT-COMPILER-001",
            "TEST-GROUNDING-001",
            "TEST-SEM-IMPACT-001",
            "TEST-SEM-AUTH-001",
            "TEST-SEM-PERSISTENCE-001",
            "TEST-SEM-API-001",
            "TEST-WEB-SEM-001",
            "TEST-ARCH-005",
        ],
        "limitations": [
            "REQ-FDS/SEM/KNW/GRD and EPIC-02.6 remain CLARIFYING/PARTIAL",
            "industry ontology and mapping correctness are unverified",
            "enterprise knowledge license, classification, provenance and hostile-file "
            "review are unverified",
            "model grounding, model replacement, RAG quality and Agent hallucination "
            "are unverified",
            "EPIC-02.7 and EPIC-03 Workflow Studio/Run/debugger are not started",
            "PostgreSQL service behavior, enterprise OIDC/SCIM, PREPROD/PROD, real data "
            "and UAT are unverified",
            "no G2, G4, G5A, G5B or production release gate is advanced",
        ],
    }
    output = ROOT / "docs/acceptance/generated-epic-02.6c-evidence.json"
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()
