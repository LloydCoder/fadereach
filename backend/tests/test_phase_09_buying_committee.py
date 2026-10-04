from pathlib import Path
MIGRATION = Path(__file__).parents[1] / "alembic" / "versions" / "035_buying_committee.py"
SOURCE = MIGRATION.read_text(encoding="utf-8")

def test_buying_committee_evidence_contract():
    assert "buying_committee_member_evidence" in SOURCE
    assert "role_confidence" in SOURCE
    assert "last_verified_at" in SOURCE
    assert "supports" in SOURCE and "contradicts" in SOURCE

def test_buying_committee_evidence_is_tenant_scoped():
    assert "buying_committee_member_evidence_tenant_isolation" in SOURCE
    assert "current_setting('app.tenant_id', true)" in SOURCE
