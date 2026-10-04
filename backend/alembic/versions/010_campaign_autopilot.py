"""Campaign Autopilot run state and approval records.

Revision ID: 010_campaign_autopilot
Revises: 009_outbound_graph
"""
from alembic import op

revision = "010_campaign_autopilot"
down_revision = "009_outbound_graph"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS autopilot_runs (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            goal TEXT NOT NULL,
            plan JSONB NOT NULL,
            status TEXT NOT NULL DEFAULT 'planned'
                CHECK (status IN ('planned','approved','launched','completed','cancelled')),
            approved_by TEXT,
            approved_at TIMESTAMPTZ,
            campaign_id INTEGER REFERENCES campaigns(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_autopilot_runs_tenant
            ON autopilot_runs(tenant_id, created_at DESC);
        ALTER TABLE autopilot_runs ENABLE ROW LEVEL SECURITY;
        CREATE POLICY autopilot_runs_tenant_isolation ON autopilot_runs
            USING (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''));
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS autopilot_runs CASCADE")
