"""Phase 7: evidence-backed why-now assessments."""

from alembic import op

revision = "033_why_now"
down_revision = "032_account_graph"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS why_now_assessments (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            organization_id BIGINT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            account_id BIGINT REFERENCES accounts(id) ON DELETE SET NULL,
            opportunity_id BIGINT REFERENCES opportunities(id) ON DELETE SET NULL,
            what_changed TEXT NOT NULL,
            when_changed TIMESTAMPTZ,
            why_matters TEXT NOT NULL,
            why_now TEXT NOT NULL,
            capability_required TEXT,
            confidence NUMERIC(5,4) NOT NULL DEFAULT 0
                CHECK (confidence >= 0 AND confidence <= 1),
            unknowns JSONB NOT NULL DEFAULT '[]'::jsonb,
            evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
            signal_cluster_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
            trajectory_states JSONB NOT NULL DEFAULT '[]'::jsonb,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active','stale','superseded','blocked','unknown')),
            evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_why_now_tenant_org
            ON why_now_assessments(tenant_id, organization_id, evaluated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_why_now_tenant_confidence
            ON why_now_assessments(tenant_id, confidence DESC, evaluated_at DESC);

        ALTER TABLE why_now_assessments ENABLE ROW LEVEL SECURITY;
        ALTER TABLE why_now_assessments FORCE ROW LEVEL SECURITY;

        CREATE POLICY why_now_assessments_tenant_isolation ON why_now_assessments
            USING (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''));
    """)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS why_now_assessments CASCADE")
