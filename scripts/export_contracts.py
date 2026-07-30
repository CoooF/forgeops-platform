from __future__ import annotations

import json
from pathlib import Path

from forgeops.api import create_app
from forgeops.scenario_sdk.manifest import ScenarioManifest

ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main() -> None:
    write_json(ROOT / "contracts/openapi/forgeops.openapi.json", create_app().openapi())
    write_json(
        ROOT / "contracts/jsonschema/scenario-manifest.schema.json",
        ScenarioManifest.model_json_schema(by_alias=True),
    )


if __name__ == "__main__":
    main()
