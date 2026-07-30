from __future__ import annotations

import ast
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CORE_ROOTS = (
    REPOSITORY_ROOT / "src/forgeops/platform_core",
    REPOSITORY_ROOT / "src/forgeops/platform_contracts",
    REPOSITORY_ROOT / "src/forgeops/scenario_sdk",
)
FORBIDDEN_MODULE_TERMS = ("steel_cord", "equipment_anomaly", "scenario_packages")
FORBIDDEN_CORE_DOMAIN_TERMS = (
    "ortools",
    "cp_sat",
    "machine_order",
    "fault_hypothesis",
    "alarm_event",
)


def test_platform_core_has_zero_reference_scenario_imports() -> None:
    violations: list[str] = []
    for root in CORE_ROOTS:
        for source_file in root.rglob("*.py"):
            tree = ast.parse(source_file.read_text(), filename=str(source_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name.lower() for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [(node.module or "").lower()]
                else:
                    continue
                if any(term in name for name in names for term in FORBIDDEN_MODULE_TERMS):
                    violations.append(f"{source_file}:{node.lineno}")
    assert violations == []


def test_platform_source_has_no_reference_domain_leakage() -> None:
    violations: list[str] = []
    for root in CORE_ROOTS:
        for source_file in root.rglob("*.py"):
            source = source_file.read_text().lower()
            for term in FORBIDDEN_CORE_DOMAIN_TERMS:
                if term in source:
                    violations.append(f"{source_file}:{term}")
    assert violations == []


def test_core_migrations_are_domain_neutral() -> None:
    migrations = "\n".join(
        path.read_text().lower() for path in (REPOSITORY_ROOT / "migrations/versions").glob("*.py")
    )
    forbidden = ("order", "machine", "operation", "alarm", "fault", "ortools")
    assert not any(term in migrations for term in forbidden)
