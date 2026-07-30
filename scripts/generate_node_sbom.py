from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DEPENDENCY_TREE = ROOT / "artifacts/generated/node-dependency-tree.json"
OUTPUT = ROOT / "artifacts/generated/node-sbom.cdx.json"


def package_url(name: str, version: str) -> str:
    return f"pkg:npm/{quote(name, safe='/')}@{quote(version, safe='')}"


def components_from_tree(roots: list[dict[str, Any]]) -> list[dict[str, object]]:
    components: dict[str, dict[str, object]] = {}

    def collect(dependencies: object) -> None:
        if not isinstance(dependencies, dict):
            return
        for name, raw_metadata in dependencies.items():
            if not isinstance(raw_metadata, dict):
                continue
            version = raw_metadata.get("version")
            if not isinstance(version, str) or not version:
                continue
            purl = package_url(str(name), version)
            component: dict[str, object] = {
                "type": "library",
                "bom-ref": purl,
                "name": str(name),
                "version": version,
                "purl": purl,
            }
            resolved = raw_metadata.get("resolved")
            if isinstance(resolved, str) and resolved.startswith("https://registry.npmjs.org/"):
                component["externalReferences"] = [{"type": "distribution", "url": resolved}]
            components[purl] = component
            for field in ("dependencies", "devDependencies", "optionalDependencies"):
                collect(raw_metadata.get(field))

    for root in roots:
        for field in ("dependencies", "devDependencies", "optionalDependencies"):
            collect(root.get(field))
    return [components[key] for key in sorted(components)]


def main() -> None:
    roots = json.loads(DEPENDENCY_TREE.read_text())
    if not isinstance(roots, list):
        raise TypeError("pnpm dependency tree must be a JSON array")
    components = components_from_tree(roots)
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "bom-ref": "pkg:npm/forgeops-platform@0.1.0",
                "name": "forgeops-platform",
                "version": "0.1.0",
                "purl": "pkg:npm/forgeops-platform@0.1.0",
            },
            "properties": [
                {"name": "forgeops:scope", "value": "LOCAL_SYNTHETIC_ENGINEERING"},
                {"name": "forgeops:enterpriseApproval", "value": "NOT_GRANTED"},
            ],
        },
        "components": components,
    }
    OUTPUT.write_text(json.dumps(sbom, indent=2, sort_keys=True) + "\n")
    print(f"{OUTPUT.relative_to(ROOT)}: {len(components)} components")


if __name__ == "__main__":
    main()
