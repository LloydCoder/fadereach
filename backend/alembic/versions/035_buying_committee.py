"""Phase 9: buying committee inference hardening."""

from alembic import op

revision = "035_buying_committee"
down_revision = "034_opportunity_hypothesis"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
        ALTER TABLE buying_committee_members
            ADD COLUMN IF NOT EXISTS role_confidence NUMERIC(5,4) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'inferred',
            ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMPTZ;

        CREATE TABLE IF NOT EXISTS buying_committee_member_evidence (
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            member_id BIGINT NOT NULL REFERENCES buying_committee_members(id) ON DELETE CASCADE,
            evidence_id BIGINT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
            relation TEXT NOT NULL DEFAULT 'supports'
                CHECK (relation IN ('supports','contradicts','context')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (member_id, evidence_id, relation)
        );

        CREATE INDEX IF NOT EXISTS idx_committee_members_role
            ON buying_committee_members(tenant_id, role, confidence DESC);
        CREATE INDEX IF NOT EXISTS idx_committee_member_evidence
            ON buying_committee_member_evidence(evidence_id);

        ALTER TABLE buying_committee_member_evidence ENABLE ROW LEVEL SECURITY;
        ALTER TABLE buying_committee_member_evidence FORCE ROW LEVEL SECURITY;

        CREATE POLICY buying_committee_member_evidence_tenant_isolation
            ON buying_committee_member_evidence
            USING (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''))
            WITH CHECK (tenant_id::text = NULLIF(current_setting('app.tenant_id', true), ''));
    """)

def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS buying_committee_member_evidence CASCADE;
        DROP INDEX IF EXISTS idx_committee_members_role;
        ALTER TABLE buying_committee_members
            DROP COLUMN IF EXISTS last_verified_at,
            DROP COLUMN IF EXISTS status,
            DROP COLUMN IF EXISTS role_confidence;
    """)
