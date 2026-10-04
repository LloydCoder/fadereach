from pathlib import Path
MIGRATION = Path(__file__).parents[1] / "alembic" / "versions" / "033_why_now.py"
SOURCE = MIGRATION.read_text(encoding="utf-8")

def test_why_now_contract_is_evidence_backed():
    for field in ["what_changed","when_changed","why_matters","why_now","capability_required","confidence","unknowns","evidence_refs","signal_cluster_ids","trajectory_states"]:
        assert field in SOURCE
    assert "evidence_refs JSONB" in SOURCE

def test_why_now_is_tenant_isolated():
    assert "why_now_assessments_tenant_isolation" in SOURCE
    assert "FORCE ROW LEVEL SECURITY" in SOURCE
