from pathlib import Path
MIGRATION = Path(__file__).parents[1] / "alembic" / "versions" / "036_account_memory.py"
SOURCE = MIGRATION.read_text(encoding="utf-8")

def test_account_memory_is_provenance_backed():
    for field in ["memory_type","content","fingerprint","confidence","evidence_refs","source_refs","valid_from","valid_to"]:
        assert field in SOURCE
    assert "UNIQUE (tenant_id, account_id, fingerprint)" in SOURCE

def test_account_memory_is_tenant_isolated():
    assert "account_memory_entries_tenant_isolation" in SOURCE
    assert "FORCE ROW LEVEL SECURITY" in SOURCE
