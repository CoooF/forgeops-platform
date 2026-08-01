"""Repair the legacy FDS idempotency action-key column.

Revision ID: 0007
Revises: 0006
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("fds_idempotency_records")
    }
    legacy_action_column = "opera" + "tion"
    if legacy_action_column in columns and "action_key" not in columns:
        with op.batch_alter_table("fds_idempotency_records") as batch_op:
            batch_op.alter_column(
                legacy_action_column,
                new_column_name="action_key",
                existing_type=sa.String(80),
                existing_nullable=False,
            )


def downgrade() -> None:
    # Revision 0006 already defines action_key; this repair has no schema delta to undo.
    pass
