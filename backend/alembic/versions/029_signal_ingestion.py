"""Phase 3: governed signal ingestion and normalization."""

from alembic import op

revision = "029_signal_ingestion"
down_revision = "028_evidence_ledger"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS signal_sources (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            source_key TEXT NOT NULL,
            source_kind TEXT NOT NULL DEFAULT 'internal',
            trust_tier TEXT NOT NULL DEFAULT 'T2'
                CHECK (trust_tier IN ('T0','T1','T2','T3','T4','T5')),
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            schema_version TEXT NOT NULL DEFAULT '1',
            retention_days INTEGER,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_seen_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (tenant_id, source_key)
        );

        CREATE TABLE IF NOT EXISTS signal_ingestion_runs (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            source_key TEXT NOT NULL,
            started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            completed_at TIMESTAMPTZ,
            status TEXT NOT NULL DEFAULT 'running'
                CHECK (status IN ('running','completed','partial','failed')),
            received_count INTEGER NOT NULL DEFAULT 0,
            accepted_count INTEGER NOT NULL DEFAULT 0,
            duplicate_count INTEGER NOT NULL DEFAULT 0,
            rejected_count INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            error_summary TEXT,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb
        );

        ALTER TABLE intelligence_signals
            ADD COLUMN IF NOT EXISTS normalized_type TEXT,
            ADD COLUMN IF NOT EXISTS signal_category TEXT,
            ADD COLUMN IF NOT EXISTS source_url TEXT,
            ADD COLUMN IF NOT EXISTS source_observed_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS freshness_expires_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS raw_payload_hash TEXT,
            ADD COLUMN IF NOT EXISTS normalization_version TEXT NOT NULL DEFAULT '1',
            ADD COLUMN IF NOT EXISTS normalization_status TEXT NOT NULL DEFAULT 'normalized';

        ALTER TABLE account_signals
            ADD COLUMN IF NOT EXISTS normalized_type TEXT,
            ADD COLUMN IF NOT EXISTS signal_category TEXT,
            ADD COLUMN IF NOT EXISTS source_url TEXT;

        CREATE INDEX IF NOT EXISTS idx_signal_sources_tenant_enabled
            ON signal_sources(tenant_id, enabled, source_key);
        CREATE INDEX IF NOT EXISTS idx_signal_runs_tenant_source_time
            ON signal_ingestion_runs(tenant_id, source_key, started_at DESC);
        CREATE INDEX IF NOT EXISTS idx_intel_signals_normalized
            ON intelligence_signals(tenant_id, normalized_type, observed_at DESC);
        CREATE INDEX IF NOT EXISTS idx_intel_signals_category
            ON intelligence_signals(tenant_id, signal_category, observed_at DESC);
        CREATE INDEX IF NOT EXISTS idx_intel_signals_freshness
            ON intelligence_signals(tenant_id, freshness_expires_at);
        CREATE UNIQUE INDEX IF NOT EXISTS uq_intel_signals_payload_hash
            ON intelligence_signals(tenant_id, source, raw_payload_hash)
            WHERE raw_payload_hash IS NOT NULL;

        ALTER TABLE signal_sources ENABLE ROW LEVEL SECURITY;
        ALTER TABLE signal_sources FORCE ROW LEVEL SECURITY;
        ALTER TABLE signal_ingestion_runs ENABLE ROW LEVEL SECURITY;
        ALTER TABLE signal_ingestion_runs FORCE ROW LEVEL SECURITY;

        CREATE POLICY signal_sources_tenant_isolation ON signal_sources
            USING (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''));
        CREATE POLICY signal_ingestion_runs_tenant_isolation ON signal_ingestion_runs
            USING (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''));
    """)

def downgrade() -> None:
    op.execute("""
        ALTER TABLE account_signals
            DROP COLUMN IF EXISTS source_url,
            DROP COLUMN IF EXISTS signal_category,
            DROP COLUMN IF EXISTS normalized_type;
        ALTER TABLE intelligence_signals
            DROP COLUMN IF EXISTS normalization_status,
            DROP COLUMN IF EXISTS normalization_version,
            DROP COLUMN IF EXISTS raw_payload_hash,
            DROP COLUMN IF EXISTS freshness_expires_at,
            DROP COLUMN IF EXISTS source_observed_at,
            DROP COLUMN IF EXISTS source_url,
            DROP COLUMN IF EXISTS signal_category,
            DROP COLUMN IF EXISTS normalized_type;
        DROP TABLE IF EXISTS signal_ingestion_runs CASCADE;
        DROP TABLE IF EXISTS signal_sources CASCADE;
    """)
