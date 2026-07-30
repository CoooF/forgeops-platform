from __future__ import annotations

from typing import Any

import pytest

from forgeops.config import ActionAdapterKind
from forgeops.platform_contracts.domain import Environment, PackageLifecycleState
from forgeops.platform_contracts.errors import ErrorCode, ForgeOpsError
from forgeops.platform_core.audit import InMemoryAuditRepository
from forgeops.platform_core.scenario_registry.repository import InMemoryInstallationRepository
from forgeops.platform_core.scenario_registry.service import ScenarioPackageService


def service() -> tuple[ScenarioPackageService, InMemoryInstallationRepository]:
    repository = InMemoryInstallationRepository()
    return ScenarioPackageService(repository, InMemoryAuditRepository()), repository


def install_valid(service: ScenarioPackageService, load_fixture: Any) -> Any:
    manifest, artifact = load_fixture("steel-cord-scheduling")
    return service.install(manifest, artifact, actor_ref="local-owner", trace_id="trace-0001")


def test_repeated_install_is_idempotent(load_fixture: Any) -> None:
    package_service, repository = service()
    first = install_valid(package_service, load_fixture)
    second = install_valid(package_service, load_fixture)
    assert first.installation_id == second.installation_id
    assert len(repository.list_installations()) == 1


def test_install_does_not_grant_bind_release_or_enable(load_fixture: Any) -> None:
    package_service, _ = service()
    record = install_valid(package_service, load_fixture)
    assert record.state == PackageLifecycleState.INSTALLED_DISABLED
    assert record.granted_permissions == ()
    assert record.binding_refs == ()
    with pytest.raises(ForgeOpsError) as captured:
        package_service.assert_new_run_allowed(record.installation_id, Environment.TEST)
    assert captured.value.code == ErrorCode.PACKAGE_NOT_ENABLED


def test_full_local_lifecycle_requires_all_distinct_steps(load_fixture: Any) -> None:
    package_service, repository = service()
    installed = install_valid(package_service, load_fixture)
    tested = package_service.mark_tested(
        installed.installation_id, actor_ref="tester", trace_id="trace-0002"
    )
    assert tested.state == PackageLifecycleState.TESTED
    approved = package_service.approve(
        installed.installation_id, actor_ref="approver", trace_id="trace-0003"
    )
    assert approved.state == PackageLifecycleState.APPROVED

    with pytest.raises(ForgeOpsError) as permission_error:
        package_service.release(
            installed.installation_id,
            Environment.TEST,
            ActionAdapterKind.MOCK,
            actor_ref="releaser",
            trace_id="trace-0004",
        )
    assert permission_error.value.code == ErrorCode.PERMISSION_GRANT_REQUIRED

    package_service.grant_permissions(
        installed.installation_id,
        approved.manifest.permissions,
        actor_ref="permission-owner",
        trace_id="trace-0005",
    )
    with pytest.raises(ForgeOpsError) as binding_error:
        package_service.release(
            installed.installation_id,
            Environment.TEST,
            ActionAdapterKind.MOCK,
            actor_ref="releaser",
            trace_id="trace-0006",
        )
    assert binding_error.value.code == ErrorCode.BINDING_REQUIRED

    package_service.bind(
        installed.installation_id,
        "binding://local-contract-worker",
        actor_ref="binding-owner",
        trace_id="trace-0007",
    )
    package_service.release(
        installed.installation_id,
        Environment.TEST,
        ActionAdapterKind.MOCK,
        actor_ref="releaser",
        trace_id="trace-0008",
    )
    release = package_service.enable(
        installed.installation_id,
        Environment.TEST,
        actor_ref="environment-owner",
        trace_id="trace-0009",
    )
    assert release.state.value == "ENABLED"
    package_service.assert_new_run_allowed(installed.installation_id, Environment.TEST)
    assert repository.get_by_id(installed.installation_id) is not None


def test_prod_cannot_bind_mock_adapter(load_fixture: Any) -> None:
    package_service, _ = service()
    record = install_valid(package_service, load_fixture)
    package_service.mark_tested(record.installation_id, actor_ref="t", trace_id="trace-0001")
    approved = package_service.approve(record.installation_id, actor_ref="a", trace_id="trace-0002")
    package_service.grant_permissions(
        record.installation_id,
        approved.manifest.permissions,
        actor_ref="p",
        trace_id="trace-0003",
    )
    package_service.bind(
        record.installation_id, "binding://one", actor_ref="b", trace_id="trace-0004"
    )
    with pytest.raises(ForgeOpsError) as captured:
        package_service.release(
            record.installation_id,
            Environment.PROD,
            ActionAdapterKind.MOCK,
            actor_ref="r",
            trace_id="trace-0005",
        )
    assert captured.value.code == ErrorCode.ENVIRONMENT_POLICY_VIOLATION


def test_disable_blocks_new_run_but_preserves_metadata(load_fixture: Any) -> None:
    package_service, repository = service()
    record = install_valid(package_service, load_fixture)
    package_service.mark_tested(record.installation_id, actor_ref="t", trace_id="trace-0001")
    approved = package_service.approve(record.installation_id, actor_ref="a", trace_id="trace-0002")
    package_service.grant_permissions(
        record.installation_id,
        approved.manifest.permissions,
        actor_ref="p",
        trace_id="trace-0003",
    )
    package_service.bind(
        record.installation_id, "binding://one", actor_ref="b", trace_id="trace-0004"
    )
    package_service.release(
        record.installation_id,
        Environment.TEST,
        ActionAdapterKind.MOCK,
        actor_ref="r",
        trace_id="trace-0005",
    )
    package_service.enable(
        record.installation_id, Environment.TEST, actor_ref="e", trace_id="trace-0006"
    )
    package_service.disable(
        record.installation_id, Environment.TEST, actor_ref="d", trace_id="trace-0007"
    )
    with pytest.raises(ForgeOpsError) as captured:
        package_service.assert_new_run_allowed(record.installation_id, Environment.TEST)
    assert captured.value.code == ErrorCode.PACKAGE_DISABLED
    historical = repository.get_by_id(record.installation_id)
    assert historical is not None
    assert historical.manifest.package_id == "steel-cord-scheduling"


def test_revoke_blocks_new_run_but_preserves_metadata(load_fixture: Any) -> None:
    package_service, repository = service()
    record = install_valid(package_service, load_fixture)
    package_service.mark_tested(record.installation_id, actor_ref="t", trace_id="trace-0001")
    approved = package_service.approve(record.installation_id, actor_ref="a", trace_id="trace-0002")
    package_service.grant_permissions(
        record.installation_id,
        approved.manifest.permissions,
        actor_ref="p",
        trace_id="trace-0003",
    )
    package_service.bind(
        record.installation_id, "binding://one", actor_ref="b", trace_id="trace-0004"
    )
    package_service.release(
        record.installation_id,
        Environment.TEST,
        ActionAdapterKind.MOCK,
        actor_ref="r",
        trace_id="trace-0005",
    )
    package_service.revoke(
        record.installation_id, Environment.TEST, actor_ref="security", trace_id="trace-0006"
    )

    with pytest.raises(ForgeOpsError) as captured:
        package_service.assert_new_run_allowed(record.installation_id, Environment.TEST)
    assert captured.value.code == ErrorCode.PACKAGE_REVOKED
    historical = repository.get_by_id(record.installation_id)
    assert historical is not None
    assert historical.manifest.package_id == "steel-cord-scheduling"


def test_logical_uninstall_requires_disable_and_preserves_history(load_fixture: Any) -> None:
    package_service, repository = service()
    record = install_valid(package_service, load_fixture)
    with pytest.raises(ForgeOpsError) as transition_error:
        package_service.uninstall(
            record.installation_id, actor_ref="operator", trace_id="trace-0001"
        )
    assert transition_error.value.code == ErrorCode.ILLEGAL_STATE_TRANSITION

    package_service.mark_tested(record.installation_id, actor_ref="t", trace_id="trace-0002")
    approved = package_service.approve(record.installation_id, actor_ref="a", trace_id="trace-0003")
    package_service.grant_permissions(
        record.installation_id,
        approved.manifest.permissions,
        actor_ref="p",
        trace_id="trace-0004",
    )
    package_service.bind(
        record.installation_id, "binding://one", actor_ref="b", trace_id="trace-0005"
    )
    package_service.release(
        record.installation_id,
        Environment.TEST,
        ActionAdapterKind.MOCK,
        actor_ref="r",
        trace_id="trace-0006",
    )
    package_service.disable(
        record.installation_id, Environment.TEST, actor_ref="d", trace_id="trace-0007"
    )
    uninstalled = package_service.uninstall(
        record.installation_id, actor_ref="operator", trace_id="trace-0008"
    )

    assert uninstalled.uninstalled_at is not None
    assert uninstalled.granted_permissions == ()
    assert uninstalled.binding_refs == ()
    assert uninstalled.manifest.uninstall_policy.retain_manifest is True
    assert repository.get_by_id(record.installation_id) is not None
    with pytest.raises(ForgeOpsError) as run_error:
        package_service.assert_new_run_allowed(record.installation_id, Environment.TEST)
    assert run_error.value.code == ErrorCode.PACKAGE_UNINSTALLED
    with pytest.raises(ForgeOpsError) as bind_error:
        package_service.bind(
            record.installation_id,
            "binding://after-uninstall",
            actor_ref="operator",
            trace_id="trace-0009",
        )
    assert bind_error.value.code == ErrorCode.PACKAGE_UNINSTALLED
    assert (
        package_service.uninstall(
            record.installation_id, actor_ref="operator", trace_id="trace-0010"
        ).uninstalled_at
        == uninstalled.uninstalled_at
    )
