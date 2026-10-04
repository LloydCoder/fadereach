from pathlib import Path
MIGRATION = Path(__file__).parents[1] / "alembic" / "versions" / "029_signal_ingestion.py"
SOURCE = MIGRATION.read_text(encoding="utf-8")

def test_phase_03_has_source_governance():
    assert "signal_sources" in SOURCE
    assert "trust_tier" in SOURCE
    assert "schema_version" in SOURCE
    assert "signal_ingestion_runs" in SOURCE

def test_phase_03_has_normalized_signal_contract():
    for field in ["normalized_type","signal_category","source_url","source_observed_at","freshness_expires_at","raw_payload_hash","normalization_version","normalization_status"]:
        assert f"ADD COLUMN IF NOT EXISTS {field}" in SOURCE

def test_phase_03_is_tenant_isolated():
    assert "signal_sources_tenant_isolation" in SOURCE
    assert "signal_ingestion_runs_tenant_isolation" in SOURCE
    assert "FORCE ROW LEVEL SECURITY" in SOURCE
