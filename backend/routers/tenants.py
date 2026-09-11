"""FadeReach — Tenants Router
Profile · Settings · Plan info · Onboarding
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from .deps import get_current_tenant
from datetime import datetime
from typing import Optional

router = APIRouter()

class TenantUpdateReq(BaseModel):
    name:    Optional[str] = None
    company: Optional[str] = None

class OnboardingCompleteReq(BaseModel):
    step: str  # domain_added | dns_verified | first_lead | first_campaign

PLAN_FEATURES = {
    "trial": {
        "emails_mo":    50,    "contacts":  500,
        "domains":       1,    "ai_credits": 50,
        "sequences":     1,    "hunter_searches": 10,
        "support":      "email", "trial": True
    },
    "early_adopter": {
        "emails_mo":   10000,  "contacts":  2000,
        "domains":       1,    "ai_credits": 200,
        "sequences":     3,    "hunter_searches": 50,
        "support":      "email", "trial": False
    },
    "growth": {
        "emails_mo":   50000,  "contacts":  10000,
        "domains":       3,    "ai_credits": 1000,
        "sequences":    -1,    "hunter_searches": 200,  # -1 = unlimited
        "support":      "priority_email", "trial": False,
        "ab_testing": True, "reply_classification": True,
        "webhooks": True
    },
    "agency": {
        "emails_mo":   -1,     "contacts":  50000,
        "domains":      10,    "ai_credits": 5000,
        "sequences":    -1,    "hunter_searches": 1000,
        "support":      "live_chat", "trial": False,
        "ab_testing": True, "reply_classification": True,
        "webhooks": True, "white_label": True,
        "sub_accounts": 10, "api_access": True,
        "rbac": True, "audit_logs": True
    },
}

@router.get("/me")
async def get_tenant(request: Request, auth: dict = Depends(get_current_tenant)):
    db = request.app.state.db
    async with db.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT id, email, name, company, plan, status,
                   trial_ends_at, listmonk_url, emails_sent_mo,
                   contacts_count, onboarded, created_at
            FROM tenants WHERE id=$1
        """, auth["sub"])
    if not row:
        raise HTTPException(404, "Tenant not found")

    tenant        = dict(row)
    plan          = tenant["plan"]
    features      = PLAN_FEATURES.get(plan, PLAN_FEATURES["trial"])
    trial_ends_at = tenant.get("trial_ends_at")
    days_left     = None

    if trial_ends_at and plan == "trial":
        delta     = trial_ends_at.replace(tzinfo=None) - datetime.utcnow()
        days_left = max(0, delta.days)

    return {
        **tenant,
        "features":       features,
        "trial_days_left": days_left,
        "workspace_ready": tenant["listmonk_url"] is not None,
    }

@router.patch("/me")
async def update_tenant(
    req: TenantUpdateReq,
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    db      = request.app.state.db
    updates = {k: v for k, v in req.dict().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")

    set_clause = ", ".join(f"{k}=${i+2}" for i, k in enumerate(updates))
    values     = list(updates.values())

    async with db.acquire() as conn:
        await conn.execute(
            f"UPDATE tenants SET {set_clause}, updated_at=NOW() WHERE id=$1",
            auth["sub"], *values
        )
    return {"message": "Profile updated", "updated": updates}

@router.post("/onboarding/complete")
async def complete_onboarding_step(
    req: OnboardingCompleteReq,
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    """Track onboarding progress per step"""
    db        = request.app.state.db
    tenant_id = auth["sub"]
    redis     = request.app.state.redis

    await redis.sadd(f"onboarding:{tenant_id}", req.step)
    steps_done = await redis.smembers(f"onboarding:{tenant_id}")

    required_steps = {"domain_added", "dns_verified", "first_lead", "first_campaign"}
    all_done       = required_steps.issubset(steps_done)

    if all_done:
        async with db.acquire() as conn:
            await conn.execute(
                "UPDATE tenants SET onboarded=TRUE, updated_at=NOW() WHERE id=$1",
                tenant_id
            )

    return {
        "step":       req.step,
        "completed":  list(steps_done),
        "remaining":  list(required_steps - steps_done),
        "all_done":   all_done,
        "progress":   round(len(steps_done) / len(required_steps) * 100)
    }

@router.get("/usage")
async def get_usage(request: Request, auth: dict = Depends(get_current_tenant)):
    """Current month usage vs plan limits"""
    db        = request.app.state.db
    redis     = request.app.state.redis
    tenant_id = auth["sub"]
    month_key = datetime.utcnow().strftime("%Y-%m")

    async with db.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT plan, emails_sent_mo, contacts_count FROM tenants WHERE id=$1",
            tenant_id
        )
        campaign_stats = await conn.fetchrow("""
            SELECT
                COALESCE(SUM(emails_sent),0) as emails_sent,
                COALESCE(SUM(replies),0)     as replies,
                COUNT(*)                      as campaign_count
            FROM campaigns WHERE tenant_id=$1
            AND created_at >= date_trunc('month', NOW())
        """, tenant_id)
        domain_count = await conn.fetchval(
            "SELECT COUNT(*) FROM domains WHERE tenant_id=$1", tenant_id
        )
        lead_count = await conn.fetchval(
            "SELECT COUNT(*) FROM leads WHERE tenant_id=$1", tenant_id
        )

    ai_used   = int(await redis.get(f"ai_credits:{tenant_id}:{month_key}") or 0)
    plan      = row["plan"]
    features  = PLAN_FEATURES.get(plan, PLAN_FEATURES["trial"])

    def pct(used, limit):
        if limit == -1: return 0
        return round(used / limit * 100, 1) if limit > 0 else 100

    emails_sent = int(campaign_stats["emails_sent"])

    return {
        "plan":     plan,
        "month":    month_key,
        "usage": {
            "emails": {
                "used":  emails_sent,
                "limit": features["emails_mo"],
                "pct":   pct(emails_sent, features["emails_mo"])
            },
            "contacts": {
                "used":  int(lead_count),
                "limit": features["contacts"],
                "pct":   pct(int(lead_count), features["contacts"])
            },
            "domains": {
                "used":  int(domain_count),
                "limit": features["domains"],
                "pct":   pct(int(domain_count), features["domains"])
            },
            "ai_credits": {
                "used":  ai_used,
                "limit": features["ai_credits"],
                "pct":   pct(ai_used, features["ai_credits"])
            },
            "campaigns": {
                "count":   int(campaign_stats["campaign_count"]),
                "replies": int(campaign_stats["replies"])
            }
        }
    }
