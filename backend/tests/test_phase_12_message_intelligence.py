from pathlib import Path
S=(Path(__file__).parents[1]/"alembic/versions/038_message_intelligence.py").read_text()
def test_contract(): assert "message_intelligence_events" in S and "evidence_refs" in S and "ROW LEVEL SECURITY" in S
