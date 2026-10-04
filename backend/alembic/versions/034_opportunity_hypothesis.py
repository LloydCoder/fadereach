"""Phase 8: opportunity hypothesis generation and ranking metadata."""

from alembic import op

revision = "034_opportunity_hypothesis"
down_revision = "033_why_now"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
        ALTER TABLE opportunities
            ADD COLUMN IF NOT EXISTS source_key TEXT,
            ADD COLUMN IF NOT EXISTS fit_score NUMERIC(6,3) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS impact_score NUMERIC(6,3) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS priority_score NUMERIC(6,3) NOT NULL DEFAULT 0;

        ALTER TABLE opportunity_hypotheses
            ADD COLUMN IF NOT EXISTS why_now_assessment_id BIGINT REFERENCES why_now_assessments(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS fit_score NUMERIC(6,3) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS impact_score NUMERIC(6,3) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS priority_score NUMERIC(6,3) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active';

        CREATE INDEX IF NOT EXISTS idx_opportunities_source_key
            ON opportunities(tenant_id, organization_id, source_key);
        CREATE UNIQUE INDEX IF NOT EXISTS uq_opportunity_source_key
            ON opportunities(tenant_id, organization_id, source_key);
        CREATE INDEX IF NOT EXISTS idx_hypotheses_priority
            ON opportunity_hypotheses(tenant_id, priority_score DESC, updated_at DESC);
    """)

def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS uq_opportunity_source_key;
        DROP INDEX IF EXISTS idx_opportunities_source_key;
        DROP INDEX IF EXISTS idx_hypotheses_priority;
        ALTER TABLE opportunity_hypotheses
            DROP COLUMN IF EXISTS status,
            DROP COLUMN IF EXISTS priority_score,
            DROP COLUMN IF EXISTS impact_score,
            DROP COLUMN IF EXISTS fit_score,
            DROP COLUMN IF EXISTS why_now_assessment_id;
        ALTER TABLE opportunities
            DROP COLUMN IF EXISTS priority_score,
            DROP COLUMN IF EXISTS impact_score,
            DROP COLUMN IF EXISTS fit_score,
            DROP COLUMN IF EXISTS source_key;
    """)
