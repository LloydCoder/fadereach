from pathlib import Path
MIGRATION = Path(__file__).parents[1] / "alembic" / "versions" / "034_opportunity_hypothesis.py"
SOURCE = MIGRATION.read_text(encoding="utf-8")

def test_opportunity_ranking_metadata():
    for field in ["source_key","fit_score","impact_score","priority_score"]:
        assert field in SOURCE

def test_hypothesis_links_why_now():
    assert "why_now_assessment_id" in SOURCE
    assert "uq_opportunity_source_key" in SOURCE
