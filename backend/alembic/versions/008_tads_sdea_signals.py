"""TADS/SDEA signal ingestion and demand hypotheses.

Revision ID: 008_tads_sdea_signals
Revises: 007_intelligence_engine
"""
from alembic import op

revision = "008_tads_sdea_signals"
down_revision = "007_intelligence_engine"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS intelligence_signals (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            source TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            company_name TEXT,
            domain TEXT,
            observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            score INTEGER NOT NULL DEFAULT 0,
            evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
            external_id TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(tenant_id, source, external_id)
        );

        CREATE TABLE IF NOT EXISTS demand_hypotheses (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            company_name TEXT,
            domain TEXT,
            why_now TEXT NOT NULL,
            demand_type TEXT NOT NULL,
            recommended_offer TEXT,
            evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
            confidence NUMERIC(4,3) NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'new'
                CHECK (status IN ('new','qualified','dismissed','converted')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_intelligence_signals_tenant_domain
            ON intelligence_signals(tenant_id, domain);
        CREATE INDEX IF NOT EXISTS idx_demand_hypotheses_tenant
            ON demand_hypotheses(tenant_id, status);

        ALTER TABLE intelligence_signals ENABLE ROW LEVEL SECURITY;
        ALTER TABLE demand_hypotheses ENABLE ROW LEVEL SECURITY;

        CREATE POLICY intelligence_signals_tenant_isolation
            ON intelligence_signals USING (
                tenant_id::text = NULLIF(current_setting('app.tenant_id', true), '')
            ) WITH CHECK (
                tenant_id::text = NULLIF(current_setting('app.tenant_id', true), '')
            );
        CREATE POLICY demand_hypotheses_tenant_isolation
            ON demand_hypotheses USING (
                tenant_id::text = NULLIF(current_setting('app.tenant_id', true), '')
            ) WITH CHECK (
                tenant_id::text = NULLIF(current_setting('app.tenant_id', true), '')
            );
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS demand_hypotheses CASCADE")
    op.execute("DROP TABLE IF EXISTS intelligence_signals CASCADE")
