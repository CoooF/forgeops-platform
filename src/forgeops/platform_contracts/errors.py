from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    MANIFEST_INVALID = "MANIFEST_INVALID"
    MANIFEST_MISSING_FIELD = "MANIFEST_MISSING_FIELD"
    UNKNOWN_PERMISSION = "UNKNOWN_PERMISSION"
    SDK_INCOMPATIBLE = "SDK_INCOMPATIBLE"
    SCHEMA_BREAKING_CHANGE = "SCHEMA_BREAKING_CHANGE"
    ARTIFACT_DIGEST_MISMATCH = "ARTIFACT_DIGEST_MISMATCH"
    ARTIFACT_SIGNATURE_INVALID = "ARTIFACT_SIGNATURE_INVALID"
    PACKAGE_VERSION_DIGEST_CONFLICT = "PACKAGE_VERSION_DIGEST_CONFLICT"
    ILLEGAL_STATE_TRANSITION = "ILLEGAL_STATE_TRANSITION"
    PERMISSION_GRANT_REQUIRED = "PERMISSION_GRANT_REQUIRED"
    BINDING_REQUIRED = "BINDING_REQUIRED"
    PACKAGE_NOT_ENABLED = "PACKAGE_NOT_ENABLED"
    PACKAGE_DISABLED = "PACKAGE_DISABLED"
    PACKAGE_REVOKED = "PACKAGE_REVOKED"
    PACKAGE_UNINSTALLED = "PACKAGE_UNINSTALLED"
    ENVIRONMENT_POLICY_VIOLATION = "ENVIRONMENT_POLICY_VIOLATION"
    ADAPTER_UNAVAILABLE = "ADAPTER_UNAVAILABLE"
    INPUT_INVALID = "INPUT_INVALID"
    DATA_INSUFFICIENT = "DATA_INSUFFICIENT"
    UNAUTHORIZED = "UNAUTHORIZED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    RESOURCE_LIMIT_EXCEEDED = "RESOURCE_LIMIT_EXCEEDED"
    INTERNAL_FAILURE = "INTERNAL_FAILURE"
    ACTION_EXECUTION_DENIED = "ACTION_EXECUTION_DENIED"


class ForgeOpsError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        http_status: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.http_status = http_status

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code.value, "message": self.message, "details": self.details}
