"""REQ-OPS-001/ADR-0006: append-only business and security audit skeleton."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("event_id", sa.Uuid(), primary_key=True),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("actor_ref", sa.String(256), nullable=False),
        sa.Column("resource_ref", sa.String(256), nullable=False),
        sa.Column("result", sa.String(32), nullable=False),
        sa.Column("reason_code", sa.String(128), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("requirement_ids", sa.JSON(), nullable=False),
        sa.Column("test_ids", sa.JSON(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
    )
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_resource_ref", "audit_events", ["resource_ref"])
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"])
    op.create_index("ix_audit_events_trace_id", "audit_events", ["trace_id"])

    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            """
            CREATE FUNCTION forgeops_reject_audit_mutation() RETURNS trigger AS $$
            BEGIN RAISE EXCEPTION 'audit_events is append-only'; END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER audit_events_append_only
            BEFORE UPDATE OR DELETE ON audit_events
            FOR EACH ROW EXECUTE FUNCTION forgeops_reject_audit_mutation();
            """
        )
    elif dialect == "sqlite":
        op.execute(
            "CREATE TRIGGER audit_events_no_update BEFORE UPDATE ON audit_events "
            "BEGIN SELECT RAISE(FAIL, 'audit_events is append-only'); END;"
        )
        op.execute(
            "CREATE TRIGGER audit_events_no_delete BEFORE DELETE ON audit_events "
            "BEGIN SELECT RAISE(FAIL, 'audit_events is append-only'); END;"
        )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events")
        op.execute("DROP FUNCTION IF EXISTS forgeops_reject_audit_mutation")
    elif dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS audit_events_no_update")
        op.execute("DROP TRIGGER IF EXISTS audit_events_no_delete")
    op.drop_index("ix_audit_events_trace_id")
    op.drop_index("ix_audit_events_occurred_at")
    op.drop_index("ix_audit_events_resource_ref")
    op.drop_index("ix_audit_events_event_type")
    op.drop_table("audit_events")
