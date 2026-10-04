"""Add a durable database-backed outbound execution queue.

Revision ID: 016_durable_outbound_jobs
Revises: 015_tenant_security_hardening
"""

from alembic import op

revision = "016_durable_outbound_jobs"
down_revision = "015_tenant_security_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE campaign_executions
            DROP CONSTRAINT IF EXISTS campaign_executions_campaign_id_key;
        DROP INDEX IF EXISTS campaign_executions_campaign_id_key;

        CREATE INDEX IF NOT EXISTS idx_campaign_executions_campaign
            ON campaign_executions(tenant_id, campaign_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS execution_jobs (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            execution_id BIGINT NOT NULL REFERENCES campaign_executions(id) ON DELETE CASCADE,
            status TEXT NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued','running','succeeded','failed','cancelled')),
            attempts INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL DEFAULT 5,
            next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            locked_at TIMESTAMPTZ,
            locked_by TEXT,
            last_error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            completed_at TIMESTAMPTZ,
            UNIQUE(execution_id)
        );

        CREATE INDEX IF NOT EXISTS idx_execution_jobs_claim
            ON execution_jobs(status, next_attempt_at, created_at);

        ALTER TABLE execution_jobs ENABLE ROW LEVEL SECURITY;
        CREATE POLICY execution_jobs_tenant_isolation
            ON execution_jobs
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
    op.execute("DROP TABLE IF EXISTS execution_jobs CASCADE")
    op.execute("""
        ALTER TABLE campaign_executions
            ADD CONSTRAINT campaign_executions_campaign_id_key
            UNIQUE (campaign_id)
    """)
