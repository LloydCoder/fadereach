"""Deliverability control-plane fields and guardrails.

Revision ID: 006_deliverability_control
Revises: 005_outbound_execution
"""
from alembic import op

revision = "006_deliverability_control"
down_revision = "005_outbound_execution"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE domains ADD COLUMN IF NOT EXISTS sending_ip INET;
        ALTER TABLE domains ADD COLUMN IF NOT EXISTS dkim_selector TEXT;
        ALTER TABLE domains ADD COLUMN IF NOT EXISTS ptr_valid BOOLEAN;
        ALTER TABLE domains ADD COLUMN IF NOT EXISTS dkim_valid BOOLEAN NOT NULL DEFAULT FALSE;
        ALTER TABLE domains ADD COLUMN IF NOT EXISTS dmarc_policy TEXT;
        ALTER TABLE domains ADD COLUMN IF NOT EXISTS sending_paused BOOLEAN NOT NULL DEFAULT FALSE;
        ALTER TABLE domains ADD COLUMN IF NOT EXISTS pause_reason TEXT;
        ALTER TABLE domains ADD COLUMN IF NOT EXISTS last_deliverability_check TIMESTAMPTZ;
        CREATE INDEX IF NOT EXISTS idx_domains_sending_paused
            ON domains(tenant_id, sending_paused);
    """)


def downgrade():
    op.execute("""
        ALTER TABLE domains
            DROP COLUMN IF EXISTS sending_ip,
            DROP COLUMN IF EXISTS dkim_selector,
            DROP COLUMN IF EXISTS ptr_valid,
            DROP COLUMN IF EXISTS dkim_valid,
            DROP COLUMN IF EXISTS dmarc_policy,
            DROP COLUMN IF EXISTS sending_paused,
            DROP COLUMN IF EXISTS pause_reason,
            DROP COLUMN IF EXISTS last_deliverability_check;
    """)
