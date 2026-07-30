from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version
from pydantic import ValidationError

from forgeops.platform_contracts.domain import StrictModel
from forgeops.platform_contracts.errors import ErrorCode
from forgeops.scenario_sdk.manifest import CompatibilityPolicy, ScenarioManifest
from forgeops.scenario_sdk.permissions import (
    ALLOWED_SCENARIO_PERMISSIONS,
    FORBIDDEN_WORKER_CAPABILITIES,
)
from forgeops.scenario_sdk.schema_compatibility import find_breaking_schema_changes

CURRENT_SDK_VERSION = Version("0.1.0")


class ValidationIssue(StrictModel):
    code: ErrorCode
    message: str
    path: str = "$"


class ValidationReport(StrictModel):
    valid: bool
    manifest: ScenarioManifest | None = None
    issues: tuple[ValidationIssue, ...] = ()


class ManifestValidator:
    def validate(
        self,
        raw_manifest: dict[str, Any],
        artifact_payload: bytes,
        *,
        previous_manifest: ScenarioManifest | None = None,
    ) -> ValidationReport:
        try:
            manifest = ScenarioManifest.model_validate(raw_manifest)
        except ValidationError as exc:
            parse_issues = tuple(self._pydantic_issue(item) for item in exc.errors())
            return ValidationReport(valid=False, issues=parse_issues)

        validation_issues: list[ValidationIssue] = []
        validation_issues.extend(self._check_sdk(manifest))
        validation_issues.extend(self._check_permissions(manifest))
        validation_issues.extend(self._check_artifact(manifest, artifact_payload))
        validation_issues.extend(self._check_schemas(manifest, previous_manifest))
        return ValidationReport(
            valid=not validation_issues,
            manifest=manifest if not validation_issues else None,
            issues=tuple(validation_issues),
        )

    @staticmethod
    def _pydantic_issue(error: Mapping[str, Any]) -> ValidationIssue:
        location = ".".join(str(part) for part in error["loc"])
        code = (
            ErrorCode.MANIFEST_MISSING_FIELD
            if error["type"] == "missing"
            else ErrorCode.MANIFEST_INVALID
        )
        return ValidationIssue(code=code, message=error["msg"], path=f"$.{location}")

    @staticmethod
    def _check_sdk(manifest: ScenarioManifest) -> list[ValidationIssue]:
        try:
            compatible = CURRENT_SDK_VERSION in SpecifierSet(manifest.scenario_sdk)
        except InvalidSpecifier:
            compatible = False
        if compatible:
            return []
        return [
            ValidationIssue(
                code=ErrorCode.SDK_INCOMPATIBLE,
                message=(
                    f"package range {manifest.scenario_sdk!r} does not include SDK "
                    f"{CURRENT_SDK_VERSION}"
                ),
                path="$.scenarioSdk",
            )
        ]

    @staticmethod
    def _check_permissions(manifest: ScenarioManifest) -> list[ValidationIssue]:
        unknown = set(manifest.permissions) - ALLOWED_SCENARIO_PERMISSIONS
        forbidden = set(manifest.permissions) & FORBIDDEN_WORKER_CAPABILITIES
        issues = [
            ValidationIssue(
                code=ErrorCode.UNKNOWN_PERMISSION,
                message=f"permission is not allowed: {permission}",
                path="$.permissions",
            )
            for permission in sorted(unknown | forbidden)
        ]
        if manifest.resource_budget.network_access:
            issues.append(
                ValidationIssue(
                    code=ErrorCode.UNKNOWN_PERMISSION,
                    message="scenario workers cannot request network access in local baseline",
                    path="$.resourceBudget.networkAccess",
                )
            )
        if manifest.resource_budget.secret_refs:
            issues.append(
                ValidationIssue(
                    code=ErrorCode.UNKNOWN_PERMISSION,
                    message="scenario workers cannot request Secret access in local baseline",
                    path="$.resourceBudget.secretRefs",
                )
            )
        return issues

    @staticmethod
    def _check_artifact(
        manifest: ScenarioManifest, artifact_payload: bytes
    ) -> list[ValidationIssue]:
        actual = f"sha256:{hashlib.sha256(artifact_payload).hexdigest()}"
        declared = manifest.artifact.content_digest
        if actual != declared:
            return [
                ValidationIssue(
                    code=ErrorCode.ARTIFACT_DIGEST_MISMATCH,
                    message=f"declared {declared}; calculated {actual}",
                    path="$.artifact.contentDigest",
                )
            ]
        expected_signature = f"local-sha256:{actual.removeprefix('sha256:')}"
        if manifest.artifact.signature != expected_signature:
            return [
                ValidationIssue(
                    code=ErrorCode.ARTIFACT_SIGNATURE_INVALID,
                    message="local digest attestation does not match the artifact digest",
                    path="$.artifact.signature",
                )
            ]
        return []

    @staticmethod
    def _check_schemas(
        manifest: ScenarioManifest, previous_manifest: ScenarioManifest | None
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        previous_by_id = (
            {item.ref.contract_id: item for item in previous_manifest.domain_schemas}
            if previous_manifest
            else {}
        )
        for index, domain_schema in enumerate(manifest.domain_schemas):
            path = f"$.domainSchemas[{index}].jsonSchema"
            try:
                Draft202012Validator.check_schema(domain_schema.json_schema)
            except SchemaError as exc:
                issues.append(
                    ValidationIssue(
                        code=ErrorCode.MANIFEST_INVALID,
                        message=f"invalid JSON Schema: {exc.message}",
                        path=path,
                    )
                )
                continue
            previous = previous_by_id.get(domain_schema.ref.contract_id)
            if previous and domain_schema.compatibility == CompatibilityPolicy.BACKWARD:
                breaking = find_breaking_schema_changes(
                    previous.json_schema, domain_schema.json_schema
                )
                issues.extend(
                    ValidationIssue(
                        code=ErrorCode.SCHEMA_BREAKING_CHANGE,
                        message=message,
                        path=path,
                    )
                    for message in breaking
                )
        return issues
