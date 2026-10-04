"""Add retention and provenance controls for prospect data.

Revision ID: 017_data_governance
Revises: 016_durable_outbound_jobs
"""

from alembic import op

revision = "017_data_governance"
down_revision = "016_durable_outbound_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE leads
            ADD COLUMN IF NOT EXISTS lawful_basis TEXT,
            ADD COLUMN IF NOT EXISTS processing_purpose TEXT NOT NULL DEFAULT 'outbound_prospecting',
            ADD COLUMN IF NOT EXISTS source TEXT,
            ADD COLUMN IF NOT EXISTS source_url TEXT,
            ADD COLUMN IF NOT EXISTS collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ADD COLUMN IF NOT EXISTS retention_until TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '180 days');

        CREATE INDEX IF NOT EXISTS idx_leads_retention
            ON leads(tenant_id, retention_until);

        CREATE TABLE IF NOT EXISTS tenant_data_policies (
            tenant_id TEXT PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
            default_retention_days INTEGER NOT NULL DEFAULT 180
                CHECK (default_retention_days BETWEEN 1 AND 3650),
            default_lawful_basis TEXT,
            marketing_purpose TEXT NOT NULL DEFAULT 'outbound_prospecting',
            privacy_notice_url TEXT,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        ALTER TABLE tenant_data_policies ENABLE ROW LEVEL SECURITY;
        CREATE POLICY tenant_data_policies_tenant_isolation
            ON tenant_data_policies
            USING (
                tenant_id::text =
                NULLIF(current_setting('app.tenant_id', true), '')
            )
            WITH CHECK (
                tenant_id::text =
                NULLIF(current_setting('app.tenant_id', true), '')
            );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tenant_data_policies CASCADE")
    op.execute("""
        ALTER TABLE leads
            DROP COLUMN IF EXISTS lawful_basis,
            DROP COLUMN IF EXISTS processing_purpose,
            DROP COLUMN IF EXISTS source,
            DROP COLUMN IF EXISTS source_url,
            DROP COLUMN IF EXISTS collected_at,
            DROP COLUMN IF EXISTS retention_until
    """)
