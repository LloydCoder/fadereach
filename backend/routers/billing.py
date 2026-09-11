"""
FadeReach — Billing Router
Pricing · Checkout URLs · Plan management
LemonSqueezy + Paystack + Paddle
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from .deps import get_current_tenant
import os, httpx
from datetime import datetime

router = APIRouter()

# ── Config ──────────────────────────────────────
LS_API_KEY     = os.getenv("LEMONSQUEEZY_API_KEY", "")
LS_STORE_ID    = os.getenv("LEMONSQUEEZY_STORE_ID", "247127")
PS_SECRET      = os.getenv("PAYSTACK_SECRET_KEY", "")
PADDLE_KEY     = os.getenv("PADDLE_API_KEY", "")
PADDLE_SELLER  = os.getenv("PADDLE_SELLER_ID", "")
APP_URL        = os.getenv("APP_URL", "https://fadereach.tinlance.com")

# ── Plan catalogue ───────────────────────────────
PLANS = {
    "early_adopter": {
        "name":          "Early Adopter",
        "badge":         "LIMITED",
        "price_usd":     49,
        "price_ngn":     78400,
        "price_eur":     46,
        "price_gbp":     39,
        "annual_usd":    490,   # 2 months free
        "tagline":       "First 100 customers only",
        "emails_mo":     "10,000",
        "contacts":      "2,000",
        "domains":       "1 domain",
        "ai_credits":    "200 credits/mo",
        "sequences":     "3 sequences",
        "support":       "Email (48hr)",
        "features": [
            "1 sending domain (BYOD)",
            "10,000 emails/month",
            "2,000 contacts",
            "200 AI first-line credits",
            "3 email sequences",
            "Deliverability Copilot",
            "Warmup monitoring",
            "Unified inbox",
            "Basic analytics",
        ],
        "ls_variant":    os.getenv("LS_VARIANT_EARLY_ADOPTER", ""),
        "ps_plan":       os.getenv("PS_PLAN_EARLY_ADOPTER", ""),
        "paddle_price":  os.getenv("PADDLE_PRICE_EARLY_ADOPTER", ""),
        "highlight":     False,
        "cta":           "Start free trial",
    },
    "growth": {
        "name":          "Growth",
        "badge":         "POPULAR",
        "price_usd":     99,
        "price_ngn":     158400,
        "price_eur":     93,
        "price_gbp":     78,
        "annual_usd":    990,
        "tagline":       "For agencies and B2B teams",
        "emails_mo":     "50,000",
        "contacts":      "10,000",
        "domains":       "3 domains",
        "ai_credits":    "1,000 credits/mo",
        "sequences":     "Unlimited",
        "support":       "Priority email (24hr)",
        "features": [
            "3 sending domains (BYOD)",
            "50,000 emails/month",
            "10,000 contacts",
            "1,000 AI first-line credits",
            "Unlimited sequences",
            "A/B testing",
            "Reply classification AI",
            "Webhook integrations",
            "API access",
            "200 Hunter.io searches/mo",
            "Deliverability Copilot",
            "Full analytics suite",
        ],
        "ls_variant":    os.getenv("LS_VARIANT_GROWTH", ""),
        "ps_plan":       os.getenv("PS_PLAN_GROWTH", ""),
        "paddle_price":  os.getenv("PADDLE_PRICE_GROWTH", ""),
        "highlight":     True,
        "cta":           "Start free trial",
    },
    "agency": {
        "name":          "Agency",
        "badge":         None,
        "price_usd":     299,
        "price_ngn":     478400,
        "price_eur":     279,
        "price_gbp":     236,
        "annual_usd":    2990,
        "tagline":       "For agencies managing multiple clients",
        "emails_mo":     "Unlimited",
        "contacts":      "50,000",
        "domains":       "10 domains",
        "ai_credits":    "5,000 credits/mo",
        "sequences":     "Unlimited",
        "support":       "Live chat (business hours)",
        "features": [
            "10 sending domains",
            "Unlimited emails/month",
            "50,000 contacts",
            "5,000 AI first-line credits",
            "10 client sub-accounts",
            "Full white-label dashboard",
            "Custom domain branding",
            "Full RBAC (Owner/Admin/Manager/SDR)",
            "API access + webhooks",
            "Audit logs",
            "White-label PDF reports",
            "1,000 Hunter.io searches/mo",
            "Paddle checkout (EU/UK VAT handled)",
        ],
        "ls_variant":    os.getenv("LS_VARIANT_AGENCY", ""),
        "ps_plan":       os.getenv("PS_PLAN_AGENCY", ""),
        "paddle_price":  os.getenv("PADDLE_PRICE_AGENCY", ""),
        "highlight":     False,
        "cta":           "Start free trial",
    },
    "managed": {
        "name":          "Managed Growth",
        "badge":         "DFY",
        "price_usd":     999,
        "price_ngn":     1598400,
        "price_eur":     939,
        "price_gbp":     790,
        "annual_usd":    None,  # 3-month minimum, no annual
        "tagline":       "Done-for-you. We run everything.",
        "emails_mo":     "Unlimited",
        "contacts":      "Unlimited",
        "domains":       "Unlimited",
        "ai_credits":    "10,000 credits/mo",
        "sequences":     "Unlimited",
        "support":       "Dedicated account manager",
        "features": [
            "Everything in Agency",
            "Domain purchase + DNS setup",
            "35-day warmup fully managed",
            "500 verified leads/month",
            "AI-written 4-email sequence",
            "Campaign launch + monitoring",
            "Weekly performance report",
            "Hot lead flagging + routing",
            "Monthly strategy call (60 min)",
            "ThreatFade email security audit",
            "3-month minimum commitment",
        ],
        "ls_variant":    os.getenv("LS_VARIANT_MANAGED", ""),
        "ps_plan":       os.getenv("PS_PLAN_MANAGED", ""),
        "paddle_price":  os.getenv("PADDLE_PRICE_MANAGED", ""),
        "highlight":     False,
        "cta":           "Book a call",
        "cta_url":       "mailto:hello@fadereach.tinlance.com?subject=Managed Growth Enquiry",
    },
}

ADD_ONS = [
    {"name": "Lead Credits — Starter",  "amount": 1000,  "price_usd": 19,  "type": "leads"},
    {"name": "Lead Credits — Growth",   "amount": 5000,  "price_usd": 79,  "type": "leads"},
    {"name": "Lead Credits — Agency",   "amount": 10000, "price_usd": 149, "type": "leads"},
    {"name": "AI Credits — Starter",    "amount": 1000,  "price_usd": 9,   "type": "ai"},
    {"name": "AI Credits — Agency",     "amount": 10000, "price_usd": 69,  "type": "ai"},
    {"name": "Deliverability Audit",    "amount": 1,     "price_usd": 199, "type": "service"},
    {"name": "Domain Setup Service",    "amount": 1,     "price_usd": 99,  "type": "service"},
]

# ── Routes ───────────────────────────────────────
@router.get("/plans")
async def get_plans(
    currency: str = "usd",
    billing:  str = "monthly"
):
    """
    Public endpoint — pricing page data
    currency: usd | ngn | eur | gbp
    billing: monthly | annual
    """
    result = []
    for key, plan in PLANS.items():
        price_key = f"price_{currency}" if currency in ["usd","ngn","eur","gbp"] else "price_usd"
        price     = plan.get(price_key, plan["price_usd"])

        if billing == "annual" and plan.get("annual_usd"):
            annual = plan["annual_usd"]
            if currency == "ngn":
                annual = int(annual * 1600)
            elif currency == "eur":
                annual = int(annual * 0.94)
            elif currency == "gbp":
                annual = int(annual * 0.79)
        else:
            annual = None

        result.append({
            "id":        key,
            "name":      plan["name"],
            "badge":     plan["badge"],
            "price":     price,
            "annual":    annual,
            "currency":  currency.upper(),
            "tagline":   plan["tagline"],
            "features":  plan["features"],
            "highlight": plan["highlight"],
            "cta":       plan["cta"],
            "cta_url":   plan.get("cta_url"),
            "billing":   billing,
        })
    return {"plans": result, "add_ons": ADD_ONS}

@router.post("/checkout/lemonsqueezy")
async def ls_checkout(
    plan_id: str,
    billing: str = "monthly",
    request: Request = None,
    auth: dict = Depends(get_current_tenant)
):
    """Generate LemonSqueezy checkout URL for global buyers"""
    if not LS_API_KEY:
        raise HTTPException(503, "LemonSqueezy not configured")

    plan = PLANS.get(plan_id)
    if not plan:
        raise HTTPException(404, f"Plan {plan_id} not found")

    variant_id = plan.get("ls_variant")
    if not variant_id:
        raise HTTPException(503, f"LemonSqueezy variant not configured for {plan_id}")

    db = request.app.state.db
    async with db.acquire() as conn:
        tenant = await conn.fetchrow(
            "SELECT email, name FROM tenants WHERE id=$1", auth["sub"]
        )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.lemonsqueezy.com/v1/checkouts",
                headers={
                    "Authorization": f"Bearer {LS_API_KEY}",
                    "Accept":        "application/vnd.api+json",
                    "Content-Type":  "application/vnd.api+json",
                },
                json={
                    "data": {
                        "type": "checkouts",
                        "attributes": {
                            "checkout_data": {
                                "email": tenant["email"],
                                "name":  tenant["name"],
                                "custom": {
                                    "tenant_id": auth["sub"],
                                    "plan_id":   plan_id,
                                }
                            },
                            "product_options": {
                                "redirect_url": f"{APP_URL}/dashboard?upgraded=true",
                            },
                        },
                        "relationships": {
                            "store": {
                                "data": {"type": "stores", "id": LS_STORE_ID}
                            },
                            "variant": {
                                "data": {"type": "variants", "id": variant_id}
                            }
                        }
                    }
                }
            )
        data = resp.json()
        url  = data.get("data", {}).get("attributes", {}).get("url")
        if not url:
            raise HTTPException(502, "Failed to create checkout")
        return {"checkout_url": url, "provider": "lemonsqueezy"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"LemonSqueezy error: {str(e)}")

@router.post("/checkout/paystack")
async def paystack_checkout(
    plan_id: str,
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    """Initialize Paystack transaction for African buyers"""
    if not PS_SECRET:
        raise HTTPException(503, "Paystack not configured")

    plan = PLANS.get(plan_id)
    if not plan:
        raise HTTPException(404, f"Plan {plan_id} not found")

    plan_code = plan.get("ps_plan")
    if not plan_code:
        raise HTTPException(503, f"Paystack plan not configured for {plan_id}")

    db = request.app.state.db
    async with db.acquire() as conn:
        tenant = await conn.fetchrow(
            "SELECT email, name FROM tenants WHERE id=$1", auth["sub"]
        )

    # Amount in kobo (NGN × 100)
    amount_ngn   = plan.get("price_ngn", plan["price_usd"] * 1600)
    amount_kobo  = int(amount_ngn * 100)

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.paystack.co/transaction/initialize",
                headers={
                    "Authorization": f"Bearer {PS_SECRET}",
                    "Content-Type":  "application/json",
                },
                json={
                    "email":        tenant["email"],
                    "amount":       amount_kobo,
                    "currency":     "NGN",
                    "plan":         plan_code,
                    "callback_url": f"{APP_URL}/dashboard?upgraded=true",
                    "metadata": {
                        "tenant_id": auth["sub"],
                        "plan_id":   plan_id,
                        "name":      tenant["name"],
                        "cancel_action": f"{APP_URL}/pricing",
                    }
                }
            )
        data = resp.json()
        if not data.get("status"):
            raise HTTPException(502, data.get("message", "Paystack init failed"))

        return {
            "checkout_url":   data["data"]["authorization_url"],
            "reference":      data["data"]["reference"],
            "provider":       "paystack",
            "amount_ngn":     amount_ngn,
            "amount_display": f"₦{amount_ngn:,.0f}/month",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Paystack error: {str(e)}")

@router.post("/checkout/paddle")
async def paddle_checkout(
    plan_id: str,
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    """
    Generate Paddle checkout for EU/UK enterprise buyers
    VAT handled automatically by Paddle
    White-label checkout on Agency plan
    """
    if not PADDLE_KEY:
        raise HTTPException(503, "Paddle not configured")

    plan = PLANS.get(plan_id)
    if not plan:
        raise HTTPException(404, f"Plan {plan_id} not found")

    price_id = plan.get("paddle_price")
    if not price_id:
        raise HTTPException(503, f"Paddle price not configured for {plan_id}")

    db = request.app.state.db
    async with db.acquire() as conn:
        tenant = await conn.fetchrow(
            "SELECT email, name FROM tenants WHERE id=$1", auth["sub"]
        )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.paddle.com/transactions",
                headers={
                    "Authorization": f"Bearer {PADDLE_KEY}",
                    "Content-Type":  "application/json",
                },
                json={
                    "items": [{"price_id": price_id, "quantity": 1}],
                    "customer": {"email": tenant["email"]},
                    "custom_data": {
                        "tenant_id": auth["sub"],
                        "plan_id":   plan_id,
                    },
                    "success_url": f"{APP_URL}/dashboard?upgraded=true",
                }
            )
        data = resp.json()
        checkout_url = data.get("data", {}).get("checkout", {}).get("url")
        if not checkout_url:
            raise HTTPException(502, "Failed to create Paddle checkout")

        return {
            "checkout_url": checkout_url,
            "provider":     "paddle",
            "note":         "VAT calculated automatically at checkout",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Paddle error: {str(e)}")

@router.get("/current")
async def current_billing(
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    """Current subscription status for billing page"""
    db = request.app.state.db
    async with db.acquire() as conn:
        tenant = await conn.fetchrow("""
            SELECT plan, status, trial_ends_at, created_at
            FROM tenants WHERE id=$1
        """, auth["sub"])

        events = await conn.fetch("""
            SELECT event_type, provider, amount, created_at
            FROM billing_events
            WHERE tenant_id=$1
            ORDER BY created_at DESC LIMIT 10
        """, auth["sub"])

    plan_info      = PLANS.get(tenant["plan"], PLANS["early_adopter"])
    trial_ends_at  = tenant["trial_ends_at"]
    days_left      = None

    if trial_ends_at and tenant["status"] == "trial":
        delta     = trial_ends_at.replace(tzinfo=None) - datetime.utcnow()
        days_left = max(0, delta.days)

    return {
        "plan":          tenant["plan"],
        "status":        tenant["status"],
        "plan_name":     plan_info["name"],
        "price_usd":     plan_info["price_usd"],
        "price_ngn":     plan_info["price_ngn"],
        "trial_days_left": days_left,
        "billing_events": [dict(e) for e in events],
        "upgrade_options": [
            k for k in PLANS.keys()
            if PLANS[k]["price_usd"] > plan_info["price_usd"]
        ],
    }

@router.get("/portal")
async def billing_portal(
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    """
    Returns billing portal URLs for each provider
    Client uses whichever they originally paid with
    """
    return {
        "lemonsqueezy": "https://app.lemonsqueezy.com/my-orders",
        "paystack":     "https://paystack.com/pay",
        "paddle":       "https://customer.paddle.com",
        "support":      "mailto:billing@fadereach.tinlance.com",
    }
