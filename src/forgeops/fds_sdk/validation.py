from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from pydantic import ValidationError

from forgeops.fds_sdk.canonical import canonical_json, sha256_digest
from forgeops.fds_sdk.models import (
    FDS_MANIFEST_ADAPTER,
    ComponentKind,
    ComponentManifest,
    ContentClassification,
    DomainManifest,
    FdsManifest,
    FdsValidationIssue,
    FdsValidationReport,
    OrganizationOverlayManifest,
    PackageKind,
    ScenarioDescriptor,
    TrustTier,
    Visibility,
)
from forgeops.platform_contracts.errors import ErrorCode
from forgeops.platform_contracts.package_permissions import (
    ALLOWED_PACKAGE_PERMISSIONS,
    FORBIDDEN_PACKAGE_CAPABILITIES,
)


def issue_sort_key(issue: FdsValidationIssue) -> tuple[str, str, str]:
    return issue.code.value, issue.path, issue.message


def sorted_issues(issues: list[FdsValidationIssue]) -> tuple[FdsValidationIssue, ...]:
    return tuple(sorted(issues, key=issue_sort_key))


def manifest_requirements(manifest: FdsManifest) -> tuple[Any, ...]:
    requirements = list(manifest.dependencies)
    if isinstance(manifest, DomainManifest):
        requirements.extend(
            _required_reference(reference, PackageKind.DOMAIN) for reference in manifest.extends
        )
        requirements.extend(_required_reference(reference) for reference in manifest.imports)
        requirements.extend(_component_requirement(reference) for reference in manifest.components)
    elif isinstance(manifest, (OrganizationOverlayManifest, ScenarioDescriptor)):
        requirements.extend(_component_requirement(reference) for reference in manifest.components)
    unique = {canonical_json(requirement): requirement for requirement in requirements}
    return tuple(unique[key] for key in sorted(unique))


def _required_reference(reference: Any, expected_kind: PackageKind | None = None) -> Any:
    from forgeops.fds_sdk.models import DependencyRequirement

    package = reference
    if expected_kind is not None and reference.expected_kind is None:
        package = reference.model_copy(update={"expected_kind": expected_kind})
    return DependencyRequirement(package=package, required=True)


def _component_requirement(reference: Any) -> Any:
    from forgeops.fds_sdk.models import DependencyRequirement

    package = reference.package
    if package.expected_kind is None:
        package = package.model_copy(update={"expected_kind": PackageKind.COMPONENT})
    return DependencyRequirement(
        package=package,
        required=True,
        expected_component_kind=reference.component_kind,
    )


class FdsManifestValidator:
    def validate(self, raw_manifest: dict[str, Any]) -> FdsValidationReport:
        kind = raw_manifest.get("kind")
        if kind not in {item.value for item in PackageKind}:
            issue = FdsValidationIssue(
                code=ErrorCode.UNKNOWN_PACKAGE_KIND,
                message=f"unknown FDS package kind: {kind!r}",
                path="$.kind",
            )
            return FdsValidationReport(valid=False, issues=(issue,))
        if kind == PackageKind.COMPONENT.value:
            component_kind = raw_manifest.get("componentKind")
            if component_kind not in {item.value for item in ComponentKind}:
                issue = FdsValidationIssue(
                    code=ErrorCode.UNKNOWN_COMPONENT_KIND,
                    message=f"unknown FDS component kind: {component_kind!r}",
                    path="$.componentKind",
                )
                return FdsValidationReport(valid=False, issues=(issue,))
        try:
            manifest = FDS_MANIFEST_ADAPTER.validate_python(raw_manifest)
        except ValidationError as exc:
            parse_issues = [self._pydantic_issue(error) for error in exc.errors()]
            return FdsValidationReport(valid=False, issues=sorted_issues(parse_issues))

        model_issues = self.validate_model(manifest)
        if model_issues:
            return FdsValidationReport(valid=False, issues=model_issues)
        normalized = canonical_json(manifest)
        return FdsValidationReport(
            valid=True,
            manifest=manifest,
            normalized_manifest=normalized,
            manifest_digest=sha256_digest(manifest),
        )

    def validate_model(self, manifest: FdsManifest) -> tuple[FdsValidationIssue, ...]:
        issues: list[FdsValidationIssue] = []
        issues.extend(self._version_constraints(manifest))
        unknown_permissions = (
            set(manifest.permissions) | set(manifest.accepted_dependency_permissions)
        ) - ALLOWED_PACKAGE_PERMISSIONS
        unknown_permissions |= set(manifest.permissions) & FORBIDDEN_PACKAGE_CAPABILITIES
        issues.extend(
            FdsValidationIssue(
                code=ErrorCode.UNKNOWN_PERMISSION,
                message=(
                    f"permission is not in the local package permission dictionary: {permission}"
                ),
                path="$.permissions",
            )
            for permission in sorted(unknown_permissions)
        )
        if manifest.content_digest != manifest.artifact.content_digest:
            issues.append(
                FdsValidationIssue(
                    code=ErrorCode.ARTIFACT_DIGEST_MISMATCH,
                    message="package contentDigest must equal artifact.contentDigest",
                    path="$.contentDigest",
                )
            )
        if manifest.trust_tier == TrustTier.FIRST_PARTY_LOCAL:
            expected = f"local-sha256:{manifest.content_digest.removeprefix('sha256:')}"
            if manifest.artifact.signature != expected:
                issues.append(
                    FdsValidationIssue(
                        code=ErrorCode.ARTIFACT_SIGNATURE_INVALID,
                        message="FIRST_PARTY_LOCAL attestation must match contentDigest",
                        path="$.artifact.signature",
                    )
                )
        if manifest.artifact.executable and manifest.artifact.worker_boundary != "isolated-worker":
            issues.append(
                FdsValidationIssue(
                    code=ErrorCode.EXECUTABLE_BOUNDARY_REQUIRED,
                    message="executable FDS artifacts require isolated-worker boundary",
                    path="$.artifact.workerBoundary",
                )
            )
        if (
            manifest.visibility == Visibility.PUBLIC
            and manifest.content_classification == ContentClassification.ORGANIZATION_PRIVATE
            and not manifest.public_release_approved
        ):
            issues.append(
                FdsValidationIssue(
                    code=ErrorCode.PRIVATE_CONTENT_PUBLICATION_DENIED,
                    message="organization-private content is not approved for public release",
                    path="$.visibility",
                )
            )
        if isinstance(manifest, OrganizationOverlayManifest):
            if manifest.visibility != Visibility.ORGANIZATION_PRIVATE:
                issues.append(
                    FdsValidationIssue(
                        code=ErrorCode.VISIBILITY_VIOLATION,
                        message="organization overlays must be ORGANIZATION_PRIVATE",
                        path="$.visibility",
                    )
                )
            if not manifest.overrides_domain_capabilities:
                issues.append(
                    FdsValidationIssue(
                        code=ErrorCode.OVERLAY_TARGET_MISSING,
                        message="organization overlay must name a domain capability to override",
                        path="$.overridesDomainCapabilities",
                    )
                )
        if isinstance(manifest, DomainManifest) and not manifest.competency_question_refs:
            issues.append(
                FdsValidationIssue(
                    code=ErrorCode.MANIFEST_INVALID,
                    message="domain manifest requires competencyQuestionRefs",
                    path="$.competencyQuestionRefs",
                )
            )
        if isinstance(manifest, ScenarioDescriptor) and manifest.legacy_source is None:
            if not manifest.required_domain_capabilities:
                issues.append(
                    FdsValidationIssue(
                        code=ErrorCode.SCENARIO_DOMAIN_CAPABILITY_MISSING,
                        message="native scenario requires at least one domain capability",
                        path="$.requiredDomainCapabilities",
                    )
                )
            if manifest.input_contract_digest is None or manifest.output_contract_digest is None:
                issues.append(
                    FdsValidationIssue(
                        code=ErrorCode.MANIFEST_INVALID,
                        message="native scenario requires input and output contract digests",
                        path="$.inputContractDigest",
                    )
                )
        if isinstance(manifest, ComponentManifest):
            if manifest.artifact.executable and manifest.runtime_form.value != "ISOLATED_WORKER":
                issues.append(
                    FdsValidationIssue(
                        code=ErrorCode.EXECUTABLE_BOUNDARY_REQUIRED,
                        message="executable components require ISOLATED_WORKER runtimeForm",
                        path="$.runtimeForm",
                    )
                )
        return sorted_issues(issues)

    @staticmethod
    def _pydantic_issue(error: Mapping[str, Any]) -> FdsValidationIssue:
        package_kind_values = {item.value for item in PackageKind}
        location_parts = [part for part in error["loc"] if str(part) not in package_kind_values]
        location = ".".join(str(part) for part in location_parts)
        code = (
            ErrorCode.MANIFEST_MISSING_FIELD
            if error["type"] == "missing"
            else ErrorCode.MANIFEST_INVALID
        )
        return FdsValidationIssue(code=code, message=error["msg"], path=f"$.{location}")

    @staticmethod
    def _version_constraints(manifest: FdsManifest) -> list[FdsValidationIssue]:
        values = {
            "$.compatibility.platform": manifest.compatibility.platform,
            "$.compatibility.fds": manifest.compatibility.fds,
            "$.compatibility.scenarioSdk": manifest.compatibility.scenario_sdk,
        }
        for index, requirement in enumerate(manifest_requirements(manifest)):
            values[f"$.dependencies[{index}].package.versionConstraint"] = (
                requirement.package.version_constraint
            )
        for index, conflict in enumerate(manifest.conflicts):
            if conflict.version_constraint is not None:
                values[f"$.conflicts[{index}].versionConstraint"] = conflict.version_constraint
        issues: list[FdsValidationIssue] = []
        for path, value in values.items():
            try:
                SpecifierSet(value)
            except InvalidSpecifier:
                issues.append(
                    FdsValidationIssue(
                        code=ErrorCode.MANIFEST_INVALID,
                        message=f"invalid PEP 440 version constraint: {value!r}",
                        path=path,
                    )
                )
        return issues
