import os
import psycopg2


def test_agency_schema():
    with psycopg2.connect(os.environ["MIGRATION_DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema='public' AND table_name='tenants'
                  AND column_name IN ('parent_tenant_id','tenant_type')
            """)
            assert {r[0] for r in cur.fetchall()} == {"parent_tenant_id","tenant_type"}
            cur.execute("""
                SELECT relrowsecurity FROM pg_class
                WHERE relname='agency_client_settings'
            """)
            assert cur.fetchone() == (True,)
