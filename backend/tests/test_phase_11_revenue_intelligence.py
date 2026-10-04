from pathlib import Path
MIGRATION = Path(__file__).parents[1] / "alembic" / "versions" / "037_revenue_intelligence.py"
SOURCE = MIGRATION.read_text(encoding="utf-8")

def test_revenue_lineage_contract():
    assert "revenue_attributions" in SOURCE
    for value in ["sourced","influenced","assisted","first_touch","last_touch"]:
        assert value in SOURCE
    assert "evidence_refs" in SOURCE

def test_daily_revenue_metrics_contract():
    assert "revenue_metrics_daily" in SOURCE
    assert "signal_to_opportunity_rate" in SOURCE
    assert "meeting_to_won_rate" in SOURCE
