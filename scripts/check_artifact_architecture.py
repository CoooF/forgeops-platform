from __future__ import annotations

import ast
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_IMPORTS = (
    "scenario_packages",
    "steel_cord",
    "equipment_anomaly",
    "ortools",
)
FDS_FORBIDDEN_IMPORTS = ("fastapi", "sqlalchemy", "temporal", "openai", "langchain")
FDS_FORBIDDEN_TERMS = ("manufacturing", "steel-cord", "steel_cord")
FORBIDDEN_MEMBERS = ("scenario-packages/", "steel-cord", "equipment-anomaly")
PLATFORM_PREFIXES = (
    "forgeops/platform_core/",
    "forgeops/platform_contracts/",
    "forgeops/scenario_sdk/",
    "forgeops/fds_sdk/",
)


def imported_modules(source: str, filename: str) -> list[tuple[int, list[str]]]:
    imports: list[tuple[int, list[str]]] = []
    tree = ast.parse(source, filename=filename)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.append((node.lineno, [alias.name.lower() for alias in node.names]))
        elif isinstance(node, ast.ImportFrom):
            imports.append((node.lineno, [(node.module or "").lower()]))
    return imports


def main() -> None:
    wheels = sorted((ROOT / "dist").glob("forgeops_platform-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"expected exactly one ForgeOps wheel, found {len(wheels)}")
    wheel = wheels[0]
    violations: list[dict[str, object]] = []
    scanned_python_files = 0
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        for name in names:
            lowered = name.lower()
            if any(term in lowered for term in FORBIDDEN_MEMBERS):
                violations.append({"member": name, "reason": "reference scenario in runtime wheel"})
            if not name.endswith(".py") or not name.startswith(PLATFORM_PREFIXES):
                continue
            scanned_python_files += 1
            source = archive.read(name).decode()
            if name.startswith("forgeops/fds_sdk/"):
                for term in FDS_FORBIDDEN_TERMS:
                    if term in source.lower():
                        violations.append({"member": name, "term": term})
            for line, modules in imported_modules(source, name):
                if any(term in module for module in modules for term in FORBIDDEN_IMPORTS):
                    violations.append({"member": name, "line": line, "modules": modules})
                if name.startswith("forgeops/fds_sdk/") and any(
                    term in module for module in modules for term in FDS_FORBIDDEN_IMPORTS
                ):
                    violations.append(
                        {
                            "member": name,
                            "line": line,
                            "modules": modules,
                            "reason": "FDS runtime framework dependency",
                        }
                    )
        metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
        metadata = archive.read(metadata_name).decode().lower()
        if any(f"requires-dist: {term}" in metadata for term in FORBIDDEN_IMPORTS):
            violations.append({"member": metadata_name, "reason": "forbidden runtime dependency"})
    result = {
        "testId": "TEST-ARCH-ARTIFACT-001",
        "testIds": ["TEST-ARCH-ARTIFACT-001", "TEST-ARCH-003"],
        "requirementIds": [
            "REQ-SDK-001",
            "REQ-PKG-001",
            "REQ-FDS-001",
            "NFR-EXT-001",
        ],
        "artifact": str(wheel.relative_to(ROOT)),
        "artifactSha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "scannedPlatformPythonFiles": scanned_python_files,
        "platformToReferenceScenarioDependencies": len(violations),
        "violations": violations,
        "passed": not violations,
    }
    print(json.dumps(result, indent=2))
    if violations:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
