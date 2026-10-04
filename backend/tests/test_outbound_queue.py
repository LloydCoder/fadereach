import os

import psycopg2


def test_durable_execution_queue_allows_multiple_attempts_per_campaign():
    url = os.environ["MIGRATION_DATABASE_URL"]
    with psycopg2.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tenants (id,email,name,password_hash)
                VALUES ('f4-tenant','f4@example.test','F4','test')
                ON CONFLICT (id) DO NOTHING
            """)
            cur.execute("""
                INSERT INTO campaigns (tenant_id,name,subject)
                VALUES ('f4-tenant','F4 durable','Durable')
                RETURNING id
            """)
            campaign_id = cur.fetchone()[0]
            cur.execute("""
                INSERT INTO provider_connections
                    (tenant_id,provider_type,base_url,api_username,
                     api_token_ciphertext,from_email)
                VALUES ('f4-tenant','listmonk','http://listmonk.test',
                        'api-user','ciphertext','from@example.test')
                RETURNING id
            """)
            provider_id = cur.fetchone()[0]
            cur.execute("""
                INSERT INTO campaign_executions
                    (tenant_id,campaign_id,provider_connection_id,status)
                VALUES ('f4-tenant',%s,%s,'queued')
                RETURNING id
            """, (campaign_id, provider_id))
            first_execution = cur.fetchone()[0]
            cur.execute("""
                INSERT INTO campaign_executions
                    (tenant_id,campaign_id,provider_connection_id,status)
                VALUES ('f4-tenant',%s,%s,'queued')
                RETURNING id
            """, (campaign_id, provider_id))
            second_execution = cur.fetchone()[0]
            assert first_execution != second_execution

            cur.execute("""
                INSERT INTO execution_jobs (tenant_id,execution_id)
                VALUES ('f4-tenant',%s),('f4-tenant',%s)
            """, (first_execution, second_execution))
        conn.commit()


def test_execution_jobs_are_tenant_isolated():
    url = os.environ["MIGRATION_DATABASE_URL"]
    with psycopg2.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT relrowsecurity
                FROM pg_class
                WHERE relname='execution_jobs'
            """)
            assert cur.fetchone() == (True,)
            cur.execute("""
                SELECT policyname
                FROM pg_policies
                WHERE tablename='execution_jobs'
                  AND policyname='execution_jobs_tenant_isolation'
            """)
            assert cur.fetchone() is not None
