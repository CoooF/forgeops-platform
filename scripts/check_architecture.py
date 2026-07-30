from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORM_ROOTS = (
    ROOT / "src/forgeops/platform_core",
    ROOT / "src/forgeops/platform_contracts",
    ROOT / "src/forgeops/scenario_sdk",
)
FORBIDDEN_IMPORTS = ("scenario_packages", "steel_cord", "equipment_anomaly", "ortools")


def main() -> None:
    violations: list[dict[str, object]] = []
    scanned = 0
    for platform_root in PLATFORM_ROOTS:
        for source_file in platform_root.rglob("*.py"):
            scanned += 1
            tree = ast.parse(source_file.read_text(), filename=str(source_file))
            for node in ast.walk(tree):
                modules: list[str] = []
                if isinstance(node, ast.Import):
                    modules = [alias.name.lower() for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    modules = [(node.module or "").lower()]
                if any(term in module for module in modules for term in FORBIDDEN_IMPORTS):
                    violations.append(
                        {
                            "file": str(source_file.relative_to(ROOT)),
                            "line": node.lineno,
                            "modules": modules,
                        }
                    )
    result = {
        "testId": "TEST-ARCH-001",
        "requirementIds": ["REQ-SDK-001", "REQ-PKG-001", "NFR-EXT-001"],
        "scannedPythonFiles": scanned,
        "platformToReferenceScenarioDependencies": len(violations),
        "violations": violations,
        "passed": not violations,
    }
    print(json.dumps(result, indent=2))
    if violations:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
