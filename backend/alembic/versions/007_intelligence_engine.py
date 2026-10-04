"""Evidence-backed outbound intelligence records.

Revision ID: 007_intelligence_engine
Revises: 006_deliverability_control
"""
from alembic import op

revision = "007_intelligence_engine"
down_revision = "006_deliverability_control"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS lead_intelligence (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            lead_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
            fit_score INTEGER NOT NULL DEFAULT 0,
            why_now TEXT,
            buyer_hypothesis TEXT,
            problem_hypothesis TEXT,
            offer_angle TEXT,
            evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
            confidence NUMERIC(4,3) NOT NULL DEFAULT 0,
            model_version TEXT NOT NULL DEFAULT 'deterministic-v1',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(tenant_id, lead_id)
        );
        CREATE INDEX IF NOT EXISTS idx_lead_intelligence_tenant
            ON lead_intelligence(tenant_id);
        ALTER TABLE lead_intelligence ENABLE ROW LEVEL SECURITY;
        CREATE POLICY lead_intelligence_tenant_isolation
            ON lead_intelligence USING (
                tenant_id::text = NULLIF(current_setting('app.tenant_id', true), '')
            ) WITH CHECK (
                tenant_id::text = NULLIF(current_setting('app.tenant_id', true), '')
            );
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS lead_intelligence CASCADE")
