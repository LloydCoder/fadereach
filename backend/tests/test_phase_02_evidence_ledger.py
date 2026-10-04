from pathlib import Path
MIGRATION = Path(__file__).parents[1] / "alembic" / "versions" / "028_evidence_ledger.py"
SOURCE = MIGRATION.read_text(encoding="utf-8")

def test_phase_02_ledger_is_append_only():
    assert "evidence_ledger_events" in SOURCE
    assert "evidence_append_only" in SOURCE
    assert "BEFORE UPDATE OR DELETE ON evidence" in SOURCE
    assert "REVOKE UPDATE, DELETE ON evidence FROM fadereach_runtime" in SOURCE

def test_phase_02_provenance_and_lineage_fields_exist():
    for field in ["source_type","fingerprint","freshness_days","status","supersedes_evidence_id"]:
        assert f"ADD COLUMN IF NOT EXISTS {field}" in SOURCE
    for relation in ["supports","contradicts","derived_from","invalidates","context"]:
        assert relation in SOURCE

def test_phase_02_backfills_existing_evidence():
    assert "migration:028_evidence_ledger" in SOURCE
    assert "COALESCE(e.content_hash, 'legacy-evidence-' || e.id::text)" in SOURCE
