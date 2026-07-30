from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def load_fixture() -> Any:
    def loader(package_id: str) -> tuple[dict[str, Any], bytes]:
        package_root = REPOSITORY_ROOT / "scenario-packages" / package_id
        manifest = json.loads((package_root / "manifest.json").read_text())
        artifact_payload = (package_root / "artifact.json").read_bytes()
        return manifest, artifact_payload

    return loader
