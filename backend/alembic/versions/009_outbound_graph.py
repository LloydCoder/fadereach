"""Persistent outbound intelligence graph.

Revision ID: 009_outbound_graph
Revises: 008_tads_sdea_signals
"""
from alembic import op

revision = "009_outbound_graph"
down_revision = "008_tads_sdea_signals"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            domain TEXT NOT NULL,
            name TEXT,
            industry TEXT,
            company_size TEXT,
            location TEXT,
            website TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(tenant_id, domain)
        );

        CREATE TABLE IF NOT EXISTS account_signals (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            account_id BIGINT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            source TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
            external_id TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(tenant_id, source, external_id)
        );

        ALTER TABLE leads ADD COLUMN IF NOT EXISTS account_id BIGINT REFERENCES accounts(id) ON DELETE SET NULL;
        ALTER TABLE demand_hypotheses ADD COLUMN IF NOT EXISTS account_id BIGINT REFERENCES accounts(id) ON DELETE SET NULL;

        CREATE INDEX IF NOT EXISTS idx_accounts_tenant_domain
            ON accounts(tenant_id, domain);
        CREATE INDEX IF NOT EXISTS idx_account_signals_account
            ON account_signals(tenant_id, account_id);

        ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
        ALTER TABLE account_signals ENABLE ROW LEVEL SECURITY;

        CREATE POLICY accounts_tenant_isolation ON accounts
            USING (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''));

        CREATE POLICY account_signals_tenant_isolation ON account_signals
            USING (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''));
    """)


def downgrade():
    op.execute("ALTER TABLE demand_hypotheses DROP COLUMN IF EXISTS account_id")
    op.execute("ALTER TABLE leads DROP COLUMN IF EXISTS account_id")
    op.execute("DROP TABLE IF EXISTS account_signals CASCADE")
    op.execute("DROP TABLE IF EXISTS accounts CASCADE")
