"""Phase 2: immutable evidence ledger and provenance lineage."""

from alembic import op

revision = "028_evidence_ledger"
down_revision = "027_canonical_revenue_model"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
        ALTER TABLE evidence
            ADD COLUMN IF NOT EXISTS source_type TEXT NOT NULL DEFAULT 'unknown',
            ADD COLUMN IF NOT EXISTS fingerprint TEXT,
            ADD COLUMN IF NOT EXISTS freshness_days INTEGER,
            ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'valid',
            ADD COLUMN IF NOT EXISTS supersedes_evidence_id BIGINT REFERENCES evidence(id) ON DELETE SET NULL;
        ALTER TABLE evidence
            ADD CONSTRAINT evidence_status_check
            CHECK (status IN ('valid','expired','withdrawn','contradicted','superseded','invalid'))
            NOT VALID;
        CREATE INDEX IF NOT EXISTS idx_evidence_tenant_fingerprint ON evidence(tenant_id, fingerprint) WHERE fingerprint IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_evidence_tenant_status ON evidence(tenant_id, status, collected_at DESC);

        CREATE TABLE IF NOT EXISTS evidence_ledger_links (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            evidence_id BIGINT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
            target_type TEXT NOT NULL CHECK (target_type IN ('observation','signal','signal_cluster','hypothesis','opportunity','message','execution','outcome','recommendation')),
            target_id BIGINT NOT NULL,
            relation_type TEXT NOT NULL CHECK (relation_type IN ('supports','contradicts','derived_from','invalidates','context')),
            contribution NUMERIC(6,3) NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (tenant_id, evidence_id, target_type, target_id, relation_type)
        );

        CREATE TABLE IF NOT EXISTS evidence_ledger_events (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            evidence_id BIGINT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
            event_type TEXT NOT NULL CHECK (event_type IN ('created','linked','superseded','contradicted','expired','withdrawn','validated')),
            actor TEXT NOT NULL,
            previous_event_hash TEXT,
            event_hash TEXT NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (tenant_id, event_hash)
        );

        CREATE INDEX IF NOT EXISTS idx_evidence_ledger_links_target ON evidence_ledger_links(tenant_id, target_type, target_id);
        CREATE INDEX IF NOT EXISTS idx_evidence_ledger_events_evidence ON evidence_ledger_events(tenant_id, evidence_id, created_at DESC);

        ALTER TABLE evidence_ledger_links ENABLE ROW LEVEL SECURITY;
        ALTER TABLE evidence_ledger_links FORCE ROW LEVEL SECURITY;
        ALTER TABLE evidence_ledger_events ENABLE ROW LEVEL SECURITY;
        ALTER TABLE evidence_ledger_events FORCE ROW LEVEL SECURITY;

        CREATE POLICY evidence_ledger_links_tenant_isolation ON evidence_ledger_links
            USING (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''));
        CREATE POLICY evidence_ledger_events_tenant_isolation ON evidence_ledger_events
            USING (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''));

        CREATE OR REPLACE FUNCTION fadereach_reject_evidence_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'evidence ledger is append-only; create a new evidence record instead' USING ERRCODE = '42501';
        END;
        $$;
        DROP TRIGGER IF EXISTS evidence_append_only ON evidence;
        CREATE TRIGGER evidence_append_only BEFORE UPDATE OR DELETE ON evidence
            FOR EACH ROW EXECUTE FUNCTION fadereach_reject_evidence_mutation();

        CREATE OR REPLACE FUNCTION fadereach_reject_ledger_event_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'evidence ledger events are append-only' USING ERRCODE = '42501';
        END;
        $$;
        DROP TRIGGER IF EXISTS evidence_ledger_events_append_only ON evidence_ledger_events;
        CREATE TRIGGER evidence_ledger_events_append_only BEFORE UPDATE OR DELETE ON evidence_ledger_events
            FOR EACH ROW EXECUTE FUNCTION fadereach_reject_ledger_event_mutation();

        INSERT INTO evidence_ledger_events
            (tenant_id, evidence_id, event_type, actor, previous_event_hash, event_hash, metadata)
        SELECT e.tenant_id, e.id, 'created', 'migration:028_evidence_ledger', NULL,
               COALESCE(e.content_hash, 'legacy-evidence-' || e.id::text),
               jsonb_build_object('backfilled', true, 'source', e.source)
        FROM evidence e
        WHERE NOT EXISTS (
            SELECT 1 FROM evidence_ledger_events le
            WHERE le.tenant_id = e.tenant_id AND le.evidence_id = e.id
        );

        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'fadereach_runtime') THEN
                REVOKE UPDATE, DELETE ON evidence FROM fadereach_runtime;
                REVOKE UPDATE, DELETE ON evidence_ledger_events FROM fadereach_runtime;
            END IF;
        END
        $$;
    """)

def downgrade() -> None:
    op.execute("""
        DROP TRIGGER IF EXISTS evidence_append_only ON evidence;
        DROP TRIGGER IF EXISTS evidence_ledger_events_append_only ON evidence_ledger_events;
        DROP FUNCTION IF EXISTS fadereach_reject_evidence_mutation();
        DROP FUNCTION IF EXISTS fadereach_reject_ledger_event_mutation();
        DROP TABLE IF EXISTS evidence_ledger_events CASCADE;
        DROP TABLE IF EXISTS evidence_ledger_links CASCADE;
        ALTER TABLE evidence
            DROP CONSTRAINT IF EXISTS evidence_status_check,
            DROP COLUMN IF EXISTS supersedes_evidence_id,
            DROP COLUMN IF EXISTS status,
            DROP COLUMN IF EXISTS freshness_days,
            DROP COLUMN IF EXISTS fingerprint,
            DROP COLUMN IF EXISTS source_type;
    """)
