from pathlib import Path
S=(Path(__file__).parents[1]/"alembic/versions/042_durable_execution.py").read_text()
def test_durable_job_contract(): assert "SKIP LOCKED" in S or "outbound_jobs" in S
def test_idempotency_contract(): assert "idempotency_key" in S and "UNIQUE(tenant_id,idempotency_key)" in S
