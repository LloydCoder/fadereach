"""FadeReach — Admin Router
Lloyd-only · All tenants · System health · Revenue overview
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from .deps import require_admin
from datetime import datetime
from typing import Optional

router = APIRouter()

class TenantActionReq(BaseModel):
    action: str  # suspend | activate | upgrade | downgrade | delete
    plan:   Optional[str] = None
    reason: Optional[str] = None

@router.get("/tenants")
async def admin_list_tenants(
    request: Request,
    auth: dict = Depends(require_admin),
    status: Optional[str] = None,
    plan:   Optional[str] = None,
    limit:  int = 50,
    offset: int = 0
):
    """All tenants across the system"""
    db = request.app.state.db

    conditions = ["1=1"]
    params     = []
    idx        = 1

    if status:
        conditions.append(f"status=${idx}"); params.append(status); idx += 1
    if plan:
        conditions.append(f"plan=${idx}"); params.append(plan); idx += 1

    where = " AND ".join(conditions)

    async with db.acquire() as conn:
        rows = await conn.fetch(f"""
            SELECT id, email, name, company, plan, status,
                   trial_ends_at, emails_sent_mo, contacts_count,
                   onboarded, listmonk_url, created_at
            FROM tenants
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT {limit} OFFSET {offset}
        """, *params)

        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM tenants WHERE {where}", *params
        )

        # Aggregate stats
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*)                                    as total,
                COUNT(*) FILTER (WHERE status='trial')     as on_trial,
                COUNT(*) FILTER (WHERE status='active')    as active,
                COUNT(*) FILTER (WHERE status='suspended') as suspended,
                COUNT(*) FILTER (WHERE plan='early_adopter') as ea_count,
                COUNT(*) FILTER (WHERE plan='growth')      as growth_count,
                COUNT(*) FILTER (WHERE plan='agency')      as agency_count,
                COUNT(*) FILTER (WHERE plan='managed')     as managed_count
            FROM tenants
        """)

    return {
        "tenants": [dict(r) for r in rows],
        "total":   total,
        "stats":   dict(stats),
    }

@router.get("/tenants/{tenant_id}")
async def admin_get_tenant(
    tenant_id: str,
    request: Request,
    auth: dict = Depends(require_admin)
):
    """Deep dive on a single tenant"""
    db = request.app.state.db
    async with db.acquire() as conn:
        tenant = await conn.fetchrow(
            "SELECT * FROM tenants WHERE id=$1", tenant_id
        )
        if not tenant:
            raise HTTPException(404, "Tenant not found")

        campaigns = await conn.fetch(
            "SELECT id, name, status, emails_sent, replies FROM campaigns WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT 10",
            tenant_id
        )
        domains = await conn.fetch(
            "SELECT domain, health_score, warmup_day, warmup_status FROM domains WHERE tenant_id=$1",
            tenant_id
        )
        billing = await conn.fetch(
            "SELECT event_type, provider, amount, created_at FROM billing_events WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT 10",
            tenant_id
        )

    return {
        "tenant":   dict(tenant),
        "campaigns": [dict(c) for c in campaigns],
        "domains":   [dict(d) for d in domains],
        "billing":   [dict(b) for b in billing],
    }

@router.post("/tenants/{tenant_id}/action")
async def admin_tenant_action(
    tenant_id: str,
    req: TenantActionReq,
    request: Request,
    auth: dict = Depends(require_admin)
):
    """Suspend, activate, upgrade, downgrade tenant"""
    db = request.app.state.db

    action_map = {
        "suspend":    {"status": "suspended"},
        "activate":   {"status": "active"},
        "upgrade":    {"plan": req.plan, "status": "active"},
        "downgrade":  {"plan": req.plan or "early_adopter"},
    }

    if req.action not in action_map:
        raise HTTPException(400, f"Unknown action: {req.action}")

    updates = action_map[req.action]
    set_parts = [f"{k}=${i+2}" for i, k in enumerate(updates)]
    set_clause = ", ".join(set_parts)

    async with db.acquire() as conn:
        await conn.execute(
            f"UPDATE tenants SET {set_clause}, updated_at=NOW() WHERE id=$1",
            tenant_id, *list(updates.values())
        )
        await conn.execute("""
            INSERT INTO audit_log (actor, tenant_id, action, metadata)
            VALUES ('admin_lloyd', $1, $2, $3)
        """, tenant_id, req.action,
            __import__('json').dumps({"reason": req.reason, "updates": updates}))

    return {
        "tenant_id": tenant_id,
        "action":    req.action,
        "applied":   updates
    }

@router.get("/revenue")
async def admin_revenue(
    request: Request,
    auth: dict = Depends(require_admin)
):
    """Revenue overview — MRR, by plan, by provider"""
    db = request.app.state.db
    async with db.acquire() as conn:
        by_plan = await conn.fetch("""
            SELECT plan, COUNT(*) as count
            FROM tenants
            WHERE status='active'
            GROUP BY plan
        """)

        by_provider = await conn.fetch("""
            SELECT provider,
                   COUNT(*) as transactions,
                   COALESCE(SUM(amount), 0) as total_amount
            FROM billing_events
            WHERE event_type IN ('subscription_created','subscription.create','subscription.created')
            AND created_at >= date_trunc('month', NOW())
            GROUP BY provider
        """)

        recent_events = await conn.fetch("""
            SELECT be.event_type, be.provider, be.amount, be.created_at,
                   t.email, t.plan
            FROM billing_events be
            JOIN tenants t ON be.tenant_id = t.id
            ORDER BY be.created_at DESC
            LIMIT 20
        """)

    # MRR calculation
    plan_prices = {
        "early_adopter": 49,
        "growth":        99,
        "agency":        299,
        "managed":       999
    }
    mrr = sum(
        plan_prices.get(r["plan"], 0) * int(r["count"])
        for r in by_plan
    )

    return {
        "mrr_usd":       mrr,
        "arr_usd":       mrr * 12,
        "by_plan":       [dict(r) for r in by_plan],
        "by_provider":   [dict(r) for r in by_provider],
        "recent_events": [dict(r) for r in recent_events],
    }

@router.get("/system/health")
async def admin_system_health(
    request: Request,
    auth: dict = Depends(require_admin)
):
    """EC2 system health — DB, Redis, n8n, Reacher, Listmonk"""
    import httpx
    db    = request.app.state.db
    redis = request.app.state.redis

    checks = {}

    # PostgreSQL
    try:
        await db.fetchval("SELECT 1")
        checks["postgres"] = {"status": "ok"}
    except Exception as e:
        checks["postgres"] = {"status": "error", "error": str(e)}

    # Redis
    try:
        await redis.ping()
        info = await redis.info("memory")
        checks["redis"] = {
            "status": "ok",
            "memory_used": info.get("used_memory_human", "unknown")
        }
    except Exception as e:
        checks["redis"] = {"status": "error", "error": str(e)}

    # Reacher (self-hosted email verifier)
    REACHER_URL = __import__('os').getenv("REACHER_URL", "http://localhost:8083")
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{REACHER_URL}/health")
        checks["reacher"] = {"status": "ok" if resp.status_code == 200 else "error"}
    except:
        checks["reacher"] = {"status": "offline"}

    # n8n
    N8N_URL = __import__('os').getenv("N8N_WEBHOOK_URL", "http://localhost:5678")
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{N8N_URL}/healthz")
        checks["n8n"] = {"status": "ok" if resp.status_code == 200 else "error"}
    except:
        checks["n8n"] = {"status": "offline"}

    # Tenant container count
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "ps", "--filter", "label=fadereach.tenant", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=5
        )
        containers = [c for c in result.stdout.strip().split("\n") if c]
        checks["listmonk_containers"] = {
            "status": "ok",
            "count":  len(containers)
        }
    except:
        checks["listmonk_containers"] = {"status": "unknown"}

    all_ok = all(v.get("status") == "ok" for v in checks.values())

    return {
        "overall":  "ok" if all_ok else "degraded",
        "checks":   checks,
        "timestamp": datetime.utcnow().isoformat(),
    }
