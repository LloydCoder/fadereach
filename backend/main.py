"""
FadeReach — FastAPI Core | Phase 1
fadereach.tinlance.com | Tinlance Limited | Lloyd
EC2 Stockholm 13.50.16.19 | Port 8001
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import asyncio
import asyncpg, redis.asyncio as aioredis
import os
from datetime import datetime
from tenant_context import tenant_id_context
from db import TenantAwarePool
from middleware.security import SecurityHeadersMiddleware, allowed_hosts
from outbound_worker import run_outbound_worker
from retention_worker import run_retention_worker

DB_URL      = os.getenv("DATABASE_URL")
WORKER_DB_URL = os.getenv("WORKER_DATABASE_URL") or DB_URL
if not DB_URL:
    raise RuntimeError("DATABASE_URL must be configured")
REDIS_URL   = os.getenv("REDIS_URL", "redis://localhost:6379")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
APP_URL     = os.getenv("APP_URL", "https://fadereach.tinlance.com")

@asynccontextmanager
async def lifespan(app: FastAPI):
    raw_db = await asyncpg.create_pool(DB_URL, min_size=2, max_size=10)
    worker_db = await asyncpg.create_pool(WORKER_DB_URL, min_size=1, max_size=3)
    app.state.db = TenantAwarePool(raw_db)
    app.state.worker_queue_db = worker_db
    app.state.redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
    await _init_db(app.state.db)
    worker_task = asyncio.create_task(run_outbound_worker(app.state.db, app.state.worker_queue_db))
    retention_task = asyncio.create_task(run_retention_worker(app.state.db))
    app.state.outbound_worker = worker_task
    app.state.retention_worker = retention_task
    print(f"✓ FadeReach API [{ENVIRONMENT}] → {APP_URL}")
    try:
        yield
    finally:
        worker_task.cancel()
        retention_task.cancel()
        for task in (worker_task, retention_task):
            try:
                await task
            except asyncio.CancelledError:
                pass
        await app.state.db.close()
        await app.state.worker_queue_db.close()
        await app.state.redis.close()

app = FastAPI(
    title="FadeReach API",
    description="Opportunity Intelligence + Deliverability Intelligence — Tinlance Limited",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if ENVIRONMENT == "development" else None,
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts())
app.add_middleware(SecurityHeadersMiddleware)


@app.middleware("http")
async def tenant_context_scope(request: Request, call_next):
    """Clear tenant context at request boundaries to prevent cross-request bleed."""
    token = tenant_id_context.set(None)
    try:
        return await call_next(request)
    finally:
        tenant_id_context.reset(token)

default_cors = (
    "https://fadereach.app,https://fadereach.tinlance.com"
    if ENVIRONMENT == "production"
    else "https://fadereach.app,https://fadereach.tinlance.com,http://localhost:3000,http://localhost:5173"
)
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", default_cors).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"],
    allow_headers=["Authorization","Content-Type","Accept","X-Requested-With"],
)



async def _init_db(pool):
    """Deprecated compatibility hook; schema is managed by Alembic."""
    return None

@app.get("/api/health")
async def health(request: Request):
    try:
        await request.app.state.db.fetchval("SELECT 1")
        db_ok = True
    except Exception: db_ok = False
    try:
        await request.app.state.redis.ping()
        redis_ok = True
    except Exception: redis_ok = False
    return {
        "status": "ok" if (db_ok and redis_ok) else "degraded",
        "service": "FadeReach API", "version": "1.0.0",
        "environment": ENVIRONMENT, "database": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
        "timestamp": datetime.now().astimezone().isoformat(),
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


# ── Complete router registry ─────────────────────────────
# Keep the full implemented API surface reachable. Routers are mounted explicitly
# here rather than relying on implicit discovery.
from routers import (
    auth, campaigns, leads, domains, inbox, analytics, admin, tenants, rbac,
    webhooks, managed, verticals, whitelabel, ecosystem, public_api, nowpayments, providers, intelligence, integrations, graph, autopilot, enterprise, unsubscribe, privacy, agency, enterprise_security
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(campaigns.router, prefix="/api/campaigns", tags=["Campaigns"])
app.include_router(leads.router, prefix="/api/leads", tags=["Leads"])
app.include_router(domains.router, prefix="/api/domains", tags=["Domains"])
app.include_router(inbox.router, prefix="/api/inbox", tags=["Inbox"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(tenants.router, prefix="/api/tenants", tags=["Tenants"])
app.include_router(rbac.router, prefix="/api/rbac", tags=["RBAC"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])
app.include_router(unsubscribe.router, prefix="/api/unsubscribe", tags=["Unsubscribe"])
app.include_router(privacy.router, prefix="/api/privacy", tags=["Privacy"])
app.include_router(agency.router, prefix="/api/agency", tags=["Agency"])
app.include_router(enterprise_security.router, prefix="/api/enterprise-security", tags=["Enterprise Security"])
app.include_router(managed.router, prefix="/api/managed", tags=["Managed"])
app.include_router(verticals.router, prefix="/api/verticals", tags=["Verticals"])
app.include_router(whitelabel.router, prefix="/api/whitelabel", tags=["White Label"])
app.include_router(ecosystem.router, prefix="/api/ecosystem", tags=["Ecosystem"])
app.include_router(public_api.router, prefix="/api/public", tags=["Public API"])
app.include_router(nowpayments.router, prefix="/api/payments", tags=["Payments"])
app.include_router(providers.router, prefix="/api/providers", tags=["Providers"])
app.include_router(intelligence.router, prefix="/api/intelligence", tags=["Intelligence"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["Integrations"])
app.include_router(graph.router, prefix="/api/graph", tags=["Graph"])
app.include_router(autopilot.router, prefix="/api/autopilot", tags=["Autopilot"])
app.include_router(enterprise.router, prefix="/api/enterprise", tags=["Enterprise"])
