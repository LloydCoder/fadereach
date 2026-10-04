"""Phase 5: temporal signal intelligence and trajectory state."""

from alembic import op

revision = "031_temporal_intelligence"
down_revision = "030_signal_convergence"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS signal_trajectories (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            organization_id BIGINT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            normalized_type TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'emerging'
                CHECK (state IN ('emerging','persistent','accelerating','decelerating','recurring','reversing','decayed','inactive','unknown')),
            observation_count INTEGER NOT NULL DEFAULT 0,
            recurrence_count INTEGER NOT NULL DEFAULT 0,
            velocity NUMERIC(10,4) NOT NULL DEFAULT 0,
            acceleration NUMERIC(10,4) NOT NULL DEFAULT 0,
            trend_score NUMERIC(8,4) NOT NULL DEFAULT 0,
            confidence NUMERIC(5,4) NOT NULL DEFAULT 0
                CHECK (confidence >= 0 AND confidence <= 1),
            first_seen_at TIMESTAMPTZ,
            last_seen_at TIMESTAMPTZ,
            evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            rationale JSONB NOT NULL DEFAULT '{}'::jsonb,
            UNIQUE (tenant_id, organization_id, normalized_type)
        );

        CREATE INDEX IF NOT EXISTS idx_signal_trajectories_tenant_state
            ON signal_trajectories(tenant_id, state, evaluated_at DESC);

        ALTER TABLE signal_trajectories ENABLE ROW LEVEL SECURITY;
        ALTER TABLE signal_trajectories FORCE ROW LEVEL SECURITY;

        CREATE POLICY signal_trajectories_tenant_isolation ON signal_trajectories
            USING (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''));
    """)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS signal_trajectories CASCADE")
