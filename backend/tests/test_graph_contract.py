import os

import psycopg2


def test_graph_identity_contract():
    with psycopg2.connect(os.environ["MIGRATION_DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema='public' AND table_name='account_signals'
                  AND column_name IN ('source_url','confidence','valid_from','valid_to')
            """)
            assert {r[0] for r in cur.fetchall()} == {
                "source_url","confidence","valid_from","valid_to"
            }
            cur.execute("""
                SELECT relrowsecurity FROM pg_class WHERE relname='account_aliases'
            """)
            assert cur.fetchone() == (True,)
