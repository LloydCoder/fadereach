"""
FadeReach — FastAPI Core | Phase 1
fadereach.tinlance.com | Tinlance Limited | Lloyd
EC2 Stockholm 13.50.16.19 | Port 8001
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncpg, redis.asyncio as aioredis
import os
from datetime import datetime

DB_URL      = os.getenv("DATABASE_URL", "postgresql://fadereach:password@localhost/fadereach_meta")
REDIS_URL   = os.getenv("REDIS_URL", "redis://localhost:6379")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
APP_URL     = os.getenv("APP_URL", "https://fadereach.tinlance.com")

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db    = await asyncpg.create_pool(DB_URL, min_size=2, max_size=10)
    app.state.redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
    await _init_db(app.state.db)
    print(f"✓ FadeReach API [{ENVIRONMENT}] → {APP_URL}")
    yield
    await app.state.db.close()
    await app.state.redis.close()

app = FastAPI(
    title="FadeReach API",
    description="Opportunity Intelligence + Deliverability Intelligence — Tinlance Limited",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if ENVIRONMENT == "development" else None,
)

app.add_middleware(CORSMiddleware,
    allow_origins=["https://fadereach.tinlance.com","https://fadereach.ai","http://localhost:3000","http://localhost:5173"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

async def _init_db(pool):
    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
            company TEXT, password_hash TEXT NOT NULL,
            plan TEXT NOT NULL DEFAULT 'trial', status TEXT NOT NULL DEFAULT 'trial',
            trial_ends_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '14 days',
            listmonk_url TEXT, listmonk_port INTEGER,
            emails_sent_mo INTEGER DEFAULT 0, contacts_count INTEGER DEFAULT 0,
            onboarded BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS domains (
            id SERIAL PRIMARY KEY, tenant_id TEXT REFERENCES tenants(id) ON DELETE CASCADE,
            domain TEXT NOT NULL, spf_valid BOOLEAN DEFAULT FALSE,
            dkim_valid BOOLEAN DEFAULT FALSE, dmarc_valid BOOLEAN DEFAULT FALSE,
            warmup_day INTEGER DEFAULT 0, warmup_status TEXT DEFAULT 'not_started',
            daily_limit INTEGER DEFAULT 5, sent_today INTEGER DEFAULT 0,
            bounce_rate NUMERIC DEFAULT 0, complaint_rate NUMERIC DEFAULT 0,
            health_score INTEGER DEFAULT 0, inbox_prob INTEGER DEFAULT 0,
            blacklisted BOOLEAN DEFAULT FALSE,
            added_at TIMESTAMPTZ DEFAULT NOW(), last_checked TIMESTAMPTZ
        );
        CREATE TABLE IF NOT EXISTS leads (
            id SERIAL PRIMARY KEY, tenant_id TEXT REFERENCES tenants(id) ON DELETE CASCADE,
            email TEXT NOT NULL, first_name TEXT, last_name TEXT,
            company TEXT, title TEXT, domain TEXT, linkedin_url TEXT,
            industry TEXT, company_size TEXT, location TEXT,
            status TEXT DEFAULT 'uncontacted', verify_status TEXT DEFAULT 'unverified',
            verify_score INTEGER DEFAULT 0, icp_score INTEGER DEFAULT 0,
            ai_first_line TEXT, ai_hook TEXT, ai_score INTEGER DEFAULT 0,
            signal_type TEXT, signal_data JSONB, created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS campaigns (
            id SERIAL PRIMARY KEY, tenant_id TEXT REFERENCES tenants(id) ON DELETE CASCADE,
            name TEXT NOT NULL, subject TEXT NOT NULL, status TEXT DEFAULT 'draft',
            product TEXT, target_segment TEXT, sequence_steps INTEGER DEFAULT 4,
            emails_sent INTEGER DEFAULT 0, opens INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0, replies INTEGER DEFAULT 0,
            bounces INTEGER DEFAULT 0, unsubscribes INTEGER DEFAULT 0,
            audit_score INTEGER, audit_issues JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS replies (
            id SERIAL PRIMARY KEY, tenant_id TEXT REFERENCES tenants(id) ON DELETE CASCADE,
            campaign_id INTEGER REFERENCES campaigns(id), lead_id INTEGER REFERENCES leads(id),
            from_email TEXT NOT NULL, subject TEXT, body TEXT,
            intent TEXT DEFAULT 'unknown', sentiment TEXT DEFAULT 'neutral',
            is_hot BOOLEAN DEFAULT FALSE, is_read BOOLEAN DEFAULT FALSE,
            received_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS billing_events (
            id SERIAL PRIMARY KEY, tenant_id TEXT REFERENCES tenants(id),
            event_type TEXT NOT NULL, provider TEXT NOT NULL,
            amount NUMERIC, currency TEXT, metadata JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY, actor TEXT NOT NULL, tenant_id TEXT,
            action TEXT NOT NULL, resource TEXT, metadata JSONB,
            ip_address TEXT, created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_leads_tenant     ON leads(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_campaigns_tenant ON campaigns(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_replies_tenant   ON replies(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_domains_tenant   ON domains(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_replies_hot      ON replies(tenant_id, is_hot, is_read);
        """)

@app.get("/api/health")
async def health(request: Request):
    try:
        await request.app.state.db.fetchval("SELECT 1")
        db_ok = True
    except: db_ok = False
    try:
        await request.app.state.redis.ping()
        redis_ok = True
    except: redis_ok = False
    return {
        "status": "ok" if (db_ok and redis_ok) else "degraded",
        "service": "FadeReach API", "version": "1.0.0",
        "environment": ENVIRONMENT, "database": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
        "timestamp": datetime.utcnow().isoformat(),
    }

# ── Phase 2 routers ─────────────────────────────
from routers import billing, onboarding
from middleware.plan_enforcement import TrialGuard

app.add_middleware(TrialGuard)
app.include_router(billing.router,    prefix="/api/billing",    tags=["Billing"])
app.include_router(onboarding.router, prefix="/api/onboarding", tags=["Onboarding"])

# ── Phase 3 routers ─────────────────────────────
from routers import opportunity_feed, learning, graphify, testing as testing_router

app.include_router(opportunity_feed.router, prefix="/api/opportunities", tags=["Opportunity Feed"])
app.include_router(learning.router,         prefix="/api/learning",      tags=["Learning Engine"])
app.include_router(graphify.router,         prefix="/api/graphify",      tags=["Graphify"])
app.include_router(testing_router.router,   prefix="/api/testing",       tags=["A/B Testing"])
