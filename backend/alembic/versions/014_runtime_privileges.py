"""Grant runtime database privileges after migrations.

Revision ID: 014_runtime_privileges
Revises: 013_tenant_rls_completeness

The application runtime role is deliberately not allowed to own schema
objects or run migrations. The migration role remains authoritative for DDL.
"""

from alembic import op

revision = "014_runtime_privileges"
down_revision = "013_tenant_rls_completeness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'fadereach_runtime') THEN
                GRANT USAGE ON SCHEMA public TO fadereach_runtime;
                GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO fadereach_runtime;
                GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO fadereach_runtime;

                ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO fadereach_runtime;
                -- Apply defaults for objects created by the migration role that
                -- is executing this migration. Do not hard-code a production
                -- role name; migration and runtime roles are deployment-configured.
                ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO fadereach_runtime;
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
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'fadereach_runtime') THEN
                ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM fadereach_runtime;
                ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    REVOKE USAGE, SELECT, UPDATE ON SEQUENCES FROM fadereach_runtime;
                REVOKE SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM fadereach_runtime;
                REVOKE USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public FROM fadereach_runtime;
                REVOKE USAGE ON SCHEMA public FROM fadereach_runtime;
            END IF;
        END
        $$;
        """
    )
