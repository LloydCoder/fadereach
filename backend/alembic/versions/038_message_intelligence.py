"""Phase 12 message intelligence."""
from alembic import op
revision="038_message_intelligence"; down_revision="037_revenue_intelligence"; branch_labels=None; depends_on=None
def upgrade():
 op.execute("""CREATE TABLE IF NOT EXISTS message_intelligence_events (
 id BIGSERIAL PRIMARY KEY, tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
 message_id BIGINT, campaign_id BIGINT, person_id BIGINT, opportunity_id BIGINT,
 signal_type TEXT, persona TEXT, hypothesis_type TEXT, industry TEXT, country TEXT, stage TEXT,
 timing TEXT, channel TEXT, response TEXT, objection TEXT, meeting_outcome TEXT, revenue_outcome NUMERIC,
 evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb, occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 metadata JSONB NOT NULL DEFAULT '{}'::jsonb);
 ALTER TABLE message_intelligence_events ENABLE ROW LEVEL SECURITY; ALTER TABLE message_intelligence_events FORCE ROW LEVEL SECURITY;
 CREATE POLICY message_intelligence_events_tenant_isolation ON message_intelligence_events USING (tenant_id::text=NULLIF(current_setting('app.tenant_id',true),'')) WITH CHECK (tenant_id::text=NULLIF(current_setting('app.tenant_id',true),''));
 CREATE INDEX IF NOT EXISTS idx_message_intel_lookup ON message_intelligence_events(tenant_id,signal_type,persona,hypothesis_type,occurred_at DESC);""")
def downgrade(): op.execute("DROP TABLE IF EXISTS message_intelligence_events CASCADE")
