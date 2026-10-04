"""Add agency/client workspace hierarchy.

Revision ID: 022_agency_workspace_hierarchy
Revises: 021_learning_experiments
"""

from alembic import op

revision = "022_agency_workspace_hierarchy"
down_revision = "021_learning_experiments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE tenants
            ADD COLUMN IF NOT EXISTS parent_tenant_id TEXT REFERENCES tenants(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS tenant_type TEXT NOT NULL DEFAULT 'workspace'
                CHECK (tenant_type IN ('workspace','agency'));

        CREATE INDEX IF NOT EXISTS idx_tenants_parent
            ON tenants(parent_tenant_id);

        CREATE TABLE IF NOT EXISTS agency_client_settings (
            tenant_id TEXT PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
            agency_tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            client_name TEXT NOT NULL,
            billing_mode TEXT NOT NULL DEFAULT 'client'
                CHECK (billing_mode IN ('agency','client','managed')),
            reporting_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        ALTER TABLE agency_client_settings ENABLE ROW LEVEL SECURITY;
        CREATE POLICY agency_client_settings_tenant_isolation
            ON agency_client_settings
            USING (
                agency_tenant_id::text =
                NULLIF(current_setting('app.tenant_id', true), '')
                OR tenant_id::text =
                NULLIF(current_setting('app.tenant_id', true), '')
            )
            WITH CHECK (
                agency_tenant_id::text =
                NULLIF(current_setting('app.tenant_id', true), '')
            );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS agency_client_settings CASCADE")
    op.execute("""
        ALTER TABLE tenants
            DROP COLUMN IF EXISTS parent_tenant_id,
            DROP COLUMN IF EXISTS tenant_type
    """)
