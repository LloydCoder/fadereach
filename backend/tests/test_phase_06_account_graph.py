from pathlib import Path
MIGRATION = Path(__file__).parents[1] / "alembic" / "versions" / "032_account_graph.py"
SOURCE = MIGRATION.read_text(encoding="utf-8")

def test_graph_edge_contract():
    assert "account_graph_edges" in SOURCE
    assert "source_type" in SOURCE and "target_type" in SOURCE
    assert "evidence_id" in SOURCE
    assert "UNIQUE (tenant_id, source_type, source_id, relation, target_type, target_id)" in SOURCE

def test_graph_edges_are_tenant_isolated():
    assert "account_graph_edges_tenant_isolation" in SOURCE
    assert "FORCE ROW LEVEL SECURITY" in SOURCE
