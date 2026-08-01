from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from forgeops.platform_contracts.domain import StrictModel
from forgeops.platform_core.semantic_runtime.entities import AssetLifecycle

Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


def utc_now() -> datetime:
    return datetime.now(UTC)


class KnowledgeAssetType(StrEnum):
    TEXT = "TEXT"
    JSON = "JSON"
    RULE_GUIDE = "RULE_GUIDE"
    REFERENCE = "REFERENCE"


class KnowledgeClassification(StrEnum):
    SYNTHETIC_PUBLIC = "SYNTHETIC_PUBLIC"
    SYNTHETIC_INTERNAL = "SYNTHETIC_INTERNAL"
    SYNTHETIC_RESTRICTED = "SYNTHETIC_RESTRICTED"


class KnowledgeAsset(StrictModel):
    asset_id: UUID = Field(default_factory=uuid4, alias="assetId")
    organization_id: UUID = Field(alias="organizationId")
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    asset_type: KnowledgeAssetType = Field(alias="assetType")
    language: str = Field(pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$")
    owner: str = Field(min_length=1, max_length=160)
    reviewer: str = Field(min_length=1, max_length=160)
    created_by: str = Field(alias="createdBy")
    created_at: datetime = Field(default_factory=utc_now, alias="createdAt")
    version: int = Field(default=1, ge=1)


class KnowledgeAssetVersion(StrictModel):
    knowledge_version_id: UUID = Field(default_factory=uuid4, alias="knowledgeVersionId")
    asset_id: UUID = Field(alias="assetId")
    organization_id: UUID = Field(alias="organizationId")
    package_version_id: UUID = Field(alias="packageVersionId")
    package_id: str = Field(alias="packageId")
    package_version: str = Field(alias="packageVersion")
    version_label: str = Field(
        alias="versionLabel", pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"
    )
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    asset_type: KnowledgeAssetType = Field(alias="assetType")
    language: str = Field(pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$")
    owner: str = Field(min_length=1, max_length=160)
    reviewer: str = Field(min_length=1, max_length=160)
    source_ref: str = Field(alias="sourceRef", min_length=1, max_length=500)
    provenance_digest: Digest = Field(alias="provenanceDigest")
    license_id: str = Field(alias="licenseId", min_length=1, max_length=120)
    license_terms: str = Field(alias="licenseTerms", min_length=1, max_length=1000)
    content_classification: KnowledgeClassification = Field(alias="contentClassification")
    allowed_purposes: tuple[str, ...] = Field(alias="allowedPurposes", min_length=1, max_length=50)
    valid_from: datetime = Field(alias="validFrom")
    valid_to: datetime | None = Field(default=None, alias="validTo")
    status: AssetLifecycle = AssetLifecycle.VALIDATED_LOCAL_SYNTHETIC
    content_ref: str = Field(alias="contentRef", pattern=r"^file\+sha256://[0-9a-f]{64}$")
    content_type: Literal["text/plain", "application/json"] = Field(alias="contentType")
    size_bytes: int = Field(alias="sizeBytes", ge=1, le=16_384)
    content_digest: Digest = Field(alias="contentDigest")
    withdrawal_reason: str | None = Field(default=None, alias="withdrawalReason", max_length=500)
    withdrawn_at: datetime | None = Field(default=None, alias="withdrawnAt")
    created_by: str = Field(alias="createdBy")
    created_at: datetime = Field(default_factory=utc_now, alias="createdAt")
    updated_at: datetime = Field(default_factory=utc_now, alias="updatedAt")
    version: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def valid_period(self) -> KnowledgeAssetVersion:
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError("validTo must be after validFrom")
        return self

    def effective_status(self, evaluation_time: datetime) -> str:
        if self.status == AssetLifecycle.WITHDRAWN:
            return "WITHDRAWN"
        fixed_evaluation = (
            evaluation_time.replace(tzinfo=UTC)
            if evaluation_time.tzinfo is None
            else evaluation_time
        )
        fixed_from = (
            self.valid_from.replace(tzinfo=UTC)
            if self.valid_from.tzinfo is None
            else self.valid_from
        )
        fixed_to = (
            self.valid_to.replace(tzinfo=UTC)
            if self.valid_to is not None and self.valid_to.tzinfo is None
            else self.valid_to
        )
        if fixed_evaluation < fixed_from:
            return "NOT_YET_EFFECTIVE"
        if fixed_to is not None and fixed_evaluation >= fixed_to:
            return "EXPIRED"
        return self.status.value
