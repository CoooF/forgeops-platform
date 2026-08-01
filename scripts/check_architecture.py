from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORM_ROOTS = (
    ROOT / "src/forgeops/platform_core",
    ROOT / "src/forgeops/platform_contracts",
    ROOT / "src/forgeops/scenario_sdk",
    ROOT / "src/forgeops/fds_sdk",
)
FORBIDDEN_IMPORTS = ("scenario_packages", "steel_cord", "equipment_anomaly", "ortools")
FDS_FORBIDDEN_IMPORTS = ("fastapi", "sqlalchemy", "temporal", "openai", "langchain")
FDS_FORBIDDEN_TERMS = ("manufacturing", "steel-cord", "steel_cord")
FORBIDDEN_WEB_TERMS = ("steel-cord", "equipment-anomaly", "manufacturing", "plc", "rpa")
SEMANTIC_RUNTIME_ROOTS = (
    ROOT / "src/forgeops/platform_core/semantic_runtime",
    ROOT / "src/forgeops/platform_core/knowledge_hub",
)
SEMANTIC_FORBIDDEN_IMPORTS = (
    "openai",
    "langchain",
    "llama_index",
    "chromadb",
    "pinecone",
    "neo4j",
    "networkx",
    "temporal",
)
SEMANTIC_FORBIDDEN_TERMS = (
    "manufacturing",
    "steel-cord",
    "steel_cord",
    "production_order",
    "machine_id",
    "process_route",
)


def main() -> None:
    violations: list[dict[str, object]] = []
    scanned = 0
    for platform_root in PLATFORM_ROOTS:
        for source_file in platform_root.rglob("*.py"):
            scanned += 1
            source = source_file.read_text()
            tree = ast.parse(source, filename=str(source_file))
            if platform_root.name == "fds_sdk":
                for term in FDS_FORBIDDEN_TERMS:
                    if term in source.lower():
                        violations.append(
                            {
                                "file": str(source_file.relative_to(ROOT)),
                                "term": term,
                            }
                        )
            for node in ast.walk(tree):
                modules: list[str] = []
                if isinstance(node, ast.Import):
                    modules = [alias.name.lower() for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    modules = [(node.module or "").lower()]
                else:
                    continue
                if any(term in module for module in modules for term in FORBIDDEN_IMPORTS):
                    violations.append(
                        {
                            "file": str(source_file.relative_to(ROOT)),
                            "line": node.lineno,
                            "modules": modules,
                        }
                    )
                if platform_root.name == "fds_sdk" and any(
                    term in module for module in modules for term in FDS_FORBIDDEN_IMPORTS
                ):
                    violations.append(
                        {
                            "file": str(source_file.relative_to(ROOT)),
                            "line": node.lineno,
                            "modules": modules,
                            "reason": "FDS runtime framework dependency",
                        }
                    )
    web_root = ROOT / "apps/web/src"
    scanned_web_files = 0
    for source_file in (*web_root.rglob("*.ts"), *web_root.rglob("*.tsx")):
        scanned_web_files += 1
        lowered = source_file.read_text().lower()
        for term in FORBIDDEN_WEB_TERMS:
            if term in lowered:
                violations.append(
                    {
                        "file": str(source_file.relative_to(ROOT)),
                        "term": term,
                    }
                )
    for semantic_root in SEMANTIC_RUNTIME_ROOTS:
        for source_file in semantic_root.rglob("*.py"):
            source = source_file.read_text()
            lowered = source.lower()
            for term in SEMANTIC_FORBIDDEN_TERMS:
                if term in lowered:
                    violations.append(
                        {
                            "file": str(source_file.relative_to(ROOT)),
                            "term": term,
                            "reason": "semantic runtime must remain domain-neutral",
                        }
                    )
            tree = ast.parse(source, filename=str(source_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules = [alias.name.lower() for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    modules = [(node.module or "").lower()]
                else:
                    continue
                if any(term in module for module in modules for term in SEMANTIC_FORBIDDEN_IMPORTS):
                    violations.append(
                        {
                            "file": str(source_file.relative_to(ROOT)),
                            "line": node.lineno,
                            "modules": modules,
                            "reason": "Agent/LLM/vector/graph/workflow runtime dependency",
                        }
                    )
    result = {
        "testId": "TEST-ARCH-001",
        "testIds": ["TEST-ARCH-001", "TEST-ARCH-003", "TEST-ARCH-005"],
        "requirementIds": [
            "REQ-SDK-001",
            "REQ-PKG-001",
            "REQ-FDS-001",
            "REQ-SEM-001",
            "REQ-KNW-001",
            "REQ-GRD-001",
            "NFR-EXT-001",
        ],
        "scannedPythonFiles": scanned,
        "scannedWebFiles": scanned_web_files,
        "platformToReferenceScenarioDependencies": len(violations),
        "violations": violations,
        "passed": not violations,
    }
    print(json.dumps(result, indent=2))
    if violations:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
