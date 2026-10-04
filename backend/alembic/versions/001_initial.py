"""Initial FadeReach control-plane schema.

Revision ID: 001_initial
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS tenants (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        company TEXT,
        password_hash TEXT NOT NULL,
        plan TEXT NOT NULL DEFAULT 'trial',
        status TEXT NOT NULL DEFAULT 'trial',
        trial_ends_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '14 days',
        listmonk_url TEXT,
        listmonk_port INTEGER,
        emails_sent_mo INTEGER NOT NULL DEFAULT 0,
        contacts_count INTEGER NOT NULL DEFAULT 0,
        onboarded BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS domains (
        id SERIAL PRIMARY KEY,
        tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        domain TEXT NOT NULL,
        spf_valid BOOLEAN NOT NULL DEFAULT FALSE,
        dkim_valid BOOLEAN NOT NULL DEFAULT FALSE,
        dmarc_valid BOOLEAN NOT NULL DEFAULT FALSE,
        warmup_day INTEGER NOT NULL DEFAULT 0,
        warmup_status TEXT NOT NULL DEFAULT 'not_started',
        daily_limit INTEGER NOT NULL DEFAULT 5,
        sent_today INTEGER NOT NULL DEFAULT 0,
        bounce_rate NUMERIC NOT NULL DEFAULT 0,
        complaint_rate NUMERIC NOT NULL DEFAULT 0,
        health_score INTEGER NOT NULL DEFAULT 0,
        inbox_prob INTEGER NOT NULL DEFAULT 0,
        blacklisted BOOLEAN NOT NULL DEFAULT FALSE,
        added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        last_checked TIMESTAMPTZ
    );
    CREATE UNIQUE INDEX IF NOT EXISTS uq_domains_tenant_domain ON domains(tenant_id, domain);
    CREATE TABLE IF NOT EXISTS leads (
        id SERIAL PRIMARY KEY,
        tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        email TEXT NOT NULL,
        first_name TEXT,
        last_name TEXT,
        company TEXT,
        title TEXT,
        domain TEXT,
        linkedin_url TEXT,
        industry TEXT,
        company_size TEXT,
        location TEXT,
        status TEXT NOT NULL DEFAULT 'uncontacted',
        verify_status TEXT NOT NULL DEFAULT 'unverified',
        verify_score INTEGER NOT NULL DEFAULT 0,
        icp_score INTEGER NOT NULL DEFAULT 0,
        ai_first_line TEXT,
        ai_hook TEXT,
        ai_score INTEGER NOT NULL DEFAULT 0,
        signal_type TEXT,
        signal_data JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE UNIQUE INDEX IF NOT EXISTS uq_leads_tenant_email ON leads(tenant_id, email);
    CREATE INDEX IF NOT EXISTS idx_leads_tenant ON leads(tenant_id);
    CREATE TABLE IF NOT EXISTS campaigns (
        id SERIAL PRIMARY KEY,
        tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        subject TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'draft',
        product TEXT,
        target_segment TEXT,
        sequence_steps INTEGER NOT NULL DEFAULT 4,
        emails_sent INTEGER NOT NULL DEFAULT 0,
        opens INTEGER NOT NULL DEFAULT 0,
        clicks INTEGER NOT NULL DEFAULT 0,
        replies INTEGER NOT NULL DEFAULT 0,
        bounces INTEGER NOT NULL DEFAULT 0,
        unsubscribes INTEGER NOT NULL DEFAULT 0,
        audit_score INTEGER,
        audit_issues JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_campaigns_tenant ON campaigns(tenant_id);
    CREATE TABLE IF NOT EXISTS replies (
        id SERIAL PRIMARY KEY,
        tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        campaign_id INTEGER REFERENCES campaigns(id) ON DELETE SET NULL,
        lead_id INTEGER REFERENCES leads(id) ON DELETE SET NULL,
        from_email TEXT NOT NULL,
        subject TEXT,
        body TEXT,
        intent TEXT NOT NULL DEFAULT 'unknown',
        sentiment TEXT NOT NULL DEFAULT 'neutral',
        is_hot BOOLEAN NOT NULL DEFAULT FALSE,
        is_read BOOLEAN NOT NULL DEFAULT FALSE,
        sequence_step INTEGER,
        received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_replies_tenant ON replies(tenant_id);
    CREATE TABLE IF NOT EXISTS billing_events (
        id SERIAL PRIMARY KEY,
        tenant_id TEXT REFERENCES tenants(id) ON DELETE CASCADE,
        event_type TEXT NOT NULL,
        provider TEXT NOT NULL,
        amount NUMERIC,
        currency TEXT,
        metadata JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS audit_log (
        id SERIAL PRIMARY KEY,
        actor TEXT NOT NULL,
        tenant_id TEXT,
        action TEXT NOT NULL,
        resource TEXT,
        metadata JSONB,
        ip_address INET,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS workspace_members (
        id SERIAL PRIMARY KEY,
        tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        email TEXT NOT NULL,
        name TEXT,
        role TEXT NOT NULL DEFAULT 'viewer',
        status TEXT NOT NULL DEFAULT 'pending',
        invited_by TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        last_active TIMESTAMPTZ,
        UNIQUE(tenant_id, email)
    );
    """)


def downgrade():
    for table in ["workspace_members", "audit_log", "billing_events", "replies", "campaigns", "leads", "domains", "tenants"]:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
