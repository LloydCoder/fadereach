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

from routers.integrations import _normalize_signal, _source_trust_tier

def test_signal_normalization_is_deterministic():
    assert _normalize_signal("AWS migration hiring") == ("hiring", "workforce", 45)
    assert _normalize_signal("security_incident") == ("security_incident", "security", 30)
    assert _normalize_signal("unknown_custom_signal")[1] == "other"

def test_source_trust_tier_contract():
    assert _source_trust_tier("tads") == "T1"
    assert _source_trust_tier("sdea") == "T1"
    assert _source_trust_tier("reconos") == "T2"
