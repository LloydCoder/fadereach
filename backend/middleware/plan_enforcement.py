"""
FadeReach — Plan Enforcement Middleware
Checks plan limits on every protected request
Blocks over-limit actions before they hit the DB
"""
from fastapi import Request, HTTPException
from datetime import datetime
import jwt, os

JWT_SECRET = os.getenv("JWT_SECRET", "")
if os.getenv("ENVIRONMENT") == "production" and len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET must be configured with sufficient entropy")

# Plan limits — single source of truth
PLAN_LIMITS = {
    "trial": {
        "emails_mo":        50,
        "contacts":        500,
        "domains":           1,
        "ai_credits":       50,
        "sequences":         1,
        "hunter_searches":  10,
        "sub_accounts":      0,
        "api_access":    False,
        "white_label":   False,
        "webhooks":      False,
        "rbac":          False,
        "a_b_testing":   False,
        "paddle":        False,
    },
    "early_adopter": {
        "emails_mo":     10000,
        "contacts":       2000,
        "domains":           1,
        "ai_credits":      200,
        "sequences":         3,
        "hunter_searches":  50,
        "sub_accounts":      0,
        "api_access":    False,
        "white_label":   False,
        "webhooks":      False,
        "rbac":          False,
        "a_b_testing":   False,
        "paddle":        False,
    },
    "growth": {
        "emails_mo":     50000,
        "contacts":      10000,
        "domains":           3,
        "ai_credits":     1000,
        "sequences":        -1,   # unlimited
        "hunter_searches": 200,
        "sub_accounts":      0,
        "api_access":     True,
        "white_label":   False,
        "webhooks":       True,
        "rbac":          False,
        "a_b_testing":    True,
        "paddle":        False,
    },
    "agency": {
        "emails_mo":        -1,   # unlimited
        "contacts":      50000,
        "domains":          10,
        "ai_credits":     5000,
        "sequences":        -1,
        "hunter_searches":1000,
        "sub_accounts":     10,
        "api_access":     True,
        "white_label":    True,
        "webhooks":       True,
        "rbac":           True,
        "a_b_testing":    True,
        "paddle":         True,
    },
    "managed": {
        "emails_mo":        -1,
        "contacts":         -1,
        "domains":          -1,
        "ai_credits":    10000,
        "sequences":        -1,
        "hunter_searches":  -1,
        "sub_accounts":     -1,
        "api_access":     True,
        "white_label":    True,
        "webhooks":       True,
        "rbac":           True,
        "a_b_testing":    True,
        "paddle":         True,
    },
}

def get_plan_limit(plan: str, feature: str):
    """Get limit for a feature on a given plan"""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["trial"]).get(feature, 0)

def check_feature_access(plan: str, feature: str) -> bool:
    """Check if a boolean feature is available on a plan"""
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["trial"])
    val = limits.get(feature, False)
    return bool(val) and val != 0 and val != False

async def enforce_plan_limit(
    request: Request,
    feature: str,
    current_usage: int,
    plan: str,
    error_message: str = None
):
    """
    Call this in any route that needs plan enforcement.
    Raises 403 if limit exceeded.
    """
    limit = get_plan_limit(plan, feature)
    if limit == -1:
        return  # Unlimited
    if current_usage >= limit:
        raise HTTPException(
            status_code=403,
            detail=error_message or (
                f"You've reached the {feature.replace('_',' ')} limit "
                f"({limit}) on your {plan.replace('_',' ').title()} plan. "
                f"Upgrade to continue."
            )
        )

async def enforce_feature_flag(plan: str, feature: str, feature_name: str = None):
    """Check if a plan feature flag is enabled"""
    if not check_feature_access(plan, feature):
        plan_display = plan.replace("_", " ").title()
        feat_display = feature_name or feature.replace("_", " ").title()
        raise HTTPException(
            status_code=403,
            detail=f"{feat_display} is not available on the {plan_display} plan. "
                   f"Upgrade to Agency or higher to access this feature."
        )

class TrialGuard:
    """
    Checks trial expiry on every authenticated request.
    Adds trial status to request state.
    """
    async def __call__(self, request: Request, call_next):
        token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

        if token:
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
                tenant_id = payload.get("sub")
                plan      = "trial"

                # Check trial expiry
                if plan == "trial":
                    db = request.app.state.db
                    async with db.acquire() as conn:
                        row = await conn.fetchrow(
                            "SELECT trial_ends_at, status, plan FROM tenants WHERE id=$1",
                            tenant_id
                        )
                        if row and row["trial_ends_at"]:
                            expires = row["trial_ends_at"].replace(tzinfo=None)
                            if expires < datetime.utcnow() and row["status"] == "trial":
                                # Expire the trial
                                await conn.execute(
                                    "UPDATE tenants SET status='trial_expired' WHERE id=$1",
                                    tenant_id
                                )
                                # Still allow read-only routes
                                request.state.trial_expired = True
                                request.state.plan = row["plan"]
                                response = await call_next(request)
                                return response

                request.state.plan = row["plan"] if row else "trial"
                request.state.tenant_id = tenant_id
                request.state.trial_expired = False
            except:
                pass

        response = await call_next(request)
        return response
