"""Harden Campaign Autopilot approvals and stop controls.

Revision ID: 020_autopilot_governance
Revises: 019_graph_identity_hardening
"""

from alembic import op

revision = "020_autopilot_governance"
down_revision = "019_graph_identity_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE autopilot_runs
            ADD COLUMN IF NOT EXISTS approval_hash TEXT,
            ADD COLUMN IF NOT EXISTS approval_expires_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS policy_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
            ADD COLUMN IF NOT EXISTS stop_requested BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS launched_at TIMESTAMPTZ;

        CREATE INDEX IF NOT EXISTS idx_autopilot_stop
            ON autopilot_runs(tenant_id, stop_requested, status);
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE autopilot_runs
            DROP COLUMN IF EXISTS approval_hash,
            DROP COLUMN IF EXISTS approval_expires_at,
            DROP COLUMN IF EXISTS policy_snapshot,
            DROP COLUMN IF EXISTS stop_requested,
            DROP COLUMN IF EXISTS launched_at
    """)
