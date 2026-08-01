"""Add EPIC-02.6C semantic and knowledge runtime persistence.

Revision ID: 0008
Revises: 0007
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "semantic_payloads",
        sa.Column("semantic_payload_id", sa.Uuid(), primary_key=True),
        sa.Column("package_version_id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.String(128), nullable=False),
        sa.Column("package_version", sa.String(32), nullable=False),
        sa.Column("payload_kind", sa.String(32), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("canonical_payload", sa.Text(), nullable=False),
        sa.Column("payload_digest", sa.String(80), nullable=False),
        sa.Column("provenance_ref", sa.String(512), nullable=False),
        sa.Column("status", sa.String(48), nullable=False),
        sa.Column("governance_reason", sa.String(500), nullable=True),
        sa.Column("governed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["package_version_id"], ["fds_package_versions.package_version_id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"]),
        sa.UniqueConstraint("package_version_id", name="uq_semantic_payload_package_version"),
        sa.CheckConstraint(
            "payload_kind IN ('ONTOLOGY', 'TERMINOLOGY', 'DATA_MAPPING')",
            name="ck_semantic_payload_kind",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'VALIDATED_LOCAL_SYNTHETIC', "
            "'PUBLISHED_LOCAL_SYNTHETIC', 'WITHDRAWN')",
            name="ck_semantic_payload_status",
        ),
    )
    op.create_index("ix_semantic_payloads_package_version_id", "semantic_payloads", ["package_version_id"])
    op.create_index("ix_semantic_payloads_package_id", "semantic_payloads", ["package_id"])
    op.create_index("ix_semantic_payloads_payload_kind", "semantic_payloads", ["payload_kind"])
    op.create_index("ix_semantic_payloads_organization_id", "semantic_payloads", ["organization_id"])
    op.create_index("ix_semantic_payloads_payload_digest", "semantic_payloads", ["payload_digest"])
    op.create_index("ix_semantic_payloads_status", "semantic_payloads", ["status"])

    op.create_table(
        "knowledge_assets",
        sa.Column("asset_id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.String(2000), nullable=False),
        sa.Column("asset_type", sa.String(32), nullable=False),
        sa.Column("language", sa.String(16), nullable=False),
        sa.Column("owner", sa.String(160), nullable=False),
        sa.Column("reviewer", sa.String(160), nullable=False),
        sa.Column("created_by", sa.String(256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"]),
    )
    op.create_index("ix_knowledge_assets_organization_id", "knowledge_assets", ["organization_id"])

    op.create_table(
        "knowledge_asset_versions",
        sa.Column("knowledge_version_id", sa.Uuid(), primary_key=True),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("package_version_id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.String(128), nullable=False),
        sa.Column("package_version", sa.String(32), nullable=False),
        sa.Column("version_label", sa.String(32), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.String(2000), nullable=False),
        sa.Column("asset_type", sa.String(32), nullable=False),
        sa.Column("language", sa.String(16), nullable=False),
        sa.Column("owner", sa.String(160), nullable=False),
        sa.Column("reviewer", sa.String(160), nullable=False),
        sa.Column("source_ref", sa.String(512), nullable=False),
        sa.Column("provenance_digest", sa.String(80), nullable=False),
        sa.Column("license_id", sa.String(120), nullable=False),
        sa.Column("license_terms", sa.String(1000), nullable=False),
        sa.Column("content_classification", sa.String(48), nullable=False),
        sa.Column("allowed_purposes", sa.JSON(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(48), nullable=False),
        sa.Column("content_ref", sa.String(96), nullable=False),
        sa.Column("content_type", sa.String(48), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_digest", sa.String(80), nullable=False),
        sa.Column("withdrawal_reason", sa.String(500), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["asset_id"], ["knowledge_assets.asset_id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"]),
        sa.ForeignKeyConstraint(["package_version_id"], ["fds_package_versions.package_version_id"]),
        sa.UniqueConstraint("asset_id", "version_label", name="uq_knowledge_asset_version"),
        sa.UniqueConstraint("package_version_id", name="uq_knowledge_package_version"),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'VALIDATED_LOCAL_SYNTHETIC', "
            "'PUBLISHED_LOCAL_SYNTHETIC', 'WITHDRAWN')",
            name="ck_knowledge_version_status",
        ),
    )
    for name, columns in (
        ("ix_knowledge_asset_versions_asset_id", ["asset_id"]),
        ("ix_knowledge_asset_versions_organization_id", ["organization_id"]),
        ("ix_knowledge_asset_versions_package_version_id", ["package_version_id"]),
        ("ix_knowledge_asset_versions_package_id", ["package_id"]),
        ("ix_knowledge_asset_versions_content_classification", ["content_classification"]),
        ("ix_knowledge_asset_versions_valid_from", ["valid_from"]),
        ("ix_knowledge_asset_versions_status", ["status"]),
        ("ix_knowledge_asset_versions_content_digest", ["content_digest"]),
    ):
        op.create_index(name, "knowledge_asset_versions", columns)

    op.create_table(
        "context_manifests",
        sa.Column("context_manifest_id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("actor_ref", sa.String(256), nullable=False),
        sa.Column("purpose", sa.String(120), nullable=False),
        sa.Column("project_domain_lock_id", sa.Uuid(), nullable=False),
        sa.Column("domain_lock_digest", sa.String(80), nullable=False),
        sa.Column("request_digest", sa.String(80), nullable=False),
        sa.Column("manifest_json", sa.JSON(), nullable=False),
        sa.Column("canonical_digest", sa.String(80), nullable=False),
        sa.Column("compiled_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"]),
        sa.ForeignKeyConstraint(
            ["project_domain_lock_id"], ["project_domain_locks.project_domain_lock_id"]
        ),
        sa.UniqueConstraint("actor_ref", "request_digest", name="uq_context_actor_request"),
    )
    op.create_index("ix_context_manifests_organization_id", "context_manifests", ["organization_id"])
    op.create_index("ix_context_manifests_project_id", "context_manifests", ["project_id"])
    op.create_index("ix_context_manifests_actor_ref", "context_manifests", ["actor_ref"])
    op.create_index("ix_context_manifests_project_domain_lock_id", "context_manifests", ["project_domain_lock_id"])
    op.create_index("ix_context_manifests_request_digest", "context_manifests", ["request_digest"])
    op.create_index("ix_context_manifests_canonical_digest", "context_manifests", ["canonical_digest"])
    op.create_index("ix_context_manifests_compiled_at", "context_manifests", ["compiled_at"])

    op.create_table(
        "grounding_results",
        sa.Column("grounding_result_id", sa.Uuid(), primary_key=True),
        sa.Column("context_manifest_id", sa.Uuid(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("digest", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["context_manifest_id"], ["context_manifests.context_manifest_id"]),
    )
    op.create_index("ix_grounding_results_context_manifest_id", "grounding_results", ["context_manifest_id"])
    op.create_index("ix_grounding_results_digest", "grounding_results", ["digest"])
    op.create_index("ix_grounding_results_created_at", "grounding_results", ["created_at"])

    op.create_table(
        "semantic_impact_reports",
        sa.Column("impact_report_id", sa.Uuid(), primary_key=True),
        sa.Column("resource_type", sa.String(24), nullable=False),
        sa.Column("from_ref", sa.String(160), nullable=False),
        sa.Column("to_ref", sa.String(160), nullable=False),
        sa.Column("report_json", sa.JSON(), nullable=False),
        sa.Column("digest", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_semantic_impact_reports_resource_type", "semantic_impact_reports", ["resource_type"])
    op.create_index("ix_semantic_impact_reports_from_ref", "semantic_impact_reports", ["from_ref"])
    op.create_index("ix_semantic_impact_reports_to_ref", "semantic_impact_reports", ["to_ref"])
    op.create_index("ix_semantic_impact_reports_digest", "semantic_impact_reports", ["digest"])
    op.create_index("ix_semantic_impact_reports_created_at", "semantic_impact_reports", ["created_at"])

    op.create_table(
        "semantic_idempotency_records",
        sa.Column("record_id", sa.Uuid(), primary_key=True),
        sa.Column("actor_ref", sa.String(256), nullable=False),
        sa.Column("action_key", sa.String(80), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_digest", sa.String(80), nullable=False),
        sa.Column("resource_type", sa.String(48), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "actor_ref", "action_key", "idempotency_key", name="uq_semantic_idempotency_key"
        ),
    )


def downgrade() -> None:
    op.drop_table("semantic_idempotency_records")
    op.drop_table("semantic_impact_reports")
    op.drop_table("grounding_results")
    op.drop_table("context_manifests")
    op.drop_table("knowledge_asset_versions")
    op.drop_table("knowledge_assets")
    op.drop_table("semantic_payloads")

