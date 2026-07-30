from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATHS = (
    ROOT / "pyproject.toml",
    ROOT / "package.json",
    ROOT / "apps/web/package.json",
    ROOT / "deploy/local/compose.yaml",
)


def main() -> None:
    findings: list[dict[str, str]] = []
    for path in SCAN_PATHS:
        source = path.read_text()
        if re.search(r"(?:image|FROM):?\s+[^\s]+:latest\b", source, re.IGNORECASE):
            findings.append({"file": str(path.relative_to(ROOT)), "reason": "floating latest tag"})
    dependency_text = "\n".join(path.read_text().lower() for path in SCAN_PATHS[:3])
    for dependency in (
        "snap7",
        "pycomm3",
        "robotframework-rpa",
        "playwright-stealth",
        "ortools",
    ):
        if dependency in dependency_text:
            findings.append({"file": "dependency manifests", "reason": f"forbidden: {dependency}"})
    result = {
        "testIds": ["TEST-ACT-002", "TEST-SEC-002"],
        "requirementIds": ["REQ-ACT-001", "NFR-SUP-001"],
        "findings": findings,
        "passed": not findings,
        "limitations": [
            "local source/config scan only",
            "does not prove enterprise Secret or network configuration",
        ],
    }
    print(json.dumps(result, indent=2))
    if findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
