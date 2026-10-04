"""Phase 11: revenue attribution and intelligence metrics."""

from alembic import op

revision = "037_revenue_intelligence"
down_revision = "036_account_memory"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS revenue_attributions (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            revenue_id BIGINT NOT NULL REFERENCES revenue(id) ON DELETE CASCADE,
            source_type TEXT NOT NULL
                CHECK (source_type IN ('signal','signal_cluster','opportunity','hypothesis','campaign','person','message','reply','meeting','account','experiment')),
            source_id BIGINT NOT NULL,
            attribution_type TEXT NOT NULL
                CHECK (attribution_type IN ('sourced','influenced','assisted','first_touch','last_touch')),
            weight NUMERIC(6,5) NOT NULL DEFAULT 0
                CHECK (weight >= 0 AND weight <= 1),
            evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
            attributed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (tenant_id, revenue_id, source_type, source_id, attribution_type)
        );

        CREATE TABLE IF NOT EXISTS revenue_metrics_daily (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            metric_date DATE NOT NULL,
            opportunities_created INTEGER NOT NULL DEFAULT 0,
            meetings_held INTEGER NOT NULL DEFAULT 0,
            deals_won INTEGER NOT NULL DEFAULT 0,
            revenue_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
            sourced_revenue NUMERIC(18,2) NOT NULL DEFAULT 0,
            influenced_revenue NUMERIC(18,2) NOT NULL DEFAULT 0,
            signal_to_opportunity_rate NUMERIC(8,5) NOT NULL DEFAULT 0,
            opportunity_to_meeting_rate NUMERIC(8,5) NOT NULL DEFAULT 0,
            meeting_to_won_rate NUMERIC(8,5) NOT NULL DEFAULT 0,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (tenant_id, metric_date)
        );

        CREATE INDEX IF NOT EXISTS idx_revenue_attributions_source
            ON revenue_attributions(tenant_id, source_type, source_id);
        CREATE INDEX IF NOT EXISTS idx_revenue_metrics_date
            ON revenue_metrics_daily(tenant_id, metric_date DESC);

        ALTER TABLE revenue_attributions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE revenue_attributions FORCE ROW LEVEL SECURITY;
        ALTER TABLE revenue_metrics_daily ENABLE ROW LEVEL SECURITY;
        ALTER TABLE revenue_metrics_daily FORCE ROW LEVEL SECURITY;

        CREATE POLICY revenue_attributions_tenant_isolation ON revenue_attributions
            USING (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''));
        CREATE POLICY revenue_metrics_daily_tenant_isolation ON revenue_metrics_daily
            USING (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''));
    """)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS revenue_metrics_daily CASCADE")
    op.execute("DROP TABLE IF EXISTS revenue_attributions CASCADE")
