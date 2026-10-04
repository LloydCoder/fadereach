"""Force tenant RLS for owners as well as runtime roles.

Revision ID: 024_force_tenant_rls
Revises: 023_enterprise_security_controls
"""

from alembic import op

revision = "024_force_tenant_rls"
down_revision = "023_enterprise_security_controls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            item RECORD;
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
                EXECUTE format(
                    'ALTER TABLE %I FORCE ROW LEVEL SECURITY',
                    item.table_name
                );
            END LOOP;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            item RECORD;
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
                EXECUTE format(
                    'ALTER TABLE %I NO FORCE ROW LEVEL SECURITY',
                    item.table_name
                );
            END LOOP;
        END
        $$;
        """
    )
