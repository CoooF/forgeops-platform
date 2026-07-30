from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from forgeops.platform_contracts.domain import Environment
from forgeops.platform_contracts.errors import ErrorCode, ForgeOpsError


class ActionAdapterKind(StrEnum):
    MOCK = "MOCK"
    DENY_ALL = "DENY_ALL"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FORGEOPS_", env_file=".env", extra="forbid", frozen=True
    )

    environment: Environment = Environment.DEV
    action_adapter: ActionAdapterKind = ActionAdapterKind.MOCK
    database_url: str = "sqlite+pysqlite:///./.local/forgeops.db"
    object_store_path: str = "./.local/objects"
    log_level: str = "INFO"
    external_model_enabled: bool = False
    real_data_enabled: bool = False
    runtime_plugins_enabled: bool = False
    local_synthetic_only: bool = True
    service_name: str = "forgeops-api"
    sdk_version: str = Field(default="0.1.0", pattern=r"^\d+\.\d+\.\d+$")
    temporal_address: str = "127.0.0.1:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "forgeops-platform-contracts-v1"

    @model_validator(mode="after")
    def enforce_safety_invariants(self) -> Settings:
        expected = (
            ActionAdapterKind.DENY_ALL
            if self.environment in {Environment.PREPROD, Environment.PROD}
            else ActionAdapterKind.MOCK
        )
        if self.action_adapter != expected:
            raise ValueError(f"{self.environment.value} must bind {expected.value} action adapter")
        if self.external_model_enabled:
            raise ValueError("external model providers are not approved")
        if self.real_data_enabled or not self.local_synthetic_only:
            raise ValueError("only local synthetic data is approved")
        if self.runtime_plugins_enabled:
            raise ValueError("runtime third-party plugins are not approved")
        if self.environment in {Environment.PREPROD, Environment.PROD} and not (
            self.database_url.startswith("postgresql+")
        ):
            raise ValueError("PREPROD/PROD configuration requires PostgreSQL")
        return self


def assert_release_adapter(environment: Environment, adapter: ActionAdapterKind) -> None:
    expected = (
        ActionAdapterKind.DENY_ALL
        if environment in {Environment.PREPROD, Environment.PROD}
        else ActionAdapterKind.MOCK
    )
    if adapter != expected:
        raise ForgeOpsError(
            ErrorCode.ENVIRONMENT_POLICY_VIOLATION,
            f"{environment.value} release must bind {expected.value}",
            details={"environment": environment.value, "requiredAdapter": expected.value},
            http_status=409,
        )
