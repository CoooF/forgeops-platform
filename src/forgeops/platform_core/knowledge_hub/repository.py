from __future__ import annotations

from typing import Protocol
from uuid import UUID

from forgeops.platform_core.knowledge_hub.entities import KnowledgeAsset, KnowledgeAssetVersion


class KnowledgeHubRepository(Protocol):
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

    def add_knowledge_asset(
        self,
        asset: KnowledgeAsset,
        *,
        actor_ref: str,
        idempotency_key: str,
        request_digest: str,
    ) -> KnowledgeAsset: ...

    def get_knowledge_asset(self, asset_id: UUID) -> KnowledgeAsset | None: ...

    def list_knowledge_assets(
        self, organization_id: UUID | None = None
    ) -> tuple[KnowledgeAsset, ...]: ...

    def add_knowledge_version(
        self,
        version: KnowledgeAssetVersion,
        *,
        actor_ref: str,
        idempotency_key: str,
        request_digest: str,
    ) -> KnowledgeAssetVersion: ...

    def save_knowledge_version(
        self,
        version: KnowledgeAssetVersion,
        *,
        expected_version: int,
        actor_ref: str,
        operation: str,
        idempotency_key: str,
        request_digest: str,
    ) -> KnowledgeAssetVersion: ...

    def get_knowledge_version(self, version_id: UUID) -> KnowledgeAssetVersion | None: ...

    def get_knowledge_version_for_package(
        self, package_version_id: UUID
    ) -> KnowledgeAssetVersion | None: ...

    def list_knowledge_versions(
        self, asset_id: UUID | None = None
    ) -> tuple[KnowledgeAssetVersion, ...]: ...
