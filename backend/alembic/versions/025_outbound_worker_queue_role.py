"""Give the dedicated outbound worker queue role least-privileged access.

Revision ID: 025_outbound_worker_queue_role
Revises: 024_force_tenant_rls
"""

from alembic import op

revision = "025_outbound_worker_queue_role"
down_revision = "024_force_tenant_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE campaign_executions
            ADD COLUMN IF NOT EXISTS cancel_requested BOOLEAN NOT NULL DEFAULT FALSE;

        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'fadereach_worker') THEN
                EXECUTE format('GRANT CONNECT ON DATABASE %I TO fadereach_worker', current_database());
                GRANT USAGE ON SCHEMA public TO fadereach_worker;
                GRANT SELECT, UPDATE ON execution_jobs TO fadereach_worker;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'fadereach_worker') THEN
                REVOKE SELECT, UPDATE ON execution_jobs FROM fadereach_worker;
                REVOKE USAGE ON SCHEMA public FROM fadereach_worker;
            END IF;
        END
        $$;
        """
    )
