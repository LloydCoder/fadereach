import os
import psycopg2


def test_enterprise_security_columns():
    with psycopg2.connect(os.environ["MIGRATION_DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema='public' AND table_name='enterprise_settings'
                  AND column_name IN (
                    'mfa_required','session_ttl_minutes','allowed_ip_cidrs',
                    'scim_enabled','scim_base_url','audit_retention_days'
                  )
            """)
            assert {r[0] for r in cur.fetchall()} == {
                "mfa_required","session_ttl_minutes","allowed_ip_cidrs",
                "scim_enabled","scim_base_url","audit_retention_days"
            }
