"""Add API key persistence and provisioning job queue.

Revision ID: 004_api_keys_provisioning
Revises: 003_tenancy_deliverability
"""
from alembic import op

revision = "004_api_keys_provisioning"
down_revision = "003_tenancy_deliverability"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id SERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            description TEXT,
            key_hash TEXT UNIQUE NOT NULL,
            key_prefix TEXT NOT NULL,
            scopes JSONB NOT NULL,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_used TIMESTAMPTZ
        );

        CREATE INDEX IF NOT EXISTS idx_api_keys_tenant
            ON api_keys(tenant_id);

        CREATE TABLE IF NOT EXISTS provisioning_jobs (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            job_type TEXT NOT NULL,
            payload JSONB NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','running','succeeded','failed','cancelled')),
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ
        );

        CREATE INDEX IF NOT EXISTS idx_provisioning_jobs_status_created
            ON provisioning_jobs(status, created_at);
        CREATE INDEX IF NOT EXISTS idx_provisioning_jobs_tenant
            ON provisioning_jobs(tenant_id);
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS provisioning_jobs")
    op.execute("DROP TABLE IF EXISTS api_keys")
