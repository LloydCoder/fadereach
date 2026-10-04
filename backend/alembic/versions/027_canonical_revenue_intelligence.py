"""Phase 1: canonical revenue-intelligence data model.

Introduces stable, tenant-scoped entities for the full commercial lineage:
organization/account/person -> product/technology/initiative -> event/observation/
evidence/signal/cluster -> opportunity/hypothesis/buying committee -> campaign/
sequence/message/execution/reply/meeting/deal/revenue/outcome.

The existing FadeReach tables remain backward compatible; this migration adds the
canonical spine and links existing lead/campaign/reply records into it.
"""

from alembic import op

revision = "027_canonical_revenue_model"
down_revision = "026_compliance_governance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            external_id TEXT,
            name TEXT NOT NULL,
            legal_name TEXT,
            website TEXT,
            domain TEXT,
            industry TEXT,
            employee_count INTEGER,
            country_code TEXT,
            region TEXT,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active','inactive','prospect','customer','former_customer','unknown')),
            attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (tenant_id, external_id)
        );

        CREATE TABLE IF NOT EXISTS people (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            organization_id BIGINT REFERENCES organizations(id) ON DELETE SET NULL,
            external_id TEXT,
            email TEXT,
            first_name TEXT,
            last_name TEXT,
            title TEXT,
            seniority TEXT,
            department TEXT,
            linkedin_url TEXT,
            country_code TEXT,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active','inactive','unverified','suppressed','unknown')),
            attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (tenant_id, external_id)
        );

        CREATE TABLE IF NOT EXISTS products (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            external_id TEXT,
            name TEXT NOT NULL,
            category TEXT,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('draft','active','retired')),
            attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (tenant_id, external_id)
        );

        CREATE TABLE IF NOT EXISTS technologies (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            organization_id BIGINT REFERENCES organizations(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            category TEXT,
            version TEXT,
            first_seen_at TIMESTAMPTZ,
            last_seen_at TIMESTAMPTZ,
            attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (tenant_id, organization_id, name)
        );

        CREATE TABLE IF NOT EXISTS initiatives (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            organization_id BIGINT REFERENCES organizations(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            initiative_type TEXT,
            status TEXT NOT NULL DEFAULT 'suspected'
                CHECK (status IN ('suspected','active','paused','completed','cancelled','unknown')),
            started_at TIMESTAMPTZ,
            ended_at TIMESTAMPTZ,
            confidence NUMERIC(5,4) NOT NULL DEFAULT 0
                CHECK (confidence >= 0 AND confidence <= 1),
            attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS commercial_events (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            organization_id BIGINT REFERENCES organizations(id) ON DELETE CASCADE,
            person_id BIGINT REFERENCES people(id) ON DELETE SET NULL,
            event_type TEXT NOT NULL,
            external_id TEXT,
            occurred_at TIMESTAMPTZ NOT NULL,
            source TEXT NOT NULL,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (tenant_id, source, external_id)
        );

        CREATE TABLE IF NOT EXISTS observations (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            organization_id BIGINT REFERENCES organizations(id) ON DELETE CASCADE,
            event_id BIGINT REFERENCES commercial_events(id) ON DELETE SET NULL,
            observation_type TEXT NOT NULL,
            value JSONB NOT NULL DEFAULT '{}'::jsonb,
            observed_at TIMESTAMPTZ NOT NULL,
            collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            source TEXT NOT NULL,
            fingerprint TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (tenant_id, fingerprint)
        );

        CREATE TABLE IF NOT EXISTS evidence (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            observation_id BIGINT REFERENCES observations(id) ON DELETE SET NULL,
            source TEXT NOT NULL,
            source_ref TEXT,
            source_url TEXT,
            claim TEXT NOT NULL,
            evidence_type TEXT NOT NULL DEFAULT 'observation'
                CHECK (evidence_type IN ('observation','document','api','record','human','derived')),
            observed_at TIMESTAMPTZ,
            collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMPTZ,
            quality NUMERIC(5,4) NOT NULL DEFAULT 0
                CHECK (quality >= 0 AND quality <= 1),
            confidence NUMERIC(5,4) NOT NULL DEFAULT 0
                CHECK (confidence >= 0 AND confidence <= 1),
            content_hash TEXT,
            provenance JSONB NOT NULL DEFAULT '{}'::jsonb,
            contradiction_of BIGINT REFERENCES evidence(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS signals (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            organization_id BIGINT REFERENCES organizations(id) ON DELETE CASCADE,
            initiative_id BIGINT REFERENCES initiatives(id) ON DELETE SET NULL,
            signal_type TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'active'
                CHECK (state IN ('candidate','active','decayed','reversed','superseded','invalid')),
            strength NUMERIC(6,3) NOT NULL DEFAULT 0,
            confidence NUMERIC(5,4) NOT NULL DEFAULT 0
                CHECK (confidence >= 0 AND confidence <= 1),
            first_seen_at TIMESTAMPTZ NOT NULL,
            last_seen_at TIMESTAMPTZ NOT NULL,
            expires_at TIMESTAMPTZ,
            attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS signal_evidence (
            signal_id BIGINT NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
            evidence_id BIGINT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
            contribution NUMERIC(6,3) NOT NULL DEFAULT 0,
            PRIMARY KEY (signal_id, evidence_id)
        );

        CREATE TABLE IF NOT EXISTS signal_clusters (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            organization_id BIGINT REFERENCES organizations(id) ON DELETE CASCADE,
            cluster_type TEXT NOT NULL,
            convergence_score NUMERIC(6,3) NOT NULL DEFAULT 0,
            confidence NUMERIC(5,4) NOT NULL DEFAULT 0
                CHECK (confidence >= 0 AND confidence <= 1),
            independent_source_count INTEGER NOT NULL DEFAULT 0
                CHECK (independent_source_count >= 0),
            state TEXT NOT NULL DEFAULT 'active'
                CHECK (state IN ('candidate','active','decayed','invalid')),
            first_seen_at TIMESTAMPTZ,
            last_seen_at TIMESTAMPTZ,
            attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS signal_cluster_members (
            cluster_id BIGINT NOT NULL REFERENCES signal_clusters(id) ON DELETE CASCADE,
            signal_id BIGINT NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
            contribution NUMERIC(6,3) NOT NULL DEFAULT 0,
            PRIMARY KEY (cluster_id, signal_id)
        );

        CREATE TABLE IF NOT EXISTS opportunities (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            organization_id BIGINT REFERENCES organizations(id) ON DELETE CASCADE,
            product_id BIGINT REFERENCES products(id) ON DELETE SET NULL,
            name TEXT NOT NULL,
            stage TEXT NOT NULL DEFAULT 'identified'
                CHECK (stage IN ('identified','qualified','engaged','meeting','proposal','negotiation','won','lost','disqualified')),
            source TEXT NOT NULL DEFAULT 'intelligence',
            score NUMERIC(6,3) NOT NULL DEFAULT 0,
            confidence NUMERIC(5,4) NOT NULL DEFAULT 0
                CHECK (confidence >= 0 AND confidence <= 1),
            estimated_value NUMERIC(18,2),
            currency TEXT,
            buying_window_start TIMESTAMPTZ,
            buying_window_end TIMESTAMPTZ,
            closed_at TIMESTAMPTZ,
            attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS opportunity_hypotheses (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            opportunity_id BIGINT NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
            hypothesis_type TEXT NOT NULL,
            statement TEXT NOT NULL,
            capability TEXT,
            why_now TEXT,
            confidence NUMERIC(5,4) NOT NULL DEFAULT 0
                CHECK (confidence >= 0 AND confidence <= 1),
            unknowns JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS hypothesis_evidence (
            hypothesis_id BIGINT NOT NULL REFERENCES opportunity_hypotheses(id) ON DELETE CASCADE,
            evidence_id BIGINT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
            PRIMARY KEY (hypothesis_id, evidence_id)
        );

        CREATE TABLE IF NOT EXISTS buying_committees (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            opportunity_id BIGINT NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
            status TEXT NOT NULL DEFAULT 'forming'
                CHECK (status IN ('forming','active','complete','blocked','unknown')),
            confidence NUMERIC(5,4) NOT NULL DEFAULT 0
                CHECK (confidence >= 0 AND confidence <= 1),
            attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (tenant_id, opportunity_id)
        );

        CREATE TABLE IF NOT EXISTS buying_committee_members (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            committee_id BIGINT NOT NULL REFERENCES buying_committees(id) ON DELETE CASCADE,
            person_id BIGINT NOT NULL REFERENCES people(id) ON DELETE CASCADE,
            role TEXT NOT NULL
                CHECK (role IN ('economic_buyer','champion','technical_buyer','security','procurement','finance','influencer','blocker','unknown')),
            influence NUMERIC(5,4) NOT NULL DEFAULT 0
                CHECK (influence >= 0 AND influence <= 1),
            confidence NUMERIC(5,4) NOT NULL DEFAULT 0
                CHECK (confidence >= 0 AND confidence <= 1),
            evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
            UNIQUE (committee_id, person_id)
        );

        CREATE TABLE IF NOT EXISTS sequences (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            campaign_id INTEGER REFERENCES campaigns(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft','active','paused','completed','archived')),
            version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
            policy_version TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        -- messages already exists in migration 005_outbound_execution.
        -- Extend it instead of introducing a second canonical table.
        ALTER TABLE messages
            ADD COLUMN IF NOT EXISTS sequence_id BIGINT,
            ADD COLUMN IF NOT EXISTS person_id BIGINT REFERENCES people(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS opportunity_id BIGINT REFERENCES opportunities(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS body TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1,
            ADD COLUMN IF NOT EXISTS personalization_evidence JSONB NOT NULL DEFAULT '[]'::jsonb;

        CREATE TABLE IF NOT EXISTS executions (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            message_id BIGINT REFERENCES messages(id) ON DELETE SET NULL,
            provider TEXT,
            provider_message_id TEXT,
            status TEXT NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued','leased','sending','sent','delivered','bounced','failed','cancelled')),
            idempotency_key TEXT NOT NULL,
            attempt INTEGER NOT NULL DEFAULT 0 CHECK (attempt >= 0),
            scheduled_at TIMESTAMPTZ,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            result JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (tenant_id, idempotency_key)
        );

        CREATE TABLE IF NOT EXISTS meetings (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            opportunity_id BIGINT REFERENCES opportunities(id) ON DELETE SET NULL,
            person_id BIGINT REFERENCES people(id) ON DELETE SET NULL,
            execution_id BIGINT REFERENCES executions(id) ON DELETE SET NULL,
            scheduled_at TIMESTAMPTZ NOT NULL,
            status TEXT NOT NULL DEFAULT 'scheduled'
                CHECK (status IN ('scheduled','held','no_show','cancelled')),
            outcome TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS deals (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            opportunity_id BIGINT REFERENCES opportunities(id) ON DELETE SET NULL,
            name TEXT NOT NULL,
            stage TEXT NOT NULL DEFAULT 'open'
                CHECK (stage IN ('open','won','lost')),
            amount NUMERIC(18,2),
            currency TEXT,
            opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            closed_at TIMESTAMPTZ,
            attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
            UNIQUE (tenant_id, opportunity_id)
        );

        CREATE TABLE IF NOT EXISTS revenue (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            deal_id BIGINT REFERENCES deals(id) ON DELETE SET NULL,
            recognized_at TIMESTAMPTZ NOT NULL,
            amount NUMERIC(18,2) NOT NULL,
            currency TEXT NOT NULL,
            revenue_type TEXT NOT NULL DEFAULT 'recognized'
                CHECK (revenue_type IN ('booked','recognized','recurring','expansion','contraction','refund')),
            external_id TEXT,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            UNIQUE (tenant_id, external_id)
        );

        CREATE TABLE IF NOT EXISTS outcomes (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            opportunity_id BIGINT REFERENCES opportunities(id) ON DELETE SET NULL,
            execution_id BIGINT REFERENCES executions(id) ON DELETE SET NULL,
            meeting_id BIGINT REFERENCES meetings(id) ON DELETE SET NULL,
            outcome_type TEXT NOT NULL,
            value NUMERIC(18,2),
            currency TEXT,
            occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            attributes JSONB NOT NULL DEFAULT '{}'::jsonb
        );

        ALTER TABLE leads
            ADD COLUMN IF NOT EXISTS organization_id BIGINT REFERENCES organizations(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS person_id BIGINT REFERENCES people(id) ON DELETE SET NULL;

        ALTER TABLE campaigns
            ADD COLUMN IF NOT EXISTS opportunity_id BIGINT REFERENCES opportunities(id) ON DELETE SET NULL;

        ALTER TABLE replies
            ADD COLUMN IF NOT EXISTS person_id BIGINT REFERENCES people(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS opportunity_id BIGINT REFERENCES opportunities(id) ON DELETE SET NULL;
        CREATE INDEX IF NOT EXISTS idx_messages_tenant_status
            ON messages(tenant_id, status, created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_organizations_tenant_domain ON organizations(tenant_id, domain);
        CREATE INDEX IF NOT EXISTS idx_people_tenant_org ON people(tenant_id, organization_id);
        CREATE INDEX IF NOT EXISTS idx_events_tenant_org_time ON commercial_events(tenant_id, organization_id, occurred_at DESC);
        CREATE INDEX IF NOT EXISTS idx_observations_tenant_org_time ON observations(tenant_id, organization_id, observed_at DESC);
        CREATE INDEX IF NOT EXISTS idx_evidence_tenant_observed ON evidence(tenant_id, observed_at DESC);
        CREATE INDEX IF NOT EXISTS idx_signals_tenant_org_time ON signals(tenant_id, organization_id, last_seen_at DESC);
        CREATE INDEX IF NOT EXISTS idx_clusters_tenant_org ON signal_clusters(tenant_id, organization_id);
        CREATE INDEX IF NOT EXISTS idx_opportunities_tenant_stage ON opportunities(tenant_id, stage, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_hypotheses_tenant_opp ON opportunity_hypotheses(tenant_id, opportunity_id);
        CREATE INDEX IF NOT EXISTS idx_messages_tenant_status ON messages(tenant_id, status, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_executions_tenant_status ON executions(tenant_id, status, scheduled_at);
        CREATE INDEX IF NOT EXISTS idx_meetings_tenant_time ON meetings(tenant_id, scheduled_at);
        CREATE INDEX IF NOT EXISTS idx_revenue_tenant_time ON revenue(tenant_id, recognized_at DESC);
        CREATE INDEX IF NOT EXISTS idx_outcomes_tenant_time ON outcomes(tenant_id, occurred_at DESC);

        CREATE UNIQUE INDEX IF NOT EXISTS uq_organizations_tenant_domain
            ON organizations(tenant_id, domain) WHERE domain IS NOT NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS uq_people_tenant_email
            ON people(tenant_id, lower(email)) WHERE email IS NOT NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS uq_executions_provider_message
            ON executions(tenant_id, provider, provider_message_id)
            WHERE provider_message_id IS NOT NULL;

        -- All canonical tables are tenant isolated at the database boundary.
        ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
        ALTER TABLE people ENABLE ROW LEVEL SECURITY;
        ALTER TABLE products ENABLE ROW LEVEL SECURITY;
        ALTER TABLE technologies ENABLE ROW LEVEL SECURITY;
        ALTER TABLE initiatives ENABLE ROW LEVEL SECURITY;
        ALTER TABLE commercial_events ENABLE ROW LEVEL SECURITY;
        ALTER TABLE observations ENABLE ROW LEVEL SECURITY;
        ALTER TABLE evidence ENABLE ROW LEVEL SECURITY;
        ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
        ALTER TABLE signal_clusters ENABLE ROW LEVEL SECURITY;
        ALTER TABLE opportunities ENABLE ROW LEVEL SECURITY;
        ALTER TABLE opportunity_hypotheses ENABLE ROW LEVEL SECURITY;
        ALTER TABLE buying_committees ENABLE ROW LEVEL SECURITY;
        ALTER TABLE buying_committee_members ENABLE ROW LEVEL SECURITY;
        ALTER TABLE sequences ENABLE ROW LEVEL SECURITY;
        ALTER TABLE executions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE meetings ENABLE ROW LEVEL SECURITY;
        ALTER TABLE deals ENABLE ROW LEVEL SECURITY;
        ALTER TABLE revenue ENABLE ROW LEVEL SECURITY;
        ALTER TABLE outcomes ENABLE ROW LEVEL SECURITY;

        DO $$
        DECLARE
            t TEXT;
        BEGIN
            FOREACH t IN ARRAY ARRAY[
                'organizations','people','products','technologies','initiatives',
                'commercial_events','observations','evidence','signals','signal_clusters',
                'opportunities','opportunity_hypotheses','buying_committees',
                'buying_committee_members','sequences','executions',
                'meetings','deals','revenue','outcomes'
            ]
            LOOP
                EXECUTE format(
                    'CREATE POLICY %I ON %I USING (tenant_id::text = NULLIF(current_setting(''app.tenant_id'', true), '''')) WITH CHECK (tenant_id::text = NULLIF(current_setting(''app.tenant_id'', true), ''''))',
                    t || '_tenant_isolation', t
                );
            END LOOP;
        END
        $$;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE replies
            DROP COLUMN IF EXISTS opportunity_id,
            DROP COLUMN IF EXISTS person_id;
        ALTER TABLE campaigns
            DROP COLUMN IF EXISTS opportunity_id;
        ALTER TABLE leads
            DROP COLUMN IF EXISTS person_id,
            DROP COLUMN IF EXISTS organization_id;

        DROP TABLE IF EXISTS outcomes CASCADE;
        DROP TABLE IF EXISTS revenue CASCADE;
        DROP TABLE IF EXISTS deals CASCADE;
        DROP TABLE IF EXISTS meetings CASCADE;
        DROP TABLE IF EXISTS executions CASCADE;
        DROP TABLE IF EXISTS sequences CASCADE;
        DROP TABLE IF EXISTS buying_committee_members CASCADE;
        DROP TABLE IF EXISTS buying_committees CASCADE;
        DROP TABLE IF EXISTS hypothesis_evidence CASCADE;
        DROP TABLE IF EXISTS opportunity_hypotheses CASCADE;
        DROP TABLE IF EXISTS opportunities CASCADE;
        DROP TABLE IF EXISTS signal_cluster_members CASCADE;
        DROP TABLE IF EXISTS signal_clusters CASCADE;
        DROP TABLE IF EXISTS signal_evidence CASCADE;
        DROP TABLE IF EXISTS signals CASCADE;
        DROP TABLE IF EXISTS evidence CASCADE;
        DROP TABLE IF EXISTS observations CASCADE;
        DROP TABLE IF EXISTS commercial_events CASCADE;
        DROP TABLE IF EXISTS initiatives CASCADE;
        DROP TABLE IF EXISTS technologies CASCADE;
        DROP TABLE IF EXISTS products CASCADE;
        DROP TABLE IF EXISTS people CASCADE;
        DROP TABLE IF EXISTS organizations CASCADE;
    """)
