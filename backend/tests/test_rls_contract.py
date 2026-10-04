import os

import psycopg2
import pytest
from psycopg2.errors import InsufficientPrivilege


TENANT_TABLES = {
    "domains", "leads", "campaigns", "replies", "billing_events",
    "workspace_members", "audit_log", "api_keys", "provisioning_jobs",
    "provider_connections", "suppression_entries", "campaign_executions",
    "messages", "message_events", "lead_intelligence",
    "intelligence_signals", "demand_hypotheses", "accounts",
    "account_signals", "autopilot_runs", "ai_feedback",
    "optimization_log", "enterprise_settings", "execution_jobs", "tenant_data_policies", "account_aliases", "experiments", "experiment_exposures", "agency_client_settings", "organizations", "people", "products", "technologies", "initiatives", "commercial_events", "observations", "evidence", "signals", "signal_clusters", "opportunities", "opportunity_hypotheses", "buying_committees", "buying_committee_members", "sequences", "executions", "meetings", "deals", "revenue", "outcomes", "evidence_ledger_links", "evidence_ledger_events", "signal_sources", "signal_ingestion_runs", "signal_trajectories", "account_graph_edges", "why_now_assessments", "buying_committee_member_evidence", "account_memory_entries", "revenue_attributions", "revenue_metrics_daily", "message_intelligence_events", "personalization_claims", "ai_decision_records", "autonomy_decisions", "outbound_jobs", "execution_decisions", "provider_capabilities",
}


def test_runtime_role_cannot_bypass_rls():
    with psycopg2.connect(os.environ["MIGRATION_DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT rolsuper, rolcreaterole, rolcreatedb, rolbypassrls, rolinherit
                FROM pg_roles WHERE rolname = 'fadereach_runtime'
            """)
            assert cur.fetchone() == (False, False, False, False, False)


def test_every_tenant_table_has_rls_and_policy():
    with psycopg2.connect(os.environ["MIGRATION_DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.table_name, cls.relrowsecurity, cls.relforcerowsecurity,
                       EXISTS (
                           SELECT 1 FROM pg_policies p
                           WHERE p.schemaname = 'public'
                             AND p.tablename = c.table_name
                             AND p.policyname = c.table_name || '_tenant_isolation'
                       )
                FROM information_schema.columns c
                JOIN pg_class cls ON cls.relname = c.table_name
                JOIN pg_namespace n ON n.oid = cls.relnamespace
                                  AND n.nspname = 'public'
                WHERE c.table_schema = 'public' AND c.column_name = 'tenant_id'
                GROUP BY c.table_name, cls.relrowsecurity, cls.relforcerowsecurity
            """)
            found = {name: (rls, force_rls, policy) for name, rls, force_rls, policy in cur.fetchall()}

    assert not TENANT_TABLES - found.keys(), sorted(TENANT_TABLES - found.keys())
    assert not found.keys() - TENANT_TABLES, sorted(found.keys() - TENANT_TABLES)
    assert not [name for name in TENANT_TABLES if not all(found[name])]
    assert not [name for name in TENANT_TABLES if not found[name][1]]


def test_runtime_role_cannot_cross_tenants():
    admin_url = os.environ["MIGRATION_DATABASE_URL"]
    runtime_url = os.environ["DATABASE_URL"]

    with psycopg2.connect(admin_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tenants (id,email,name,password_hash)
                VALUES ('f2-a','f2-a@example.test','F2 A','test'),
                       ('f2-b','f2-b@example.test','F2 B','test')
                ON CONFLICT (id) DO NOTHING
            """)
            cur.execute("""
                INSERT INTO accounts (tenant_id,domain,name)
                VALUES ('f2-a','f2-a.example.test','F2 A account'),
                       ('f2-b','f2-b.example.test','F2 B account')
                ON CONFLICT (tenant_id,domain) DO NOTHING
            """)
        conn.commit()

    with psycopg2.connect(runtime_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id','f2-a',false)")
            cur.execute("SELECT domain FROM accounts ORDER BY domain")
            assert [row[0] for row in cur.fetchall()] == ["f2-a.example.test"]

    with psycopg2.connect(runtime_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id','f2-a',false)")
            with pytest.raises(InsufficientPrivilege):
                cur.execute("""
                    INSERT INTO accounts (tenant_id,domain,name)
                    VALUES ('f2-b','blocked.example.test','must fail')
                """)


def test_runtime_role_sees_no_tenant_without_context():
    runtime_url = os.environ["DATABASE_URL"]
    with psycopg2.connect(runtime_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM accounts")
            assert cur.fetchone()[0] == 0
            with pytest.raises(InsufficientPrivilege):
                cur.execute(
                    """
                    INSERT INTO accounts (tenant_id,domain,name)
                    VALUES ('f2-a','missing-context.example.test','must fail')
                    """
                )
