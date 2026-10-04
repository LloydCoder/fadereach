"""Phase 19 experimentation hardening."""
from alembic import op
revision="045_experimentation_hardening"; down_revision="044_provider_mesh"; branch_labels=None; depends_on=None
def upgrade(): op.execute("""ALTER TABLE experiments ADD COLUMN IF NOT EXISTS guardrails JSONB NOT NULL DEFAULT '{}'::jsonb; ALTER TABLE experiments ADD COLUMN IF NOT EXISTS analysis_plan JSONB NOT NULL DEFAULT '{}'::jsonb; ALTER TABLE experiment_exposures ADD COLUMN IF NOT EXISTS evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb; CREATE INDEX IF NOT EXISTS idx_experiment_exposure_outcome_time ON experiment_exposures(tenant_id,experiment_id,outcome_at);""")
def downgrade(): op.execute("""ALTER TABLE experiments DROP COLUMN IF EXISTS analysis_plan; ALTER TABLE experiments DROP COLUMN IF EXISTS guardrails; ALTER TABLE experiment_exposures DROP COLUMN IF EXISTS evidence_refs;""")
