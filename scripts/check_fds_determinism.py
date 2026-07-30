from __future__ import annotations

import hashlib
import json
from pathlib import Path

from export_contracts import export_fds_contracts

ROOT = Path(__file__).resolve().parents[1]
FDS_ROOT = ROOT / "contracts/fds"


def digest_map() -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(FDS_ROOT.rglob("*.json"))
    }


def main() -> None:
    export_fds_contracts()
    first = digest_map()
    export_fds_contracts()
    second = digest_map()
    result = {
        "testIds": ["TEST-FDS-LOCK-001", "TEST-FDS-CONTRACT-001"],
        "files": len(first),
        "digests": first,
        "identicalAcrossConsecutiveExports": first == second,
        "passed": first == second,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if first != second:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
