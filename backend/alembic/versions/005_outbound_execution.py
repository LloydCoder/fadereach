"""Outbound execution control plane.

Revision ID: 005_outbound_execution
Revises: 004_api_keys_provisioning
"""
from alembic import op

revision = "005_outbound_execution"
down_revision = "004_api_keys_provisioning"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS body_html TEXT NOT NULL DEFAULT '';

        CREATE TABLE IF NOT EXISTS provider_connections (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            provider_type TEXT NOT NULL,
            base_url TEXT NOT NULL,
            api_username TEXT NOT NULL,
            api_token_ciphertext TEXT NOT NULL,
            from_email TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(tenant_id, provider_type)
        );

        CREATE TABLE IF NOT EXISTS suppression_entries (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            email TEXT NOT NULL,
            reason TEXT NOT NULL,
            source TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(tenant_id, email)
        );

        CREATE TABLE IF NOT EXISTS campaign_executions (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
            provider_connection_id BIGINT NOT NULL REFERENCES provider_connections(id),
            external_campaign_id BIGINT,
            status TEXT NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued','running','succeeded','failed','cancelled')),
            recipient_count INTEGER NOT NULL DEFAULT 0,
            sent_count INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            UNIQUE(campaign_id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            campaign_id INTEGER REFERENCES campaigns(id) ON DELETE SET NULL,
            execution_id BIGINT REFERENCES campaign_executions(id) ON DELETE SET NULL,
            lead_id INTEGER REFERENCES leads(id) ON DELETE SET NULL,
            provider_message_id TEXT,
            recipient_email TEXT NOT NULL,
            subject TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            sent_at TIMESTAMPTZ
        );

        CREATE TABLE IF NOT EXISTS message_events (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            message_id BIGINT REFERENCES messages(id) ON DELETE CASCADE,
            event_type TEXT NOT NULL,
            provider_event_id TEXT,
            metadata JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(provider_event_id)
        );

        CREATE INDEX IF NOT EXISTS idx_provider_connections_tenant
            ON provider_connections(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_suppressions_tenant_email
            ON suppression_entries(tenant_id, email);
        CREATE INDEX IF NOT EXISTS idx_messages_tenant_campaign
            ON messages(tenant_id, campaign_id);
        CREATE INDEX IF NOT EXISTS idx_message_events_tenant
            ON message_events(tenant_id);

        ALTER TABLE provider_connections ENABLE ROW LEVEL SECURITY;
        ALTER TABLE suppression_entries ENABLE ROW LEVEL SECURITY;
        ALTER TABLE campaign_executions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
        ALTER TABLE message_events ENABLE ROW LEVEL SECURITY;

        CREATE POLICY provider_connections_tenant_isolation
            ON provider_connections USING (
                tenant_id::text = NULLIF(current_setting('app.tenant_id', true), '')
            ) WITH CHECK (
                tenant_id::text = NULLIF(current_setting('app.tenant_id', true), '')
            );
        CREATE POLICY suppression_entries_tenant_isolation
            ON suppression_entries USING (
                tenant_id::text = NULLIF(current_setting('app.tenant_id', true), '')
            ) WITH CHECK (
                tenant_id::text = NULLIF(current_setting('app.tenant_id', true), '')
            );
        CREATE POLICY campaign_executions_tenant_isolation
            ON campaign_executions USING (
                tenant_id::text = NULLIF(current_setting('app.tenant_id', true), '')
            ) WITH CHECK (
                tenant_id::text = NULLIF(current_setting('app.tenant_id', true), '')
            );
        CREATE POLICY messages_tenant_isolation
            ON messages USING (
                tenant_id::text = NULLIF(current_setting('app.tenant_id', true), '')
            ) WITH CHECK (
                tenant_id::text = NULLIF(current_setting('app.tenant_id', true), '')
            );
        CREATE POLICY message_events_tenant_isolation
            ON message_events USING (
                tenant_id::text = NULLIF(current_setting('app.tenant_id', true), '')
            ) WITH CHECK (
                tenant_id::text = NULLIF(current_setting('app.tenant_id', true), '')
            );
    """)


def downgrade():
    for table in ["message_events", "messages", "campaign_executions",
                  "suppression_entries", "provider_connections"]:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
