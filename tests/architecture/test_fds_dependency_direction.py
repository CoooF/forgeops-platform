from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FDS_ROOT = ROOT / "src/forgeops/fds_sdk"


def test_fds_sdk_has_no_runtime_framework_or_reference_domain_dependency() -> None:
    forbidden_modules = ("fastapi", "sqlalchemy", "temporal", "ortools", "openai", "langchain")
    forbidden_source_terms = ("manufacturing", "steel-cord", "steel_cord")
    violations: list[str] = []
    for source_file in FDS_ROOT.rglob("*.py"):
        source = source_file.read_text()
        assert not any(term in source.lower() for term in forbidden_source_terms)
        tree = ast.parse(source, filename=str(source_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name.lower() for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [(node.module or "").lower()]
            else:
                continue
            if any(term in module for module in modules for term in forbidden_modules):
                violations.append(f"{source_file}:{node.lineno}:{modules}")
    assert violations == []


def test_fds_kernel_has_no_registry_or_state_creation_import() -> None:
    imports = "\n".join(path.read_text() for path in FDS_ROOT.rglob("*.py"))
    assert "scenario_registry" not in imports
    assert "identity_access" not in imports
    assert "domain_registry" not in imports
