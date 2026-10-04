"""Enterprise controls foundation.

Revision ID: 012_enterprise_controls
Revises: 011_learning_attribution
"""
from alembic import op

revision = "012_enterprise_controls"
down_revision = "011_learning_attribution"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS enterprise_settings (
            tenant_id TEXT PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
            data_region TEXT NOT NULL DEFAULT 'global',
            retention_days INTEGER NOT NULL DEFAULT 365,
            audit_export_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            sso_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            sso_issuer TEXT,
            sso_client_id TEXT,
            sso_client_secret_ciphertext TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        ALTER TABLE workspace_members
            DROP CONSTRAINT IF EXISTS workspace_members_role_check;
        ALTER TABLE workspace_members
            ADD CONSTRAINT workspace_members_role_check
            CHECK (role IN ('owner','admin','manager','member','viewer'));

        CREATE INDEX IF NOT EXISTS idx_workspace_members_tenant_role
            ON workspace_members(tenant_id, role);

        ALTER TABLE enterprise_settings ENABLE ROW LEVEL SECURITY;
        CREATE POLICY enterprise_settings_tenant_isolation ON enterprise_settings
            USING (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''));

        INSERT INTO enterprise_settings (tenant_id)
        SELECT id FROM tenants
        ON CONFLICT (tenant_id) DO NOTHING;
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS enterprise_settings CASCADE")
    op.execute("ALTER TABLE workspace_members DROP CONSTRAINT IF EXISTS workspace_members_role_check")
