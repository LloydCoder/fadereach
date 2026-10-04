"""Harden outbound graph identity, provenance and temporal state.

Revision ID: 019_graph_identity_hardening
Revises: 018_intel_evidence_contract
"""

from alembic import op

revision = "019_graph_identity_hardening"
down_revision = "018_intel_evidence_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE accounts
            ADD COLUMN IF NOT EXISTS canonical_domain TEXT,
            ADD COLUMN IF NOT EXISTS first_observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ADD COLUMN IF NOT EXISTS last_observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

        UPDATE accounts
        SET canonical_domain=lower(regexp_replace(domain, '\\\\.$', ''))
        WHERE canonical_domain IS NULL;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_accounts_tenant_canonical_domain
            ON accounts(tenant_id, canonical_domain);

        ALTER TABLE account_signals
            ADD COLUMN IF NOT EXISTS source_url TEXT,
            ADD COLUMN IF NOT EXISTS confidence NUMERIC(4,3) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ADD COLUMN IF NOT EXISTS valid_to TIMESTAMPTZ;

        CREATE TABLE IF NOT EXISTS account_aliases (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            account_id BIGINT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            source TEXT NOT NULL,
            external_id TEXT NOT NULL,
            observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            UNIQUE(tenant_id, source, external_id)
        );

        CREATE INDEX IF NOT EXISTS idx_account_aliases_account
            ON account_aliases(tenant_id, account_id);

        ALTER TABLE account_aliases ENABLE ROW LEVEL SECURITY;
        CREATE POLICY account_aliases_tenant_isolation
            ON account_aliases
            USING (
                tenant_id::text =
                NULLIF(current_setting('app.tenant_id', true), '')
            )
            WITH CHECK (
                tenant_id::text =
                NULLIF(current_setting('app.tenant_id', true), '')
            );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS account_aliases CASCADE")
    op.execute("""
        ALTER TABLE account_signals
            DROP COLUMN IF EXISTS source_url,
            DROP COLUMN IF EXISTS confidence,
            DROP COLUMN IF EXISTS valid_from,
            DROP COLUMN IF EXISTS valid_to;
        DROP INDEX IF EXISTS uq_accounts_tenant_canonical_domain;
        ALTER TABLE accounts
            DROP COLUMN IF EXISTS canonical_domain,
            DROP COLUMN IF EXISTS first_observed_at,
            DROP COLUMN IF EXISTS last_observed_at
    """)
