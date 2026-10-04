import os

import psycopg2


def test_data_governance_schema_and_rls():
    with psycopg2.connect(os.environ["MIGRATION_DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema='public' AND table_name='leads'
                  AND column_name IN (
                    'lawful_basis','processing_purpose','source',
                    'source_url','collected_at','retention_until'
                  )
            """)
            assert {row[0] for row in cur.fetchall()} == {
                "lawful_basis","processing_purpose","source",
                "source_url","collected_at","retention_until"
            }
            cur.execute("""
                SELECT relrowsecurity FROM pg_class
                WHERE relname='tenant_data_policies'
            """)
            assert cur.fetchone() == (True,)
