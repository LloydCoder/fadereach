"""Compliance and retention enforcement controls.

Revision ID: 026_compliance_governance
Revises: 025_outbound_worker_queue_role
"""
from alembic import op

revision = "026_compliance_governance"
down_revision = "025_outbound_worker_queue_role"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE leads
            ADD COLUMN IF NOT EXISTS subscriber_type TEXT NOT NULL DEFAULT 'unknown',
            ADD COLUMN IF NOT EXISTS consent_status TEXT NOT NULL DEFAULT 'unknown',
            ADD COLUMN IF NOT EXISTS objection_status TEXT NOT NULL DEFAULT 'unknown';

        ALTER TABLE leads
            ADD CONSTRAINT leads_subscriber_type_check
            CHECK (subscriber_type IN ('unknown','corporate','individual','sole_trader','partnership'))
            NOT VALID;
        ALTER TABLE leads
            ADD CONSTRAINT leads_consent_status_check
            CHECK (consent_status IN ('unknown','consented','not_required','withdrawn'))
            NOT VALID;
        ALTER TABLE leads
            ADD CONSTRAINT leads_objection_status_check
            CHECK (objection_status IN ('unknown','not_objected','objected'))
            NOT VALID;

        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'fadereach_worker') THEN
                GRANT SELECT ON tenant_data_policies TO fadereach_worker;
                GRANT DELETE ON leads, replies TO fadereach_worker;
            END IF;
        END
        $$;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE leads
            DROP CONSTRAINT IF EXISTS leads_subscriber_type_check,
            DROP CONSTRAINT IF EXISTS leads_consent_status_check,
            DROP CONSTRAINT IF EXISTS leads_objection_status_check,
            DROP COLUMN IF EXISTS subscriber_type,
            DROP COLUMN IF EXISTS consent_status,
            DROP COLUMN IF EXISTS objection_status;
    """)
