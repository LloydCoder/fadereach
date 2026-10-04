"""Expand enterprise security and session policy controls.

Revision ID: 023_enterprise_security_controls
Revises: 022_agency_workspace_hierarchy
"""

from alembic import op

revision = "023_enterprise_security_controls"
down_revision = "022_agency_workspace_hierarchy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE enterprise_settings
            ADD COLUMN IF NOT EXISTS mfa_required BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS session_ttl_minutes INTEGER NOT NULL DEFAULT 60,
            ADD COLUMN IF NOT EXISTS allowed_ip_cidrs JSONB NOT NULL DEFAULT '[]'::jsonb,
            ADD COLUMN IF NOT EXISTS scim_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS scim_base_url TEXT,
            ADD COLUMN IF NOT EXISTS audit_retention_days INTEGER NOT NULL DEFAULT 365;

        ALTER TABLE enterprise_settings
            ADD CONSTRAINT enterprise_session_ttl_check
            CHECK (session_ttl_minutes BETWEEN 5 AND 1440);

        ALTER TABLE enterprise_settings
            ADD CONSTRAINT enterprise_audit_retention_check
            CHECK (audit_retention_days BETWEEN 30 AND 3650);
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE enterprise_settings
            DROP CONSTRAINT IF EXISTS enterprise_session_ttl_check,
            DROP CONSTRAINT IF EXISTS enterprise_audit_retention_check;
        ALTER TABLE enterprise_settings
            DROP COLUMN IF EXISTS mfa_required,
            DROP COLUMN IF EXISTS session_ttl_minutes,
            DROP COLUMN IF EXISTS allowed_ip_cidrs,
            DROP COLUMN IF EXISTS scim_enabled,
            DROP COLUMN IF EXISTS scim_base_url,
            DROP COLUMN IF EXISTS audit_retention_days
    """)
