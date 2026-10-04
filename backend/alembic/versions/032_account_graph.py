"""Phase 6: account intelligence graph edges and traversal metadata."""

from alembic import op

revision = "032_account_graph"
down_revision = "031_temporal_intelligence"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS account_graph_edges (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            account_id BIGINT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            source_type TEXT NOT NULL
                CHECK (source_type IN ('account','person','technology','initiative','signal','evidence','opportunity','hypothesis','campaign','outcome')),
            source_id BIGINT NOT NULL,
            target_type TEXT NOT NULL
                CHECK (target_type IN ('account','person','technology','initiative','signal','evidence','opportunity','campaign','outcome')),
            target_id BIGINT NOT NULL,
            relation TEXT NOT NULL,
            confidence NUMERIC(5,4) NOT NULL DEFAULT 0
                CHECK (confidence >= 0 AND confidence <= 1),
            evidence_id BIGINT REFERENCES evidence(id) ON DELETE SET NULL,
            valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            valid_to TIMESTAMPTZ,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (tenant_id, source_type, source_id, relation, target_type, target_id)
        );

        CREATE INDEX IF NOT EXISTS idx_account_graph_account
            ON account_graph_edges(tenant_id, account_id);
        CREATE INDEX IF NOT EXISTS idx_account_graph_source
            ON account_graph_edges(tenant_id, source_type, source_id);
        CREATE INDEX IF NOT EXISTS idx_account_graph_target
            ON account_graph_edges(tenant_id, target_type, target_id);

        ALTER TABLE account_graph_edges ENABLE ROW LEVEL SECURITY;
        ALTER TABLE account_graph_edges FORCE ROW LEVEL SECURITY;

        CREATE POLICY account_graph_edges_tenant_isolation ON account_graph_edges
            USING (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''));
    """)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS account_graph_edges CASCADE")
