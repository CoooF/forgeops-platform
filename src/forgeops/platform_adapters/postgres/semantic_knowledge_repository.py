from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from forgeops.platform_adapters.postgres.models import (
    ContextManifestRow,
    GroundingResultRow,
    KnowledgeAssetRow,
    KnowledgeAssetVersionRow,
    SemanticIdempotencyRecordRow,
    SemanticImpactReportRow,
    SemanticPayloadRow,
)
from forgeops.platform_contracts.errors import ErrorCode, ForgeOpsError
from forgeops.platform_core.knowledge_hub.entities import KnowledgeAsset, KnowledgeAssetVersion
from forgeops.platform_core.semantic_runtime.entities import (
    AssetLifecycle,
    ContextManifestRecord,
    GroundingResultRecord,
    ImpactReportRecord,
    SemanticPayloadDefinition,
    SemanticPayloadKind,
    SemanticPayloadRecord,
)


class SqlSemanticKnowledgeRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def find_idempotent_resource(
        self,
        actor_ref: str,
        operation: str,
        idempotency_key: str,
        request_digest: str,
    ) -> tuple[str, UUID] | None:
        with self._session_factory() as session:
            replay = self._find_replay(
                session, actor_ref, operation, idempotency_key, request_digest
            )
            return (replay.resource_type, replay.resource_id) if replay is not None else None

    def bind_idempotent_resource(
        self,
        actor_ref: str,
        operation: str,
        idempotency_key: str,
        request_digest: str,
        resource_type: str,
        resource_id: UUID,
    ) -> None:
        with self._session_factory() as session, session.begin():
            replay = self._find_replay(
                session, actor_ref, operation, idempotency_key, request_digest
            )
            if replay is not None:
                if replay.resource_type != resource_type or replay.resource_id != resource_id:
                    raise self._idempotency_corrupt()
                return
            self._add_idempotency(
                session,
                actor_ref,
                operation,
                idempotency_key,
                request_digest,
                resource_type,
                resource_id,
            )
            self._flush(session)

    def add_semantic_payload(
        self,
        payload: SemanticPayloadRecord,
        *,
        actor_ref: str,
        idempotency_key: str,
        request_digest: str,
    ) -> SemanticPayloadRecord:
        with self._session_factory() as session, session.begin():
            replay = self._find_replay(
                session, actor_ref, "semantic-payload.register", idempotency_key, request_digest
            )
            if replay is not None:
                existing = self._semantic_payload(
                    session.get(SemanticPayloadRow, replay.resource_id)
                )
                if existing is None:
                    raise self._idempotency_corrupt()
                return existing
            session.add(self._semantic_payload_row(payload))
            self._add_idempotency(
                session,
                actor_ref,
                "semantic-payload.register",
                idempotency_key,
                request_digest,
                "SEMANTIC_PAYLOAD",
                payload.semantic_payload_id,
            )
            self._flush(session, ErrorCode.SEMANTIC_PAYLOAD_DIGEST_CONFLICT)
        return payload

    def save_semantic_payload(
        self,
        payload: SemanticPayloadRecord,
        *,
        expected_version: int,
        actor_ref: str,
        operation: str,
        idempotency_key: str,
        request_digest: str,
    ) -> SemanticPayloadRecord:
        with self._session_factory() as session, session.begin():
            replay = self._find_replay(
                session, actor_ref, operation, idempotency_key, request_digest
            )
            if replay is not None:
                existing = self._semantic_payload(
                    session.get(SemanticPayloadRow, replay.resource_id)
                )
                if existing is None:
                    raise self._idempotency_corrupt()
                return existing
            row = session.scalar(
                select(SemanticPayloadRow)
                .where(SemanticPayloadRow.semantic_payload_id == payload.semantic_payload_id)
                .with_for_update()
            )
            if row is None or row.version != expected_version:
                raise self._concurrency_conflict(expected_version)
            row.status = payload.status.value
            row.governance_reason = payload.governance_reason
            row.governed_at = payload.governed_at
            row.updated_at = payload.updated_at
            row.version = expected_version + 1
            self._add_idempotency(
                session,
                actor_ref,
                operation,
                idempotency_key,
                request_digest,
                "SEMANTIC_PAYLOAD",
                payload.semantic_payload_id,
            )
            self._flush(session)
        return payload.model_copy(update={"version": expected_version + 1})

    def get_semantic_payload(self, payload_id: UUID) -> SemanticPayloadRecord | None:
        with self._session_factory() as session:
            return self._semantic_payload(session.get(SemanticPayloadRow, payload_id))

    def get_semantic_payload_for_package(
        self, package_version_id: UUID
    ) -> SemanticPayloadRecord | None:
        with self._session_factory() as session:
            row = session.scalar(
                select(SemanticPayloadRow).where(
                    SemanticPayloadRow.package_version_id == package_version_id
                )
            )
            return self._semantic_payload(row)

    def list_semantic_payloads(self) -> tuple[SemanticPayloadRecord, ...]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(SemanticPayloadRow).order_by(
                    SemanticPayloadRow.package_id, SemanticPayloadRow.package_version
                )
            )
            return tuple(self._required_semantic_payload(row) for row in rows)

    def add_knowledge_asset(
        self,
        asset: KnowledgeAsset,
        *,
        actor_ref: str,
        idempotency_key: str,
        request_digest: str,
    ) -> KnowledgeAsset:
        with self._session_factory() as session, session.begin():
            replay = self._find_replay(
                session, actor_ref, "knowledge-asset.create", idempotency_key, request_digest
            )
            if replay is not None:
                existing = self._knowledge_asset(session.get(KnowledgeAssetRow, replay.resource_id))
                if existing is None:
                    raise self._idempotency_corrupt()
                return existing
            session.add(
                KnowledgeAssetRow(
                    asset_id=asset.asset_id,
                    organization_id=asset.organization_id,
                    title=asset.title,
                    description=asset.description,
                    asset_type=asset.asset_type.value,
                    language=asset.language,
                    owner=asset.owner,
                    reviewer=asset.reviewer,
                    created_by=asset.created_by,
                    created_at=asset.created_at,
                    version=asset.version,
                )
            )
            self._add_idempotency(
                session,
                actor_ref,
                "knowledge-asset.create",
                idempotency_key,
                request_digest,
                "KNOWLEDGE_ASSET",
                asset.asset_id,
            )
            self._flush(session, ErrorCode.KNOWLEDGE_ASSET_INVALID)
        return asset

    def get_knowledge_asset(self, asset_id: UUID) -> KnowledgeAsset | None:
        with self._session_factory() as session:
            return self._knowledge_asset(session.get(KnowledgeAssetRow, asset_id))

    def list_knowledge_assets(
        self, organization_id: UUID | None = None
    ) -> tuple[KnowledgeAsset, ...]:
        with self._session_factory() as session:
            statement = select(KnowledgeAssetRow)
            if organization_id is not None:
                statement = statement.where(KnowledgeAssetRow.organization_id == organization_id)
            rows = session.scalars(statement.order_by(KnowledgeAssetRow.created_at))
            return tuple(self._required_knowledge_asset(row) for row in rows)

    def add_knowledge_version(
        self,
        version: KnowledgeAssetVersion,
        *,
        actor_ref: str,
        idempotency_key: str,
        request_digest: str,
    ) -> KnowledgeAssetVersion:
        with self._session_factory() as session, session.begin():
            replay = self._find_replay(
                session, actor_ref, "knowledge-version.register", idempotency_key, request_digest
            )
            if replay is not None:
                existing = self._knowledge_version(
                    session.get(KnowledgeAssetVersionRow, replay.resource_id)
                )
                if existing is None:
                    raise self._idempotency_corrupt()
                return existing
            session.add(self._knowledge_version_row(version))
            self._add_idempotency(
                session,
                actor_ref,
                "knowledge-version.register",
                idempotency_key,
                request_digest,
                "KNOWLEDGE_VERSION",
                version.knowledge_version_id,
            )
            self._flush(session, ErrorCode.KNOWLEDGE_VERSION_CONFLICT)
        return version

    def save_knowledge_version(
        self,
        version: KnowledgeAssetVersion,
        *,
        expected_version: int,
        actor_ref: str,
        operation: str,
        idempotency_key: str,
        request_digest: str,
    ) -> KnowledgeAssetVersion:
        with self._session_factory() as session, session.begin():
            replay = self._find_replay(
                session, actor_ref, operation, idempotency_key, request_digest
            )
            if replay is not None:
                existing = self._knowledge_version(
                    session.get(KnowledgeAssetVersionRow, replay.resource_id)
                )
                if existing is None:
                    raise self._idempotency_corrupt()
                return existing
            row = session.scalar(
                select(KnowledgeAssetVersionRow)
                .where(
                    KnowledgeAssetVersionRow.knowledge_version_id == version.knowledge_version_id
                )
                .with_for_update()
            )
            if row is None or row.version != expected_version:
                raise self._concurrency_conflict(expected_version)
            row.status = version.status.value
            row.withdrawal_reason = version.withdrawal_reason
            row.withdrawn_at = version.withdrawn_at
            row.updated_at = version.updated_at
            row.version = expected_version + 1
            self._add_idempotency(
                session,
                actor_ref,
                operation,
                idempotency_key,
                request_digest,
                "KNOWLEDGE_VERSION",
                version.knowledge_version_id,
            )
            self._flush(session)
        return version.model_copy(update={"version": expected_version + 1})

    def get_knowledge_version(self, version_id: UUID) -> KnowledgeAssetVersion | None:
        with self._session_factory() as session:
            return self._knowledge_version(session.get(KnowledgeAssetVersionRow, version_id))

    def get_knowledge_version_for_package(
        self, package_version_id: UUID
    ) -> KnowledgeAssetVersion | None:
        with self._session_factory() as session:
            row = session.scalar(
                select(KnowledgeAssetVersionRow).where(
                    KnowledgeAssetVersionRow.package_version_id == package_version_id
                )
            )
            return self._knowledge_version(row)

    def list_knowledge_versions(
        self, asset_id: UUID | None = None
    ) -> tuple[KnowledgeAssetVersion, ...]:
        with self._session_factory() as session:
            statement = select(KnowledgeAssetVersionRow)
            if asset_id is not None:
                statement = statement.where(KnowledgeAssetVersionRow.asset_id == asset_id)
            rows = session.scalars(
                statement.order_by(
                    KnowledgeAssetVersionRow.asset_id,
                    KnowledgeAssetVersionRow.version_label,
                )
            )
            return tuple(self._required_knowledge_version(row) for row in rows)

    def add_context_manifest(
        self,
        manifest: ContextManifestRecord,
        *,
        actor_ref: str,
        idempotency_key: str,
        request_digest: str,
    ) -> ContextManifestRecord:
        with self._session_factory() as session, session.begin():
            replay = self._find_replay(
                session, actor_ref, "context.compile", idempotency_key, request_digest
            )
            if replay is not None:
                existing = self._context_manifest(
                    session.get(ContextManifestRow, replay.resource_id)
                )
                if existing is None:
                    raise self._idempotency_corrupt()
                return existing
            existing_row = session.scalar(
                select(ContextManifestRow).where(
                    ContextManifestRow.actor_ref == actor_ref,
                    ContextManifestRow.request_digest == manifest.request_digest,
                )
            )
            if existing_row is not None:
                existing = self._required_context_manifest(existing_row)
                self._add_idempotency(
                    session,
                    actor_ref,
                    "context.compile",
                    idempotency_key,
                    request_digest,
                    "CONTEXT_MANIFEST",
                    existing.context_manifest_id,
                )
                self._flush(session)
                return existing
            session.add(
                ContextManifestRow(
                    context_manifest_id=manifest.context_manifest_id,
                    organization_id=manifest.organization_id,
                    project_id=manifest.project_id,
                    actor_ref=manifest.actor_ref,
                    purpose=manifest.purpose,
                    project_domain_lock_id=manifest.project_domain_lock_id,
                    domain_lock_digest=manifest.domain_lock_digest,
                    request_digest=manifest.request_digest,
                    manifest_json=manifest.model_dump(mode="json", by_alias=True),
                    canonical_digest=manifest.canonical_digest,
                    compiled_at=manifest.compiled_at,
                )
            )
            self._add_idempotency(
                session,
                actor_ref,
                "context.compile",
                idempotency_key,
                request_digest,
                "CONTEXT_MANIFEST",
                manifest.context_manifest_id,
            )
            self._flush(session)
        return manifest

    def get_context_manifest(self, manifest_id: UUID) -> ContextManifestRecord | None:
        with self._session_factory() as session:
            return self._context_manifest(session.get(ContextManifestRow, manifest_id))

    def list_context_manifests(self, project_id: UUID) -> tuple[ContextManifestRecord, ...]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(ContextManifestRow)
                .where(ContextManifestRow.project_id == project_id)
                .order_by(ContextManifestRow.compiled_at, ContextManifestRow.context_manifest_id)
            )
            return tuple(self._required_context_manifest(row) for row in rows)

    def add_grounding_result(
        self,
        result: GroundingResultRecord,
        *,
        actor_ref: str,
        idempotency_key: str,
        request_digest: str,
    ) -> GroundingResultRecord:
        with self._session_factory() as session, session.begin():
            replay = self._find_replay(
                session, actor_ref, "grounding.validate", idempotency_key, request_digest
            )
            if replay is not None:
                row = session.get(GroundingResultRow, replay.resource_id)
                if row is None:
                    raise self._idempotency_corrupt()
                return GroundingResultRecord.model_validate(row.result_json)
            session.add(
                GroundingResultRow(
                    grounding_result_id=result.grounding_result_id,
                    context_manifest_id=result.context_manifest_id,
                    result_json=result.model_dump(mode="json", by_alias=True),
                    digest=result.digest,
                    created_at=result.created_at,
                )
            )
            self._add_idempotency(
                session,
                actor_ref,
                "grounding.validate",
                idempotency_key,
                request_digest,
                "GROUNDING_RESULT",
                result.grounding_result_id,
            )
            self._flush(session)
        return result

    def get_grounding_result(self, result_id: UUID) -> GroundingResultRecord | None:
        with self._session_factory() as session:
            row = session.get(GroundingResultRow, result_id)
            return GroundingResultRecord.model_validate(row.result_json) if row else None

    def add_impact_report(
        self,
        report: ImpactReportRecord,
        *,
        actor_ref: str,
        idempotency_key: str,
        request_digest: str,
    ) -> ImpactReportRecord:
        with self._session_factory() as session, session.begin():
            replay = self._find_replay(
                session, actor_ref, "semantic-impact.analyze", idempotency_key, request_digest
            )
            if replay is not None:
                row = session.get(SemanticImpactReportRow, replay.resource_id)
                if row is None:
                    raise self._idempotency_corrupt()
                return ImpactReportRecord.model_validate(row.report_json)
            session.add(
                SemanticImpactReportRow(
                    impact_report_id=report.impact_report_id,
                    resource_type=report.resource_type,
                    from_ref=report.from_ref,
                    to_ref=report.to_ref,
                    report_json=report.model_dump(mode="json", by_alias=True),
                    digest=report.digest,
                    created_at=report.created_at,
                )
            )
            self._add_idempotency(
                session,
                actor_ref,
                "semantic-impact.analyze",
                idempotency_key,
                request_digest,
                "SEMANTIC_IMPACT_REPORT",
                report.impact_report_id,
            )
            self._flush(session)
        return report

    def get_impact_report(self, report_id: UUID) -> ImpactReportRecord | None:
        with self._session_factory() as session:
            row = session.get(SemanticImpactReportRow, report_id)
            return ImpactReportRecord.model_validate(row.report_json) if row else None

    def list_impact_reports(self) -> tuple[ImpactReportRecord, ...]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(SemanticImpactReportRow).order_by(
                    SemanticImpactReportRow.created_at,
                    SemanticImpactReportRow.impact_report_id,
                )
            )
            return tuple(ImpactReportRecord.model_validate(row.report_json) for row in rows)

    @staticmethod
    def _semantic_payload_row(payload: SemanticPayloadRecord) -> SemanticPayloadRow:
        return SemanticPayloadRow(
            semantic_payload_id=payload.semantic_payload_id,
            package_version_id=payload.package_version_id,
            package_id=payload.package_id,
            package_version=payload.package_version,
            payload_kind=payload.component_kind.value,
            organization_id=payload.organization_id,
            definition=payload.definition.model_dump(mode="json", by_alias=True),
            canonical_payload=payload.canonical_payload,
            payload_digest=payload.payload_digest,
            provenance_ref=payload.provenance_ref,
            status=payload.status.value,
            governance_reason=payload.governance_reason,
            governed_at=payload.governed_at,
            created_by=payload.created_by,
            created_at=payload.created_at,
            updated_at=payload.updated_at,
            version=payload.version,
        )

    @staticmethod
    def _semantic_payload(row: SemanticPayloadRow | None) -> SemanticPayloadRecord | None:
        if row is None:
            return None
        return SemanticPayloadRecord(
            semantic_payload_id=row.semantic_payload_id,
            package_version_id=row.package_version_id,
            package_id=row.package_id,
            package_version=row.package_version,
            component_kind=SemanticPayloadKind(row.payload_kind),
            organization_id=row.organization_id,
            definition=SemanticPayloadDefinition.model_validate(row.definition),
            canonical_payload=row.canonical_payload,
            payload_digest=row.payload_digest,
            provenance_ref=row.provenance_ref,
            status=AssetLifecycle(row.status),
            governance_reason=row.governance_reason,
            governed_at=row.governed_at,
            created_by=row.created_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
            version=row.version,
        )

    @classmethod
    def _required_semantic_payload(cls, row: SemanticPayloadRow) -> SemanticPayloadRecord:
        payload = cls._semantic_payload(row)
        assert payload is not None
        return payload

    @staticmethod
    def _knowledge_asset(row: KnowledgeAssetRow | None) -> KnowledgeAsset | None:
        if row is None:
            return None
        return KnowledgeAsset(
            asset_id=row.asset_id,
            organization_id=row.organization_id,
            title=row.title,
            description=row.description,
            asset_type=row.asset_type,
            language=row.language,
            owner=row.owner,
            reviewer=row.reviewer,
            created_by=row.created_by,
            created_at=row.created_at,
            version=row.version,
        )

    @classmethod
    def _required_knowledge_asset(cls, row: KnowledgeAssetRow) -> KnowledgeAsset:
        asset = cls._knowledge_asset(row)
        assert asset is not None
        return asset

    @staticmethod
    def _knowledge_version_row(version: KnowledgeAssetVersion) -> KnowledgeAssetVersionRow:
        return KnowledgeAssetVersionRow(
            knowledge_version_id=version.knowledge_version_id,
            asset_id=version.asset_id,
            organization_id=version.organization_id,
            package_version_id=version.package_version_id,
            package_id=version.package_id,
            package_version=version.package_version,
            version_label=version.version_label,
            title=version.title,
            description=version.description,
            asset_type=version.asset_type.value,
            language=version.language,
            owner=version.owner,
            reviewer=version.reviewer,
            source_ref=version.source_ref,
            provenance_digest=version.provenance_digest,
            license_id=version.license_id,
            license_terms=version.license_terms,
            content_classification=version.content_classification.value,
            allowed_purposes=list(version.allowed_purposes),
            valid_from=version.valid_from,
            valid_to=version.valid_to,
            status=version.status.value,
            content_ref=version.content_ref,
            content_type=version.content_type,
            size_bytes=version.size_bytes,
            content_digest=version.content_digest,
            withdrawal_reason=version.withdrawal_reason,
            withdrawn_at=version.withdrawn_at,
            created_by=version.created_by,
            created_at=version.created_at,
            updated_at=version.updated_at,
            version=version.version,
        )

    @staticmethod
    def _knowledge_version(row: KnowledgeAssetVersionRow | None) -> KnowledgeAssetVersion | None:
        if row is None:
            return None
        return KnowledgeAssetVersion(
            knowledge_version_id=row.knowledge_version_id,
            asset_id=row.asset_id,
            organization_id=row.organization_id,
            package_version_id=row.package_version_id,
            package_id=row.package_id,
            package_version=row.package_version,
            version_label=row.version_label,
            title=row.title,
            description=row.description,
            asset_type=row.asset_type,
            language=row.language,
            owner=row.owner,
            reviewer=row.reviewer,
            source_ref=row.source_ref,
            provenance_digest=row.provenance_digest,
            license_id=row.license_id,
            license_terms=row.license_terms,
            content_classification=row.content_classification,
            allowed_purposes=tuple(row.allowed_purposes),
            valid_from=row.valid_from,
            valid_to=row.valid_to,
            status=AssetLifecycle(row.status),
            content_ref=row.content_ref,
            content_type=row.content_type,
            size_bytes=row.size_bytes,
            content_digest=row.content_digest,
            withdrawal_reason=row.withdrawal_reason,
            withdrawn_at=row.withdrawn_at,
            created_by=row.created_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
            version=row.version,
        )

    @classmethod
    def _required_knowledge_version(cls, row: KnowledgeAssetVersionRow) -> KnowledgeAssetVersion:
        version = cls._knowledge_version(row)
        assert version is not None
        return version

    @staticmethod
    def _context_manifest(row: ContextManifestRow | None) -> ContextManifestRecord | None:
        return ContextManifestRecord.model_validate(row.manifest_json) if row else None

    @classmethod
    def _required_context_manifest(cls, row: ContextManifestRow) -> ContextManifestRecord:
        manifest = cls._context_manifest(row)
        assert manifest is not None
        return manifest

    @staticmethod
    def _find_replay(
        session: Session,
        actor_ref: str,
        operation: str,
        idempotency_key: str,
        request_digest: str,
    ) -> SemanticIdempotencyRecordRow | None:
        row = session.scalar(
            select(SemanticIdempotencyRecordRow).where(
                SemanticIdempotencyRecordRow.actor_ref == actor_ref,
                SemanticIdempotencyRecordRow.action_key == operation,
                SemanticIdempotencyRecordRow.idempotency_key == idempotency_key,
            )
        )
        if row is not None and row.request_digest != request_digest:
            raise ForgeOpsError(
                ErrorCode.IDEMPOTENCY_CONFLICT,
                "Idempotency-Key was already used with a different canonical request",
                http_status=409,
            )
        return row

    @staticmethod
    def _add_idempotency(
        session: Session,
        actor_ref: str,
        operation: str,
        idempotency_key: str,
        request_digest: str,
        resource_type: str,
        resource_id: UUID,
    ) -> None:
        session.add(
            SemanticIdempotencyRecordRow(
                record_id=uuid4(),
                actor_ref=actor_ref,
                action_key=operation,
                idempotency_key=idempotency_key,
                request_digest=request_digest,
                resource_type=resource_type,
                resource_id=resource_id,
                created_at=datetime.now(UTC),
            )
        )

    @staticmethod
    def _flush(session: Session, code: ErrorCode = ErrorCode.CONCURRENCY_CONFLICT) -> None:
        try:
            session.flush()
        except IntegrityError as exc:
            raise ForgeOpsError(
                code, "persistence constraint rejected the operation", http_status=409
            ) from exc

    @staticmethod
    def _concurrency_conflict(expected_version: int) -> ForgeOpsError:
        return ForgeOpsError(
            ErrorCode.CONCURRENCY_CONFLICT,
            "resource version changed before the governance transition",
            details={"expectedVersion": expected_version},
            http_status=409,
        )

    @staticmethod
    def _idempotency_corrupt() -> ForgeOpsError:
        return ForgeOpsError(
            ErrorCode.INTERNAL_FAILURE,
            "idempotency record refers to an incompatible or missing resource",
            http_status=500,
        )
