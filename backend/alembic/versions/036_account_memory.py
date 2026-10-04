"""Phase 10: persistent account memory with provenance."""

from alembic import op

revision = "036_account_memory"
down_revision = "035_buying_committee"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS account_memory_entries (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            account_id BIGINT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            memory_type TEXT NOT NULL
                CHECK (memory_type IN ('fact','signal','hypothesis','objection','preference','technology','leadership','campaign','engagement','outcome','risk','relationship','unknown')),
            content JSONB NOT NULL,
            fingerprint TEXT NOT NULL,
            confidence NUMERIC(5,4) NOT NULL DEFAULT 0
                CHECK (confidence >= 0 AND confidence <= 1),
            evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
            source_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
            valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            valid_to TIMESTAMPTZ,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active','superseded','expired','invalid','unknown')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (tenant_id, account_id, fingerprint)
        );

        CREATE INDEX IF NOT EXISTS idx_account_memory_account
            ON account_memory_entries(tenant_id, account_id, status, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_account_memory_type
            ON account_memory_entries(tenant_id, account_id, memory_type, updated_at DESC);

        ALTER TABLE account_memory_entries ENABLE ROW LEVEL SECURITY;
        ALTER TABLE account_memory_entries FORCE ROW LEVEL SECURITY;

        CREATE POLICY account_memory_entries_tenant_isolation ON account_memory_entries
            USING (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''));
    """)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS account_memory_entries CASCADE")
