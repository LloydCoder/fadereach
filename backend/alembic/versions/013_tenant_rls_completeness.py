"""Complete RLS coverage for every tenant-owned table.

Revision ID: 013_tenant_rls_completeness
Revises: 012_enterprise_controls
"""
from alembic import op

revision = "013_tenant_rls_completeness"
down_revision = "012_enterprise_controls"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        DO $$
        DECLARE
            item RECORD;
            policy_name TEXT;
        BEGIN
            FOR item IN
                SELECT c.table_name
                FROM information_schema.columns c
                WHERE c.table_schema = 'public'
                  AND c.column_name = 'tenant_id'
                  AND c.table_name <> 'alembic_version'
                GROUP BY c.table_name
                ORDER BY c.table_name
            LOOP
                policy_name := item.table_name || '_tenant_isolation';
                EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', item.table_name);
                EXECUTE format('DROP POLICY IF EXISTS %I ON %I', policy_name, item.table_name);
                EXECUTE format(
                    'CREATE POLICY %I ON %I USING (tenant_id::text = NULLIF(current_setting(''app.tenant_id'', true), '''')) WITH CHECK (tenant_id::text = NULLIF(current_setting(''app.tenant_id'', true), ''''))',
                    policy_name,
                    item.table_name
                );
            END LOOP;
        END
        $$;
    """)


def downgrade():
    op.execute("""
        DO $$
        DECLARE
            item RECORD;
            policy_name TEXT;
        BEGIN
            FOR item IN
                SELECT c.table_name
                FROM information_schema.columns c
                WHERE c.table_schema = 'public'
                  AND c.column_name = 'tenant_id'
                  AND c.table_name <> 'alembic_version'
                GROUP BY c.table_name
            LOOP
                policy_name := item.table_name || '_tenant_isolation';
                EXECUTE format('DROP POLICY IF EXISTS %I ON %I', policy_name, item.table_name);
                EXECUTE format('ALTER TABLE %I DISABLE ROW LEVEL SECURITY', item.table_name);
            END LOOP;
        END
        $$;
    """)


