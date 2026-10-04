"""Phase 4: signal convergence and corroboration controls."""

from alembic import op

revision = "030_signal_convergence"
down_revision = "029_signal_ingestion"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
        ALTER TABLE signals
            ADD COLUMN IF NOT EXISTS source TEXT,
            ADD COLUMN IF NOT EXISTS normalized_type TEXT,
            ADD COLUMN IF NOT EXISTS signal_category TEXT,
            ADD COLUMN IF NOT EXISTS source_independence_key TEXT,
            ADD COLUMN IF NOT EXISTS polarity SMALLINT NOT NULL DEFAULT 1,
            ADD COLUMN IF NOT EXISTS decay_rate NUMERIC(6,5) NOT NULL DEFAULT 0.02;

        ALTER TABLE signals
            ADD CONSTRAINT signals_polarity_check
            CHECK (polarity IN (-1, 1))
            NOT VALID;
        ALTER TABLE signals
            ADD CONSTRAINT signals_decay_rate_check
            CHECK (decay_rate >= 0 AND decay_rate <= 1)
            NOT VALID;

        ALTER TABLE signal_clusters
            ADD COLUMN IF NOT EXISTS contradiction_count INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS decay_score NUMERIC(6,3) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS rationale JSONB NOT NULL DEFAULT '{}'::jsonb,
            ADD COLUMN IF NOT EXISTS evaluated_at TIMESTAMPTZ;

        CREATE INDEX IF NOT EXISTS idx_signals_convergence_lookup
            ON signals(tenant_id, organization_id, normalized_type, last_seen_at DESC);
        CREATE INDEX IF NOT EXISTS idx_signals_source_independence
            ON signals(tenant_id, organization_id, source_independence_key);
        CREATE INDEX IF NOT EXISTS idx_clusters_convergence_score
            ON signal_clusters(tenant_id, convergence_score DESC, last_seen_at DESC);
    """)

def downgrade() -> None:
    op.execute("""
        ALTER TABLE signal_clusters
            DROP COLUMN IF EXISTS evaluated_at,
            DROP COLUMN IF EXISTS rationale,
            DROP COLUMN IF EXISTS decay_score,
            DROP COLUMN IF EXISTS contradiction_count;
        ALTER TABLE signals
            DROP CONSTRAINT IF EXISTS signals_decay_rate_check,
            DROP CONSTRAINT IF EXISTS signals_polarity_check,
            DROP COLUMN IF EXISTS decay_rate,
            DROP COLUMN IF EXISTS polarity,
            DROP COLUMN IF EXISTS source_independence_key,
            DROP COLUMN IF EXISTS signal_category,
            DROP COLUMN IF EXISTS normalized_type,
            DROP COLUMN IF EXISTS source;
    """)
