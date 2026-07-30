from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, model_validator

from forgeops.platform_contracts.domain import StrictModel
from forgeops.platform_contracts.envelopes import ArtifactAttestation, ContractRef, ResourceBudget


class CompatibilityPolicy(StrEnum):
    BACKWARD = "BACKWARD"
    STRICT = "STRICT"


class UninstallMode(StrEnum):
    PRESERVE_HISTORY = "PRESERVE_HISTORY"


class MigrationKind(StrEnum):
    PACKAGE_PRIVATE_SCHEMA = "PACKAGE_PRIVATE_SCHEMA"
    CONTRACT_UPCASTER = "CONTRACT_UPCASTER"


class Declaration(StrictModel):
    ref: ContractRef
    title: str = Field(min_length=1, max_length=160)


class DomainSchema(Declaration):
    json_schema: dict[str, Any] = Field(alias="jsonSchema")
    compatibility: CompatibilityPolicy = CompatibilityPolicy.BACKWARD


class NodePack(Declaration):
    node_refs: tuple[str, ...] = Field(alias="nodeRefs")
    artifact: ArtifactAttestation | None = None


class WorkflowTemplate(Declaration):
    node_refs: tuple[str, ...] = Field(alias="nodeRefs")
    input_schema_ref: str = Field(alias="inputSchemaRef")
    output_schema_ref: str = Field(alias="outputSchemaRef")


class AgentProfilePack(Declaration):
    output_schema_ref: str = Field(alias="outputSchemaRef")
    deterministic_fallback_template: str = Field(
        alias="deterministicFallbackTemplate", min_length=1
    )
    external_model_required: Literal[False] = Field(default=False, alias="externalModelRequired")


class SkillPack(Declaration):
    skill_refs: tuple[str, ...] = Field(alias="skillRefs")
    artifact: ArtifactAttestation | None = None


class DataContractPack(Declaration):
    product_schema_refs: tuple[str, ...] = Field(alias="productSchemaRefs")
    synthetic_only: Literal[True] = Field(default=True, alias="syntheticOnly")


class SolverAdapter(Declaration):
    artifact: ArtifactAttestation
    problem_schema_ref: str = Field(alias="problemSchemaRef")
    result_schema_ref: str = Field(alias="resultSchemaRef")


class SimulationModel(Declaration):
    artifact: ArtifactAttestation
    input_schema_ref: str = Field(alias="inputSchemaRef")
    result_schema_ref: str = Field(alias="resultSchemaRef")


class EvaluationProfile(Declaration):
    metric_schema_ref: str = Field(alias="metricSchemaRef")
    hard_gate_refs: tuple[str, ...] = Field(alias="hardGateRefs")


class SyntheticDataset(Declaration):
    artifact: ArtifactAttestation
    classification: Literal["SYNTHETIC"] = "SYNTHETIC"
    business_validated: Literal[False] = Field(default=False, alias="businessValidated")


class GoldenTestCases(Declaration):
    artifact: ArtifactAttestation
    purpose: Literal["CONTRACT_ONLY"] = "CONTRACT_ONLY"
    business_validated: Literal[False] = Field(default=False, alias="businessValidated")


class UIComponentKind(StrEnum):
    FORM = "FORM"
    TABLE = "TABLE"
    METRIC_CARD = "METRIC_CARD"
    CHART = "CHART"
    GENERIC_SLOT = "GENERIC_SLOT"


class UIComponent(StrictModel):
    component_id: str = Field(alias="componentId", pattern=r"^[a-z][a-z0-9.-]+$")
    kind: UIComponentKind
    schema_ref: str = Field(alias="schemaRef")


class UIExtension(Declaration):
    route: str = Field(pattern=r"^/scenarios/[a-z0-9-]+(?:/[a-z0-9-]+)*$")
    navigation_label: str = Field(alias="navigationLabel", min_length=1)
    components: tuple[UIComponent, ...]
    runtime_script: Literal[None] = Field(default=None, alias="runtimeScript")


class PackageMigration(StrictModel):
    migration_id: str = Field(alias="migrationId", pattern=r"^[a-z0-9.-]+$")
    kind: MigrationKind
    from_version: str = Field(alias="fromVersion")
    to_version: str = Field(alias="toVersion")
    artifact: ArtifactAttestation


class UninstallPolicy(StrictModel):
    mode: UninstallMode = UninstallMode.PRESERVE_HISTORY
    retain_manifest: Literal[True] = Field(default=True, alias="retainManifest")
    retain_audit: Literal[True] = Field(default=True, alias="retainAudit")
    retain_historical_runs: Literal[True] = Field(default=True, alias="retainHistoricalRuns")


class ScenarioManifest(StrictModel):
    manifest_version: Literal["1.0.0"] = Field(alias="manifestVersion")
    package_id: str = Field(alias="packageId", pattern=r"^[a-z][a-z0-9-]{2,63}$", max_length=64)
    package_version: str = Field(alias="packageVersion", pattern=r"^\d+\.\d+\.\d+$")
    scenario_sdk: str = Field(alias="scenarioSdk", min_length=1)
    publisher: Literal["FIRST_PARTY_LOCAL"]
    artifact: ArtifactAttestation
    domain_schemas: tuple[DomainSchema, ...] = Field(alias="domainSchemas")
    node_packs: tuple[NodePack, ...] = Field(alias="nodePacks")
    workflow_templates: tuple[WorkflowTemplate, ...] = Field(alias="workflowTemplates")
    agent_profile_packs: tuple[AgentProfilePack, ...] = Field(alias="agentProfilePacks")
    skill_packs: tuple[SkillPack, ...] = Field(alias="skillPacks")
    data_contract_packs: tuple[DataContractPack, ...] = Field(alias="dataContractPacks")
    solver_adapters: tuple[SolverAdapter, ...] = Field(alias="solverAdapters")
    simulation_models: tuple[SimulationModel, ...] = Field(alias="simulationModels")
    evaluation_profiles: tuple[EvaluationProfile, ...] = Field(alias="evaluationProfiles")
    synthetic_datasets: tuple[SyntheticDataset, ...] = Field(alias="syntheticDatasets")
    golden_test_cases: tuple[GoldenTestCases, ...] = Field(alias="goldenTestCases")
    ui_extensions: tuple[UIExtension, ...] = Field(alias="uiExtensions")
    permissions: tuple[str, ...]
    resource_budget: ResourceBudget = Field(alias="resourceBudget")
    migrations: tuple[PackageMigration, ...]
    uninstall_policy: UninstallPolicy = Field(alias="uninstallPolicy")

    @model_validator(mode="after")
    def executable_artifacts_are_isolated(self) -> ScenarioManifest:
        artifacts: list[ArtifactAttestation] = [self.artifact]
        artifacts.extend(x.artifact for x in self.node_packs if x.artifact is not None)
        artifacts.extend(x.artifact for x in self.skill_packs if x.artifact is not None)
        artifacts.extend(x.artifact for x in self.solver_adapters)
        artifacts.extend(x.artifact for x in self.simulation_models)
        artifacts.extend(x.artifact for x in self.synthetic_datasets)
        artifacts.extend(x.artifact for x in self.golden_test_cases)
        artifacts.extend(x.artifact for x in self.migrations)
        for artifact in artifacts:
            if artifact.executable and artifact.worker_boundary != "isolated-worker":
                raise ValueError("executable artifacts require isolated-worker boundary")
        return self
