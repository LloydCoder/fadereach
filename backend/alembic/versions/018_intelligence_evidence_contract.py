"""Harden intelligence evidence semantics.

Revision ID: 018_intelligence_evidence_contract
Revises: 017_data_governance
"""

from alembic import op

revision = "018_intelligence_evidence_contract"
down_revision = "017_data_governance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE lead_intelligence
            ADD COLUMN IF NOT EXISTS evidence_status TEXT NOT NULL DEFAULT 'PARTIAL',
            ADD COLUMN IF NOT EXISTS evidence_contract_version TEXT NOT NULL DEFAULT '1',
            ADD COLUMN IF NOT EXISTS evidence_freshness_days INTEGER;

        ALTER TABLE lead_intelligence
            ADD CONSTRAINT lead_intelligence_evidence_status_check
            CHECK (evidence_status IN ('UNKNOWN','PARTIAL','SUPPORTED'))
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE lead_intelligence
            DROP CONSTRAINT IF EXISTS lead_intelligence_evidence_status_check;
        ALTER TABLE lead_intelligence
            DROP COLUMN IF EXISTS evidence_status,
            DROP COLUMN IF EXISTS evidence_contract_version,
            DROP COLUMN IF EXISTS evidence_freshness_days
    """)
