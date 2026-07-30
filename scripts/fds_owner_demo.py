from __future__ import annotations

import json
from pathlib import Path

from forgeops.fds_sdk.models import FdsManifest, PackageRef, TargetVersions
from forgeops.fds_sdk.resolver import DependencyResolver
from forgeops.fds_sdk.validation import FdsManifestValidator

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "contracts/fds/examples"
ROOT_PACKAGE = "org.forgeops.scenario.contract-shape"
REQUIRED_COMPONENT = "org.forgeops.component.core-semantics"


def load_candidates() -> list[FdsManifest]:
    paths = sorted(
        path
        for suffix in ("*.domain.json", "*.overlay.json", "*.scenario.json", "*.component.json")
        for path in EXAMPLES.glob(suffix)
    )
    candidates: list[FdsManifest] = []
    for path in paths:
        report = FdsManifestValidator().validate(json.loads(path.read_text()))
        if report.manifest is None:
            raise RuntimeError(f"invalid owner-demo fixture {path.name}: {report.issues}")
        candidates.append(report.manifest)
    return candidates


def main() -> None:
    candidates = load_candidates()
    resolver = DependencyResolver()
    root = PackageRef(package_id=ROOT_PACKAGE, version_constraint="==0.1.0")
    targets = TargetVersions(platform="0.1.0", fds="0.1.0", scenario_sdk="0.1.0")
    legal = resolver.resolve(root, candidates, targets)
    illegal = resolver.resolve(
        root,
        [item for item in candidates if item.package_id != REQUIRED_COMPONENT],
        targets,
    )
    if legal.lock is None or not illegal.issues:
        raise RuntimeError("owner demo did not produce its expected legal/illegal outcomes")
    result = {
        "scope": "LOCAL_SYNTHETIC_CONTRACT_ONLY",
        "legalPackage": {
            "status": "LOCKED",
            "rootPackageId": legal.lock.root_package_id,
            "nodeCount": len(legal.lock.nodes),
            "lockDigest": legal.lock.lock_digest,
            "authorizationEffect": legal.lock.authorization_effect,
            "runtimeStateCreated": legal.lock.runtime_state_created,
        },
        "illegalPackage": {
            "status": "REJECTED",
            "removedRequiredPackage": REQUIRED_COMPONENT,
            "issueCode": illegal.issues[0].code.value,
            "issuePath": illegal.issues[0].path,
            "partialLockReturned": illegal.lock is not None,
        },
        "notImplemented": [
            "FDS Registry or installation",
            "Project DomainLock",
            "semantic or knowledge runtime",
            "business or cross-industry E2E",
        ],
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
