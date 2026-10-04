from pathlib import Path

MIGRATION = Path(__file__).parents[1] / "alembic" / "versions" / "027_canonical_revenue_intelligence.py"
SOURCE = MIGRATION.read_text(encoding="utf-8")

def test_phase_01_canonical_entities_are_present():
    required = ["organizations","people","products","technologies","initiatives","commercial_events","observations","evidence","signals","signal_clusters","opportunities","opportunity_hypotheses","buying_committees","sequences","messages","executions","meetings","deals","revenue","outcomes"]
    for table in required:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in SOURCE

def test_phase_01_has_tenant_isolation_and_lineage_constraints():
    assert "ENABLE ROW LEVEL SECURITY" in SOURCE
    assert "current_setting(''app.tenant_id'', true)" in SOURCE
    assert "signal_evidence" in SOURCE and "hypothesis_evidence" in SOURCE
    assert "idempotency_key" in SOURCE and "provider_message_id" in SOURCE

def test_phase_01_links_legacy_records():
    assert "ALTER TABLE leads" in SOURCE
    assert "organization_id BIGINT" in SOURCE and "person_id BIGINT" in SOURCE
    assert "ALTER TABLE campaigns" in SOURCE and "ALTER TABLE replies" in SOURCE
