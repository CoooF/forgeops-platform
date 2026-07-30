from __future__ import annotations

import pytest
from pydantic import ValidationError

from forgeops.config import ActionAdapterKind, Settings, assert_release_adapter
from forgeops.platform_contracts.domain import Environment
from forgeops.platform_contracts.errors import ErrorCode, ForgeOpsError


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
