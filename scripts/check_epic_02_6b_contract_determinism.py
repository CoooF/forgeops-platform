from __future__ import annotations

import hashlib
import json
from pathlib import Path

from export_contracts import main as export_contracts

ROOT = Path(__file__).resolve().parents[1]
OPENAPI = ROOT / "contracts/openapi/forgeops.openapi.json"
FDS_ROOT = ROOT / "contracts/fds"


def digest_map() -> dict[str, str]:
    paths = [OPENAPI, *sorted(FDS_ROOT.rglob("*.json"))]
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths
    }


def main() -> None:
    export_contracts()
    first = digest_map()
    export_contracts()
    second = digest_map()
    identical = first == second
    result = {
        "testIds": ["TEST-FDS-API-001", "TEST-FDS-CONTRACT-001"],
        "files": len(first),
        "digests": first,
        "identicalAcrossConsecutiveExports": identical,
        "passed": identical,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if not identical:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
