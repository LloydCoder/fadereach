"""Add experiment exposure and revenue attribution primitives.

Revision ID: 021_learning_experiments
Revises: 020_autopilot_governance
"""

from alembic import op

revision = "021_learning_experiments"
down_revision = "020_autopilot_governance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS experiments (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            hypothesis TEXT NOT NULL,
            dimension TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft','running','paused','completed')),
            variants JSONB NOT NULL,
            primary_metric TEXT NOT NULL,
            minimum_sample_size INTEGER NOT NULL DEFAULT 100,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS experiment_exposures (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            experiment_id BIGINT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
            subject_type TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            variant TEXT NOT NULL,
            exposed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            outcome TEXT,
            outcome_value NUMERIC,
            outcome_at TIMESTAMPTZ,
            UNIQUE(experiment_id, subject_type, subject_id)
        );

        CREATE INDEX IF NOT EXISTS idx_experiment_exposures_metric
            ON experiment_exposures(tenant_id, experiment_id, variant, outcome);

        ALTER TABLE experiments ENABLE ROW LEVEL SECURITY;
        ALTER TABLE experiment_exposures ENABLE ROW LEVEL SECURITY;

        CREATE POLICY experiments_tenant_isolation ON experiments
            USING (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''));
        CREATE POLICY experiment_exposures_tenant_isolation ON experiment_exposures
            USING (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''));
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS experiment_exposures CASCADE")
    op.execute("DROP TABLE IF EXISTS experiments CASCADE")
