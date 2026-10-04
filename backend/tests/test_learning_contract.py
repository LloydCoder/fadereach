import os
import psycopg2


def test_experiment_tables_have_rls():
    with psycopg2.connect(os.environ["MIGRATION_DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT tablename FROM pg_policies
                WHERE schemaname='public'
                  AND tablename IN ('experiments','experiment_exposures')
            """)
            assert {r[0] for r in cur.fetchall()} == {
                "experiments","experiment_exposures"
            }
