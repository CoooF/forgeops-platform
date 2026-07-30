from __future__ import annotations

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_no_production_write_or_control_dependencies() -> None:
    dependency_files = [
        REPOSITORY_ROOT / "pyproject.toml",
        REPOSITORY_ROOT / "package.json",
        REPOSITORY_ROOT / "apps/web/package.json",
    ]
    forbidden = ("snap7", "opcua", "pycomm3", "rpa", "plc", "mes-write", "erp-write")
    combined = "\n".join(path.read_text().lower() for path in dependency_files if path.exists())
    assert not any(term in combined for term in forbidden)


def test_no_real_data_or_secret_material_in_fixtures() -> None:
    package_root = REPOSITORY_ROOT / "scenario-packages"
    contents = "\n".join(path.read_text() for path in package_root.rglob("*.json"))
    assert "SYNTHETIC" in contents
    forbidden = ("password", "api_key", "client_secret", "BEGIN PRIVATE KEY", "jdbc:")
    assert not any(term in contents for term in forbidden)


def test_api_has_no_external_execution_route() -> None:
    source = (REPOSITORY_ROOT / "src/forgeops/api.py").read_text().lower()
    forbidden_routes = (':execute"', '/execute"', "update-mes", "write-plc")
    assert not any(route in source for route in forbidden_routes)
