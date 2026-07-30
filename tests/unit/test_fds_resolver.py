from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from forgeops.fds_sdk.canonical import canonical_json
from forgeops.fds_sdk.models import (
    Compatibility,
    ConflictDeclaration,
    DependencyRequirement,
    FdsManifest,
    PackageKind,
    PackageRef,
    RequestedResourceBudget,
    TargetVersions,
    Visibility,
)
from forgeops.fds_sdk.resolver import DependencyResolver, verify_dependency_lock
from forgeops.fds_sdk.validation import FdsManifestValidator
from forgeops.platform_contracts.errors import ErrorCode

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "contracts/fds/examples"
TARGETS = TargetVersions(platform="0.1.0", fds="0.1.0", scenario_sdk="0.1.0")
ROOT_REF = PackageRef(
    package_id="org.forgeops.scenario.contract-shape", version_constraint="==0.1.0"
)


def graph() -> list[FdsManifest]:
    manifests: list[FdsManifest] = []
    paths = sorted(
        path
        for suffix in ("*.domain.json", "*.overlay.json", "*.scenario.json", "*.component.json")
        for path in EXAMPLES.glob(suffix)
    )
    for path in paths:
        report = FdsManifestValidator().validate(json.loads(path.read_text()))
        assert report.manifest is not None, report.issues
        manifests.append(report.manifest)
    return manifests


def by_id(manifests: list[FdsManifest], package_id: str) -> FdsManifest:
    return next(item for item in manifests if item.package_id == package_id)


def replace(manifests: list[FdsManifest], updated: FdsManifest) -> list[FdsManifest]:
    return [updated if item.package_id == updated.package_id else item for item in manifests]


def resolve(manifests: list[FdsManifest], **kwargs: Any) -> Any:
    return DependencyResolver().resolve(ROOT_REF, manifests, TARGETS, **kwargs)


def test_multilayer_graph_produces_fixed_topological_lock_without_runtime_state() -> None:
    report = resolve(graph())
    assert report.valid, report.issues
    assert report.lock is not None
    assert [node.package_id for node in report.lock.nodes] == [
        "org.forgeops.component.core-semantics",
        "org.forgeops.domain.manufacturing-shape",
        "org.forgeops.domain.steel-cord-shape",
        "org.forgeops.overlay.synthetic-shape",
        "org.forgeops.scenario.contract-shape",
    ]
    assert report.lock.authorization_effect == "NONE"
    assert report.lock.runtime_state_created is False
    assert report.lock.requested_permissions == ("evidence.read",)
    assert report.lock.permission_delta == ()
    assert report.lock.resource_budget_delta == RequestedResourceBudget()
    assert verify_dependency_lock(report.lock, graph()) == ()


def test_candidate_order_and_repeated_runs_do_not_change_lock() -> None:
    manifests = graph()
    expected = resolve(manifests).lock
    assert expected is not None
    permutations = [manifests[offset:] + manifests[:offset] for offset in range(len(manifests))]
    permutations.append(list(reversed(manifests)))
    for permuted in permutations:
        actual = resolve(permuted).lock
        assert actual is not None
        assert canonical_json(actual) == canonical_json(expected)
        assert actual.lock_digest == expected.lock_digest


def test_optional_dependency_rule_is_explicit_and_deterministic() -> None:
    manifests = graph()
    root = by_id(manifests, ROOT_REF.package_id)
    optional_missing = DependencyRequirement(
        package=PackageRef(
            package_id="org.forgeops.component.optional-missing",
            version_constraint="==0.1.0",
            expected_kind=PackageKind.COMPONENT,
        ),
        required=False,
    )
    optional_present = DependencyRequirement(
        package=PackageRef(
            package_id="org.forgeops.domain.reference-a",
            version_constraint="==0.1.0",
            expected_kind=PackageKind.DOMAIN,
        ),
        required=False,
    )
    root = root.model_copy(
        update={"dependencies": (*root.dependencies, optional_missing, optional_present)}
    )
    manifests = replace(manifests, root)

    included = resolve(manifests)
    assert included.lock is not None
    assert "org.forgeops.domain.reference-a" in {node.package_id for node in included.lock.nodes}
    assert included.lock.skipped_optional_dependencies == (
        "org.forgeops.component.optional-missing",
    )

    excluded = resolve(manifests, include_optional=False)
    assert excluded.lock is not None
    assert excluded.lock.skipped_optional_dependencies == (
        "org.forgeops.component.optional-missing",
        "org.forgeops.domain.reference-a",
    )


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("missing", ErrorCode.DEPENDENCY_MISSING),
        ("version", ErrorCode.DEPENDENCY_VERSION_UNSATISFIED),
        ("kind", ErrorCode.DEPENDENCY_KIND_MISMATCH),
        ("compatibility", ErrorCode.FDS_INCOMPATIBLE),
    ],
)
def test_missing_version_kind_and_compatibility_fail_without_partial_lock(
    mutation: str, expected_code: ErrorCode
) -> None:
    manifests = graph()
    if mutation == "missing":
        manifests = [
            item for item in manifests if item.package_id != "org.forgeops.component.core-semantics"
        ]
    elif mutation == "compatibility":
        component = by_id(manifests, "org.forgeops.component.core-semantics")
        component = component.model_copy(
            update={
                "compatibility": Compatibility(
                    platform=">=0.1.0,<0.2.0",
                    fds=">=2.0.0,<3.0.0",
                    scenario_sdk=">=0.1.0,<0.2.0",
                )
            }
        )
        manifests = replace(manifests, component)
    else:
        domain = by_id(manifests, "org.forgeops.domain.manufacturing-shape")
        component_ref = domain.components[0]  # type: ignore[union-attr]
        package = component_ref.package.model_copy(
            update={
                "version_constraint": "<0.1.0" if mutation == "version" else "==0.1.0",
                "expected_kind": (
                    PackageKind.DOMAIN if mutation == "kind" else PackageKind.COMPONENT
                ),
            }
        )
        component_ref = component_ref.model_copy(update={"package": package})
        domain = domain.model_copy(update={"components": (component_ref,)})  # type: ignore[union-attr]
        manifests = replace(manifests, domain)
    report = resolve(manifests)
    assert report.lock is None
    assert expected_code in {issue.code for issue in report.issues}


def test_digest_conflict_and_same_digest_ambiguity_fail_before_selection() -> None:
    manifests = graph()
    component = by_id(manifests, "org.forgeops.component.core-semantics")
    ambiguous = component.model_copy(update={"publisher": "ANOTHER_LOCAL_PUBLISHER"})
    report = resolve([*manifests, ambiguous])
    assert report.lock is None
    assert report.issues[0].code == ErrorCode.DEPENDENCY_AMBIGUOUS

    new_digest = "sha256:" + "9" * 64
    artifact = component.artifact.model_copy(
        update={
            "content_digest": new_digest,
            "signature": "local-sha256:" + "9" * 64,
        }
    )
    conflict = component.model_copy(update={"content_digest": new_digest, "artifact": artifact})
    report = resolve([*manifests, conflict])
    assert report.lock is None
    assert report.issues[0].code == ErrorCode.PACKAGE_VERSION_DIGEST_CONFLICT


def test_cycle_conflict_layer_visibility_and_provider_conflicts_are_stable() -> None:
    manifests = graph()
    manufacturing = by_id(manifests, "org.forgeops.domain.manufacturing-shape")
    steel = by_id(manifests, "org.forgeops.domain.steel-cord-shape")
    cycle_requirement = DependencyRequirement(
        package=PackageRef(
            package_id=steel.package_id,
            version_constraint="==0.1.0",
            expected_kind=PackageKind.DOMAIN,
        )
    )
    cycle_domain = manufacturing.model_copy(
        update={"dependencies": (*manufacturing.dependencies, cycle_requirement)}
    )
    assert ErrorCode.DEPENDENCY_CYCLE in {
        issue.code for issue in resolve(replace(manifests, cycle_domain)).issues
    }

    conflict_domain = steel.model_copy(
        update={"conflicts": (ConflictDeclaration(package_id=manufacturing.package_id),)}
    )
    assert ErrorCode.DEPENDENCY_CONFLICT in {
        issue.code for issue in resolve(replace(manifests, conflict_domain)).issues
    }

    overlay = by_id(manifests, "org.forgeops.overlay.synthetic-shape")
    reverse_requirement = DependencyRequirement(
        package=PackageRef(
            package_id=overlay.package_id,
            version_constraint="==0.1.0",
            expected_kind=PackageKind.ORGANIZATION_OVERLAY,
        )
    )
    reverse_domain = manufacturing.model_copy(
        update={"dependencies": (*manufacturing.dependencies, reverse_requirement)}
    )
    reverse_codes = {issue.code for issue in resolve(replace(manifests, reverse_domain)).issues}
    assert ErrorCode.DEPENDENCY_LAYER_VIOLATION in reverse_codes
    assert ErrorCode.VISIBILITY_VIOLATION in reverse_codes

    duplicate_provider = steel.model_copy(
        update={
            "provided_capabilities": (
                *steel.provided_capabilities,
                *manufacturing.provided_capabilities,
            ),
            "provided_namespaces": (
                *steel.provided_namespaces,
                *manufacturing.provided_namespaces,
            ),
        }
    )
    provider_codes = {
        issue.code for issue in resolve(replace(manifests, duplicate_provider)).issues
    }
    assert ErrorCode.CAPABILITY_CONFLICT in provider_codes
    assert ErrorCode.NAMESPACE_CONFLICT in provider_codes


def test_scenario_and_overlay_required_domain_capabilities_must_resolve() -> None:
    manifests = graph()
    root = by_id(manifests, ROOT_REF.package_id)
    root = root.model_copy(update={"required_domain_capabilities": ("domain.unavailable",)})
    assert ErrorCode.SCENARIO_DOMAIN_CAPABILITY_MISSING in {
        issue.code for issue in resolve(replace(manifests, root)).issues
    }
    overlay = by_id(manifests, "org.forgeops.overlay.synthetic-shape")
    overlay = overlay.model_copy(update={"overrides_domain_capabilities": ("domain.unavailable",)})
    assert ErrorCode.OVERLAY_TARGET_MISSING in {
        issue.code for issue in resolve(replace(manifests, overlay)).issues
    }


def test_public_domain_cannot_reach_private_content_transitively() -> None:
    manifests = graph()
    core = by_id(manifests, "org.forgeops.component.core-semantics")
    private_digest = "sha256:" + "3" * 64
    private_artifact = core.artifact.model_copy(
        update={
            "content_digest": private_digest,
            "signature": "local-sha256:" + "3" * 64,
        }
    )
    private_component = core.model_copy(
        update={
            "package_id": "org.forgeops.component.private-helper",
            "content_digest": private_digest,
            "artifact": private_artifact,
            "visibility": Visibility.PRIVATE,
            "provided_capabilities": ("semantic.private-helper",),
            "provided_namespaces": ("org.forgeops.semantic.private-helper",),
        }
    )
    private_requirement = DependencyRequirement(
        package=PackageRef(
            package_id=private_component.package_id,
            version_constraint="==0.1.0",
            expected_kind=PackageKind.COMPONENT,
        )
    )
    core = core.model_copy(update={"dependencies": (private_requirement,)})
    report = resolve([*replace(manifests, core), private_component])
    assert report.lock is None
    assert ErrorCode.VISIBILITY_VIOLATION in {issue.code for issue in report.issues}


def test_transitive_permission_and_budget_expansion_fail_closed_but_create_no_state() -> None:
    manifests = graph()
    component = by_id(manifests, "org.forgeops.component.core-semantics")
    component = component.model_copy(
        update={
            "permissions": ("candidate.create",),
            "resource_budget": RequestedResourceBudget(cpu_millis=1),
        }
    )
    report = resolve(replace(manifests, component))
    assert report.lock is None
    assert {issue.code for issue in report.issues} == {
        ErrorCode.PERMISSION_EXPANSION,
        ErrorCode.RESOURCE_BUDGET_EXPANSION,
    }

    root = by_id(manifests, ROOT_REF.package_id)
    root = root.model_copy(
        update={
            "accepted_dependency_permissions": ("candidate.create",),
            "dependency_resource_budget_allowance": RequestedResourceBudget(cpu_millis=1),
        }
    )
    accepted = resolve(replace(replace(manifests, component), root))
    assert accepted.lock is not None
    assert accepted.lock.permission_delta == ("candidate.create",)
    assert accepted.lock.authorization_effect == "NONE"


def test_highest_compatible_version_is_selected_and_lock_tampering_is_detected() -> None:
    manifests = graph()
    manufacturing = by_id(manifests, "org.forgeops.domain.manufacturing-shape")
    higher_digest = "sha256:" + "1" * 64
    higher_artifact = manufacturing.artifact.model_copy(
        update={
            "content_digest": higher_digest,
            "signature": "local-sha256:" + "1" * 64,
        }
    )
    higher = manufacturing.model_copy(
        update={
            "package_version": "0.1.1",
            "content_digest": higher_digest,
            "artifact": higher_artifact,
        }
    )
    steel = by_id(manifests, "org.forgeops.domain.steel-cord-shape")
    extends = steel.extends[0].model_copy(  # type: ignore[union-attr]
        update={"version_constraint": ">=0.1.0,<0.2.0", "content_digest": None}
    )
    steel = steel.model_copy(update={"extends": (extends,)})
    report = resolve([*replace(replace(manifests, steel), higher), manufacturing])
    assert report.lock is not None
    selected = {node.package_id: node.package_version for node in report.lock.nodes}
    assert selected[manufacturing.package_id] == "0.1.1"

    tampered = report.lock.model_copy(update={"lock_digest": "sha256:" + "0" * 64})
    assert verify_dependency_lock(tampered)[0].code == ErrorCode.LOCK_DIGEST_MISMATCH
    changed_node = report.lock.nodes[0].model_copy(update={"content_digest": "sha256:" + "2" * 64})
    changed_payload = report.lock.model_copy(
        update={"nodes": (changed_node, *report.lock.nodes[1:])}
    )
    codes = {issue.code for issue in verify_dependency_lock(changed_payload, [*manifests, higher])}
    assert ErrorCode.LOCK_DIGEST_MISMATCH in codes
    assert ErrorCode.LOCK_CONTENT_MISMATCH in codes


def test_error_order_is_identical_when_candidates_are_reversed() -> None:
    manifests = graph()
    root = by_id(manifests, ROOT_REF.package_id)
    root = root.model_copy(update={"required_domain_capabilities": ("domain.unavailable",)})
    manifests = replace(manifests, root)
    first = resolve(manifests)
    second = resolve(list(reversed(manifests)))
    assert first.lock is second.lock is None
    assert first.issues == second.issues
