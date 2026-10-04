"""Learning and attribution persistence.

Revision ID: 011_learning_attribution
Revises: 010_campaign_autopilot
"""
from alembic import op

revision = "011_learning_attribution"
down_revision = "010_campaign_autopilot"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS ai_feedback (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            resource_type TEXT NOT NULL,
            resource_id INTEGER,
            rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
            outcome TEXT,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS optimization_log (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            run_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            insights JSONB NOT NULL DEFAULT '{}'::jsonb,
            actions JSONB NOT NULL DEFAULT '{}'::jsonb
        );

        CREATE INDEX IF NOT EXISTS idx_ai_feedback_tenant_resource
            ON ai_feedback(tenant_id, resource_type, created_at);
        CREATE INDEX IF NOT EXISTS idx_optimization_log_tenant
            ON optimization_log(tenant_id, run_at DESC);

        ALTER TABLE ai_feedback ENABLE ROW LEVEL SECURITY;
        ALTER TABLE optimization_log ENABLE ROW LEVEL SECURITY;

        CREATE POLICY ai_feedback_tenant_isolation ON ai_feedback
            USING (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''));
        CREATE POLICY optimization_log_tenant_isolation ON optimization_log
            USING (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''));
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS optimization_log CASCADE")
    op.execute("DROP TABLE IF EXISTS ai_feedback CASCADE")
