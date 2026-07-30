from __future__ import annotations

from typing import Any

from forgeops.fds_sdk.canonical import sha256_digest
from forgeops.fds_sdk.models import (
    Compatibility,
    CompatibilityReport,
    CompatibilityStatus,
    ContentClassification,
    FdsValidationIssue,
    LegacyAdaptationResult,
    LegacyManifestReference,
    LegacyScenarioSource,
    LicenseMetadata,
    LifecyclePolicy,
    PackageKind,
    Provenance,
    RequestedResourceBudget,
    ScenarioDescriptor,
    SupportStatus,
    TrustTier,
    Visibility,
)
from forgeops.fds_sdk.validation import sorted_issues
from forgeops.scenario_sdk.manifest import ScenarioManifest
from forgeops.scenario_sdk.validation import ManifestValidator

LEGACY_LIMITATIONS = (
    "LEGACY_SOURCE_HAS_NO_DECLARED_FDS_DOMAIN_CAPABILITY",
    "LEGACY_SOURCE_HAS_NO_VERIFIED_FDS_LICENSE",
    "LEGACY_SOURCE_HAS_NO_FDS_DEPENDENCY_LOCK",
    "LEGACY_SOURCE_HAS_NO_INPUT_OUTPUT_CONTENT_DIGEST",
    "LOCAL_DIGEST_ATTESTATION_IS_NOT_ENTERPRISE_SIGNATURE_VERIFICATION",
)


class LegacyScenarioAdapter:
    def adapt(
        self, raw_manifest: dict[str, Any], artifact_payload: bytes
    ) -> LegacyAdaptationResult:
        source_digest = sha256_digest(raw_manifest)
        validation = ManifestValidator().validate(raw_manifest, artifact_payload)
        if not validation.valid or validation.manifest is None:
            issues = sorted_issues(
                [
                    FdsValidationIssue(code=item.code, message=item.message, path=item.path)
                    for item in validation.issues
                ]
            )
            report = self._report(
                status=CompatibilityStatus.INCOMPATIBLE,
                source_manifest_digest=source_digest,
                descriptor_digest=None,
                manifest=None,
                issues=issues,
            )
            return LegacyAdaptationResult(descriptor=None, report=report)

        manifest = validation.manifest
        descriptor = self._descriptor(manifest, source_digest)
        descriptor_digest = sha256_digest(descriptor)
        report = self._report(
            status=CompatibilityStatus.COMPATIBLE_WITH_LIMITATIONS,
            source_manifest_digest=source_digest,
            descriptor_digest=descriptor_digest,
            manifest=manifest,
            issues=(),
        )
        return LegacyAdaptationResult(descriptor=descriptor, report=report)

    @staticmethod
    def _descriptor(manifest: ScenarioManifest, source_digest: str) -> ScenarioDescriptor:
        references: list[LegacyManifestReference] = []
        categories = (
            ("domainSchemas", manifest.domain_schemas),
            ("nodePacks", manifest.node_packs),
            ("workflowTemplates", manifest.workflow_templates),
            ("agentProfilePacks", manifest.agent_profile_packs),
            ("skillPacks", manifest.skill_packs),
            ("dataContractPacks", manifest.data_contract_packs),
            ("solverAdapters", manifest.solver_adapters),
            ("simulationModels", manifest.simulation_models),
            ("evaluationProfiles", manifest.evaluation_profiles),
            ("syntheticDatasets", manifest.synthetic_datasets),
            ("goldenTestCases", manifest.golden_test_cases),
            ("uiExtensions", manifest.ui_extensions),
        )
        for category, declarations in categories:
            for declaration in declarations:
                artifact = getattr(declaration, "artifact", None)
                references.append(
                    LegacyManifestReference(
                        category=category,
                        contract_id=declaration.ref.contract_id,
                        version=declaration.ref.version,
                        schema_ref=declaration.ref.schema_ref,
                        artifact_digest=(artifact.content_digest if artifact is not None else None),
                    )
                )
        legacy_source = LegacyScenarioSource(
            manifest_version=manifest.manifest_version,
            scenario_sdk=manifest.scenario_sdk,
            manifest_digest=source_digest,
            references=tuple(references),
            compatibility_limitations=LEGACY_LIMITATIONS,
        )
        return ScenarioDescriptor(
            api_version="forgeops.ai/fds/v1alpha1",
            kind=PackageKind.SCENARIO,
            package_id=manifest.package_id,
            package_version=manifest.package_version,
            publisher=manifest.publisher,
            namespace_owner=manifest.publisher,
            license=LicenseMetadata(
                license_id="UNSPECIFIED",
                license_ref=None,
                redistribution_allowed=False,
                derivative_work_allowed=False,
                verified=False,
            ),
            provenance=Provenance(
                source_ref=f"legacy-scenario-sdk://{manifest.package_id}/{manifest.package_version}",
                provenance_digest=source_digest,
                synthetic=True,
            ),
            visibility=Visibility.PRIVATE,
            trust_tier=TrustTier.FIRST_PARTY_LOCAL,
            content_classification=ContentClassification.SYNTHETIC,
            public_release_approved=False,
            content_digest=manifest.artifact.content_digest,
            artifact=manifest.artifact,
            compatibility=Compatibility(
                platform=">=0.1.0,<0.2.0",
                fds=">=0.1.0,<0.2.0",
                scenario_sdk=manifest.scenario_sdk,
            ),
            applicability=("LEGACY_CONTRACT_INPUT_ONLY",),
            prohibited_uses=("BUSINESS_DECISION", "REAL_DATA", "EXTERNAL_EXECUTION"),
            support_status=SupportStatus.EXPERIMENTAL,
            permissions=manifest.permissions,
            resource_budget=RequestedResourceBudget(
                cpu_millis=manifest.resource_budget.cpu_millis,
                memory_mib=manifest.resource_budget.memory_mib,
                timeout_seconds=manifest.resource_budget.timeout_seconds,
                max_output_bytes=manifest.resource_budget.max_output_bytes,
                network_access=manifest.resource_budget.network_access,
                secret_refs=manifest.resource_budget.secret_refs,
            ),
            accepted_dependency_permissions=(),
            dependency_resource_budget_allowance=RequestedResourceBudget(),
            lifecycle=LifecyclePolicy(),
            evaluation_refs=tuple(item.ref.contract_id for item in manifest.evaluation_profiles),
            dependencies=(),
            conflicts=(),
            provided_capabilities=(),
            provided_namespaces=(),
            required_domain_capabilities=(),
            components=(),
            input_contract_digest=None,
            output_contract_digest=None,
            legacy_source=legacy_source,
        )

    @staticmethod
    def _report(
        *,
        status: CompatibilityStatus,
        source_manifest_digest: str,
        descriptor_digest: str | None,
        manifest: ScenarioManifest | None,
        issues: tuple[Any, ...],
    ) -> CompatibilityReport:
        payload = {
            "reportVersion": "forgeops.ai/fds-compatibility/v1alpha1",
            "status": status,
            "sourcePackageId": manifest.package_id if manifest else None,
            "sourcePackageVersion": manifest.package_version if manifest else None,
            "sourceManifestDigest": source_manifest_digest,
            "descriptorDigest": descriptor_digest,
            "legacyScenarioSdk": manifest.scenario_sdk if manifest else None,
            "resolverReady": False,
            "historyMutated": False,
            "limitations": LEGACY_LIMITATIONS,
            "issues": issues,
        }
        return CompatibilityReport(**payload, report_digest=sha256_digest(payload))
