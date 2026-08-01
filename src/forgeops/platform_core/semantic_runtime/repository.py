from __future__ import annotations

from typing import Protocol
from uuid import UUID

from forgeops.platform_core.semantic_runtime.entities import (
    ContextManifestRecord,
    GroundingResultRecord,
    ImpactReportRecord,
    SemanticPayloadRecord,
)


class SemanticRuntimeRepository(Protocol):
    def find_idempotent_resource(
        self,
        actor_ref: str,
        operation: str,
        idempotency_key: str,
        request_digest: str,
    ) -> tuple[str, UUID] | None: ...

    def bind_idempotent_resource(
        self,
        actor_ref: str,
        operation: str,
        idempotency_key: str,
        request_digest: str,
        resource_type: str,
        resource_id: UUID,
    ) -> None: ...

    def add_semantic_payload(
        self,
        payload: SemanticPayloadRecord,
        *,
        actor_ref: str,
        idempotency_key: str,
        request_digest: str,
    ) -> SemanticPayloadRecord: ...

    def save_semantic_payload(
        self,
        payload: SemanticPayloadRecord,
        *,
        expected_version: int,
        actor_ref: str,
        operation: str,
        idempotency_key: str,
        request_digest: str,
    ) -> SemanticPayloadRecord: ...

    def get_semantic_payload(self, payload_id: UUID) -> SemanticPayloadRecord | None: ...

    def get_semantic_payload_for_package(
        self, package_version_id: UUID
    ) -> SemanticPayloadRecord | None: ...

    def list_semantic_payloads(self) -> tuple[SemanticPayloadRecord, ...]: ...

    def add_context_manifest(
        self,
        manifest: ContextManifestRecord,
        *,
        actor_ref: str,
        idempotency_key: str,
        request_digest: str,
    ) -> ContextManifestRecord: ...

    def get_context_manifest(self, manifest_id: UUID) -> ContextManifestRecord | None: ...

    def list_context_manifests(self, project_id: UUID) -> tuple[ContextManifestRecord, ...]: ...

    def add_grounding_result(
        self,
        result: GroundingResultRecord,
        *,
        actor_ref: str,
        idempotency_key: str,
        request_digest: str,
    ) -> GroundingResultRecord: ...

    def get_grounding_result(self, result_id: UUID) -> GroundingResultRecord | None: ...

    def add_impact_report(
        self,
        report: ImpactReportRecord,
        *,
        actor_ref: str,
        idempotency_key: str,
        request_digest: str,
    ) -> ImpactReportRecord: ...

    def get_impact_report(self, report_id: UUID) -> ImpactReportRecord | None: ...

    def list_impact_reports(self) -> tuple[ImpactReportRecord, ...]: ...
