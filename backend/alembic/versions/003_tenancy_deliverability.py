"""Database hardening: tenant RLS and deliverability schema reconciliation.

Revision ID: 003_tenancy_deliverability
Revises: 001_initial
"""
from alembic import op

revision = "003_tenancy_deliverability"
down_revision = "002_webhook_idempotency"
branch_labels = None
depends_on = None


TENANT_TABLES = [
    "domains",
    "leads",
    "campaigns",
    "replies",
    "billing_events",
    "audit_log",
    "workspace_members",
]


def upgrade():
    op.execute("""
        ALTER TABLE domains
            ADD COLUMN IF NOT EXISTS mx_valid BOOLEAN NOT NULL DEFAULT FALSE;
        ALTER TABLE domains
            ADD COLUMN IF NOT EXISTS deliverability_readiness INTEGER NOT NULL DEFAULT 0;

        CREATE INDEX IF NOT EXISTS idx_domains_tenant
            ON domains(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_replies_tenant_campaign
            ON replies(tenant_id, campaign_id);
        CREATE INDEX IF NOT EXISTS idx_workspace_members_tenant
            ON workspace_members(tenant_id);
    """)

    # Preserve existing values while moving product semantics away from the
    # unsupported "inbox probability" heuristic.
    op.execute("""
        UPDATE domains
        SET deliverability_readiness = GREATEST(0, LEAST(100, COALESCE(inbox_prob, 0)))
        WHERE deliverability_readiness = 0;
    """)

    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            DROP POLICY IF EXISTS {table}_tenant_isolation ON {table};
            CREATE POLICY {table}_tenant_isolation ON {table}
                USING (
                    tenant_id::text = NULLIF(current_setting('app.tenant_id', true), '')
                )
                WITH CHECK (
                    tenant_id::text = NULLIF(current_setting('app.tenant_id', true), '')
                );
            """
        )

    # The application role is intentionally separate from the migration owner.
    # Fresh Compose deployments create this role before migrations run.
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fadereach_runtime') THEN
                GRANT USAGE ON SCHEMA public TO fadereach_runtime;
                GRANT SELECT, INSERT, UPDATE, DELETE
                    ON ALL TABLES IN SCHEMA public TO fadereach_runtime;
                GRANT USAGE, SELECT, UPDATE
                    ON ALL SEQUENCES IN SCHEMA public TO fadereach_runtime;
                ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO fadereach_runtime;
                ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO fadereach_runtime;
            END IF;
        END
        $$;
    """)


def downgrade():
    for table in reversed(TENANT_TABLES):
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.execute("""
        ALTER TABLE domains
            DROP COLUMN IF EXISTS deliverability_readiness,
            DROP COLUMN IF EXISTS mx_valid;
    """)
