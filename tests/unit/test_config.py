from __future__ import annotations

import pytest
from pydantic import ValidationError

from forgeops.config import ActionAdapterKind, Settings, assert_release_adapter
from forgeops.platform_contracts.domain import Environment
from forgeops.platform_contracts.errors import ErrorCode, ForgeOpsError
from forgeops.platform_core.identity_access.auth import auth_adapter_for_environment


def test_prod_requires_deny_all_and_postgres() -> None:
    settings = Settings(
        environment=Environment.PROD,
        action_adapter=ActionAdapterKind.DENY_ALL,
        database_url="postgresql+psycopg://local-placeholder/forgeops",
    )
    assert settings.action_adapter == ActionAdapterKind.DENY_ALL


@pytest.mark.parametrize("environment", [Environment.DEV, Environment.TEST, Environment.INT])
def test_local_engineering_environments_require_mock(environment: Environment) -> None:
    settings = Settings(environment=environment, action_adapter=ActionAdapterKind.MOCK)
    assert settings.environment == environment
    with pytest.raises(ValidationError, match="must bind MOCK"):
        Settings(environment=environment, action_adapter=ActionAdapterKind.DENY_ALL)


@pytest.mark.parametrize("environment", [Environment.PREPROD, Environment.PROD])
def test_high_environments_reject_mock(environment: Environment) -> None:
    with pytest.raises(ValidationError, match="must bind DENY_ALL"):
        Settings(
            environment=environment,
            action_adapter=ActionAdapterKind.MOCK,
            database_url="postgresql+psycopg://local-placeholder/forgeops",
        )


@pytest.mark.parametrize("environment", [Environment.PREPROD, Environment.PROD])
def test_high_environments_reject_local_sqlite(environment: Environment) -> None:
    with pytest.raises(ValidationError, match="requires PostgreSQL"):
        Settings(environment=environment, action_adapter=ActionAdapterKind.DENY_ALL)


def test_unapproved_model_real_data_and_plugins_fail_startup() -> None:
    for field in ("external_model_enabled", "real_data_enabled", "runtime_plugins_enabled"):
        with pytest.raises(ValidationError):
            Settings(**{field: True})


def test_prod_release_policy_is_not_a_feature_flag() -> None:
    with pytest.raises(ForgeOpsError) as captured:
        assert_release_adapter(Environment.PROD, ActionAdapterKind.MOCK)
    assert captured.value.code == ErrorCode.ENVIRONMENT_POLICY_VIOLATION


@pytest.mark.parametrize("environment", [Environment.DEV, Environment.TEST])
def test_local_header_auth_is_limited_to_local_test_modes(environment: Environment) -> None:
    resolved = auth_adapter_for_environment(environment).authenticate("local-owner")
    assert resolved is not None
    assert resolved.subject_ref == "local-owner"


@pytest.mark.parametrize("environment", [Environment.INT, Environment.PREPROD, Environment.PROD])
def test_unconnected_enterprise_identity_fails_closed(environment: Environment) -> None:
    assert auth_adapter_for_environment(environment).authenticate("local-owner") is None
