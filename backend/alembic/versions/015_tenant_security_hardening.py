"""Harden the application database role and tenant RLS contract.

Revision ID: 015_tenant_security_hardening
Revises: 014_runtime_privileges
"""

from alembic import op

revision = "015_tenant_security_hardening"
down_revision = "014_runtime_privileges"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT FROM pg_roles WHERE rolname = 'fadereach_runtime'
            ) THEN
                RAISE EXCEPTION 'fadereach_runtime role must exist before migrations run';
            END IF;

            ALTER ROLE fadereach_runtime
                NOSUPERUSER NOCREATEDB NOCREATEROLE
                NOREPLICATION NOBYPASSRLS NOINHERIT;
        END
        $$;
    """)

    op.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC;")
    op.execute("REVOKE CREATE ON SCHEMA public FROM fadereach_runtime;")
    op.execute("""
        REVOKE TRUNCATE, REFERENCES, TRIGGER
        ON ALL TABLES IN SCHEMA public
        FROM fadereach_runtime;
    """)

    op.execute("""
        DO $$
        DECLARE
            item RECORD;
            policy_name TEXT;
        BEGIN
            FOR item IN
                SELECT c.table_name
                FROM information_schema.columns c
                JOIN information_schema.tables t
                  ON t.table_schema = c.table_schema
                 AND t.table_name = c.table_name
                WHERE c.table_schema = 'public'
                  AND t.table_type = 'BASE TABLE'
                  AND c.column_name = 'tenant_id'
                  AND c.table_name <> 'alembic_version'
                GROUP BY c.table_name
                ORDER BY c.table_name
            LOOP
                policy_name := item.table_name || '_tenant_isolation';
                EXECUTE format(
                    'ALTER TABLE %I ENABLE ROW LEVEL SECURITY',
                    item.table_name
                );
                EXECUTE format(
                    'DROP POLICY IF EXISTS %I ON %I',
                    policy_name, item.table_name
                );
                EXECUTE format(
                    'CREATE POLICY %I ON %I
                       USING (tenant_id::text = NULLIF(current_setting(''app.tenant_id'', true), ''''))
                       WITH CHECK (tenant_id::text = NULLIF(current_setting(''app.tenant_id'', true), ''''))',
                    policy_name, item.table_name
                );
            END LOOP;
        END
        $$;
    """)


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'fadereach_runtime') THEN
                ALTER ROLE fadereach_runtime INHERIT NOBYPASSRLS;
            END IF;
        END
        $$;
    """)
