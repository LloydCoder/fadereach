"""FadeReach — Webhooks Router
LemonSqueezy · Paystack · Paddle
All three payment systems handled here
"""
from fastapi import APIRouter, HTTPException, Request, Header
import hmac, hashlib, json, os, httpx
from datetime import datetime, timezone

router = APIRouter()

LS_WEBHOOK_SECRET     = os.getenv("LEMONSQUEEZY_WEBHOOK_SECRET", "")
PAYSTACK_SECRET_KEY   = os.getenv("PAYSTACK_SECRET_KEY", "")
PADDLE_WEBHOOK_SECRET = os.getenv("PADDLE_WEBHOOK_SECRET", "")
RESEND_KEY            = os.getenv("RESEND_API_KEY", "")
APP_URL               = os.getenv("APP_URL", "https://fadereach.tinlance.com")

async def _claim_webhook_event(db, provider: str, event_id: str, payload: dict) -> bool:
    """Atomically claim an event; duplicate deliveries become no-ops."""
    if not event_id:
        raise HTTPException(400, "Webhook event identifier is required")
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO webhook_events (provider, event_id, payload)
               VALUES ($1,$2,$3::jsonb)
               ON CONFLICT (provider,event_id) DO NOTHING
               RETURNING id""",
            provider, event_id, json.dumps(payload),
        )
    return row is not None



# ── Plan mapping per provider ───────────────────
LS_VARIANT_PLANS = {
    # LemonSqueezy variant IDs → FadeReach plan
    # Set these in LemonSqueezy dashboard
    os.getenv("LS_VARIANT_EARLY_ADOPTER", ""): "early_adopter",
    os.getenv("LS_VARIANT_GROWTH", ""):         "growth",
    os.getenv("LS_VARIANT_AGENCY", ""):         "agency",
    os.getenv("LS_VARIANT_MANAGED", ""):        "managed",
}

PAYSTACK_PLAN_CODES = {
    os.getenv("PS_PLAN_EARLY_ADOPTER", ""): "early_adopter",
    os.getenv("PS_PLAN_GROWTH", ""):         "growth",
    os.getenv("PS_PLAN_AGENCY", ""):         "agency",
}

PADDLE_PRICE_PLANS = {
    os.getenv("PADDLE_PRICE_EARLY_ADOPTER", ""): "early_adopter",
    os.getenv("PADDLE_PRICE_GROWTH", ""):         "growth",
    os.getenv("PADDLE_PRICE_AGENCY", ""):         "agency",
    os.getenv("PADDLE_PRICE_MANAGED", ""):        "managed",
}

# ── LemonSqueezy ────────────────────────────────
@router.post("/lemonsqueezy")
async def lemonsqueezy_webhook(
    request: Request,
    x_signature: str = Header(None, alias="X-Signature")
):
    body = await request.body()

    # Verify signature — fail closed when the secret is not configured.
    if not LS_WEBHOOK_SECRET:
        raise HTTPException(503, "LemonSqueezy webhook verification is not configured")
    expected = hmac.new(
            LS_WEBHOOK_SECRET.encode(),
            body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(f"sha256={expected}", x_signature or ""):
            raise HTTPException(401, "Invalid LemonSqueezy signature")

    data       = json.loads(body)
    event_type = data.get("meta", {}).get("event_name", "")
    event_id   = f"{event_type}:{data.get('data', {}).get('id', '')}"
    db         = request.app.state.db
    if not await _claim_webhook_event(db, "lemonsqueezy", event_id, data):
        return {"received": True, "duplicate": True}
    attrs      = data.get("data", {}).get("attributes", {})
    email      = attrs.get("user_email", "")
    variant_id = str(attrs.get("variant_id", ""))
    plan       = LS_VARIANT_PLANS.get(variant_id, "growth")


    if event_type == "subscription_created":
        await _activate_plan(db, email, plan, "lemonsqueezy",
                             attrs.get("subtotal", 0))

    elif event_type == "subscription_updated":
        new_variant = str(attrs.get("variant_id", ""))
        new_plan    = LS_VARIANT_PLANS.get(new_variant, plan)
        await _upgrade_plan(db, email, new_plan)

    elif event_type == "subscription_cancelled":
        await _cancel_plan(db, email)

    elif event_type == "subscription_expired":
        await _suspend_tenant(db, email)

    elif event_type == "subscription_payment_failed":
        await _payment_failed(db, email)

    elif event_type == "order_created":
        # One-time purchases: lead credits, AI credits
        product_id = str(attrs.get("first_order_item", {}).get("product_id", ""))
        await _handle_one_time_purchase(db, email, product_id, "lemonsqueezy")

    await _log_billing(db, email, event_type, "lemonsqueezy",
                       attrs.get("subtotal", 0), data)
    return {"received": True}

# ── Paystack ─────────────────────────────────────
@router.post("/paystack")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str = Header(None, alias="X-Paystack-Signature")
):
    body = await request.body()

    # Verify HMAC-SHA512 — fail closed when the secret is not configured.
    if not PAYSTACK_SECRET_KEY:
        raise HTTPException(503, "Paystack webhook verification is not configured")
    expected = hmac.new(
            PAYSTACK_SECRET_KEY.encode(),
            body, hashlib.sha512
    ).hexdigest()
    if not hmac.compare_digest(expected, x_paystack_signature or ""):
            raise HTTPException(401, "Invalid Paystack signature")

    data  = json.loads(body)
    event = data.get("event", "")
    event_id = f"{event}:{data.get('data', {}).get('id', '')}"
    db = request.app.state.db
    if not await _claim_webhook_event(db, "paystack", event_id, data):
        return {"received": True, "duplicate": True}
    obj   = data.get("data", {})
    email = obj.get("customer", {}).get("email", "")


    if event == "subscription.create":
        plan_code = obj.get("plan", {}).get("plan_code", "")
        plan      = PAYSTACK_PLAN_CODES.get(plan_code, "growth")
        amount    = obj.get("amount", 0) / 100  # Paystack sends kobo
        await _activate_plan(db, email, plan, "paystack", amount)

    elif event == "subscription.disable":
        await _cancel_plan(db, email)

    elif event == "charge.success":
        # Successful recurring charge — ensure account stays active
        await _ensure_active(db, email)

    elif event in ["invoice.payment_failed", "subscription.not_renew"]:
        await _payment_failed(db, email)

    await _log_billing(db, email, event, "paystack",
                       obj.get("amount", 0) / 100, data)
    return {"received": True}

# ── Paddle ───────────────────────────────────────
@router.post("/paddle")
async def paddle_webhook(
    request: Request,
    paddle_signature: str = Header(None, alias="Paddle-Signature")
):
    """
    Paddle — EU/UK enterprise tier
    Handles VAT automatically — no code needed
    White-label checkout for Agency plan
    """
    body = await request.body()

    # Verify Paddle signature — fail closed when the secret is not configured.
    if not PADDLE_WEBHOOK_SECRET:
        raise HTTPException(503, "Paddle webhook verification is not configured")
    if not _verify_paddle_signature(body, paddle_signature or "", PADDLE_WEBHOOK_SECRET):
            raise HTTPException(401, "Invalid Paddle signature")

    data       = json.loads(body)
    event_type = data.get("event_type", "")
    event_id   = str(data.get("event_id", ""))
    try:
        ts = int(dict(p.split("=", 1) for p in (paddle_signature or "").split(";") if "=" in p).get("ts", "0"))
        if abs(datetime.now(timezone.utc).timestamp() - ts) > 300:
            raise HTTPException(401, "Paddle webhook timestamp outside tolerance")
    except ValueError:
        raise HTTPException(401, "Invalid Paddle webhook timestamp")
    obj        = data.get("data", {})
    db         = request.app.state.db

    # Extract email from customer object
    email    = obj.get("customer", {}).get("email", "") or \
               obj.get("custom_data", {}).get("email", "")
    price_id = obj.get("items", [{}])[0].get("price", {}).get("id", "") if obj.get("items") else ""
    plan     = PADDLE_PRICE_PLANS.get(price_id, "agency")

    if not await _claim_webhook_event(db, "paddle", event_id, data):
        return {"received": True, "duplicate": True}

    if event_type == "subscription.created":
        amount = obj.get("items", [{}])[0].get("price", {}).get("unit_price", {}).get("amount", 0)
        await _activate_plan(db, email, plan, "paddle", float(amount) / 100)

    elif event_type == "subscription.updated":
        new_price_id = obj.get("items", [{}])[0].get("price", {}).get("id", "")
        new_plan     = PADDLE_PRICE_PLANS.get(new_price_id, plan)
        await _upgrade_plan(db, email, new_plan)

    elif event_type == "subscription.cancelled":
        await _cancel_plan(db, email)

    elif event_type == "subscription.past_due":
        await _payment_failed(db, email)

    elif event_type == "transaction.completed":
        # One-time: lead credits, deliverability audit
        await _handle_one_time_purchase(db, email, price_id, "paddle")

    await _log_billing(db, email, event_type, "paddle", 0, data)
    return {"received": True}

# ── Shared lifecycle functions ──────────────────
async def _activate_plan(db, email: str, plan: str, provider: str, amount: float):
    """Activate paid plan — called on successful subscription"""
    async with db.acquire() as conn:
        row = await conn.fetchrow("SELECT id, name FROM tenants WHERE email=$1", email)
        if not row:
            return
        await conn.execute("""
            UPDATE tenants
            SET plan=$1, status='active', trial_ends_at=NULL, updated_at=NOW()
            WHERE email=$2
        """, plan, email)

    # Send confirmation via Resend
    await _send_plan_email(email, row["name"], plan, "activated", amount, provider)

async def _upgrade_plan(db, email: str, new_plan: str):
    async with db.acquire() as conn:
        await conn.execute("""
            UPDATE tenants SET plan=$1, status='active', updated_at=NOW()
            WHERE email=$2
        """, new_plan, email)

async def _cancel_plan(db, email: str):
    """Downgrade to trial limits on cancellation"""
    async with db.acquire() as conn:
        row = await conn.fetchrow("SELECT name FROM tenants WHERE email=$1", email)
        await conn.execute("""
            UPDATE tenants
            SET plan='early_adopter', status='cancelled', updated_at=NOW()
            WHERE email=$1
        """, email)
    if row:
        await _send_cancellation_email(email, row["name"])

async def _suspend_tenant(db, email: str):
    async with db.acquire() as conn:
        await conn.execute("""
            UPDATE tenants SET status='suspended', updated_at=NOW()
            WHERE email=$1
        """, email)

async def _ensure_active(db, email: str):
    async with db.acquire() as conn:
        await conn.execute("""
            UPDATE tenants SET status='active', updated_at=NOW()
            WHERE email=$1 AND status != 'suspended'
        """, email)

async def _payment_failed(db, email: str):
    """3-day grace period before suspension"""
    async with db.acquire() as conn:
        row = await conn.fetchrow("SELECT name, plan FROM tenants WHERE email=$1", email)
        if row:
            await _send_payment_failed_email(email, row["name"])
            # Grace: keep active for 3 days, provider retries

async def _handle_one_time_purchase(db, email: str, product_id: str, provider: str):
    """Add lead credits or AI credits on one-time purchase"""
    redis = None  # Get from app state if needed
    # Placeholder — map product_id to credit amount
    pass

async def _log_billing(db, email: str, event: str, provider: str, amount: float, raw: dict):
    from tenant_context import tenant_id_context
    async with db.acquire() as conn:
        tenant = await conn.fetchrow("SELECT id FROM tenants WHERE email=$1", email)
        if not tenant:
            return
        token = tenant_id_context.set(str(tenant["id"]))
        try:
            await conn.execute("""
                INSERT INTO billing_events
                (tenant_id, event_type, provider, amount, currency, metadata)
                VALUES ($1,$2,$3,$4,'USD',$5)
            """, tenant["id"], event, provider, amount, json.dumps(raw))
        finally:
            tenant_id_context.reset(token)

# ── Email notifications via Resend ──────────────
async def _send_plan_email(email: str, name: str, plan: str,
                            action: str, amount: float, provider: str):
    if not RESEND_KEY:
        return
    plan_display = plan.replace("_", " ").title()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_KEY}"},
                json={
                    "from": "FadeReach <billing@fadereach.tinlance.com>",
                    "to":   email,
                    "subject": f"You're on FadeReach {plan_display} ✦",
                    "html": f"""
                    <div style="font-family:Inter,sans-serif;max-width:520px">
                    <h2>Welcome to {plan_display}, {name}!</h2>
                    <p>Your FadeReach {plan_display} plan is now active.</p>
                    <p>
                      <a href="{APP_URL}/dashboard"
                         style="background:#00E5A0;color:#000;padding:12px 24px;
                                border-radius:8px;text-decoration:none;font-weight:600">
                        Open dashboard →
                      </a>
                    </p>
                    <p style="font-size:12px;color:#666">
                      Billed via {provider.title()}. Receipt sent separately.<br>
                      Questions? Reply to this email.
                    </p>
                    </div>
                    """
                }
            )
    except Exception as e:
        print(f"Plan email failed: {e}")

async def _send_cancellation_email(email: str, name: str):
    if not RESEND_KEY:
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_KEY}"},
                json={
                    "from": "FadeReach <billing@fadereach.tinlance.com>",
                    "to":   email,
                    "subject": "Your FadeReach subscription has been cancelled",
                    "html": f"""
                    <div style="font-family:Inter,sans-serif;max-width:520px">
                    <p>Hi {name},</p>
                    <p>Your FadeReach subscription has been cancelled.</p>
                    <p>Your data and campaigns are preserved. You can reactivate anytime.</p>
                    <p>
                      <a href="{APP_URL}/pricing">Reactivate →</a>
                    </p>
                    <p>If we did something wrong, reply to this email — I read every one.</p>
                    <p>— Lloyd, Tinlance Limited</p>
                    </div>
                    """
                }
            )
    except Exception as e:
        print(f"Cancellation email failed: {e}")

async def _send_payment_failed_email(email: str, name: str):
    if not RESEND_KEY:
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_KEY}"},
                json={
                    "from": "FadeReach <billing@fadereach.tinlance.com>",
                    "to":   email,
                    "subject": "Payment failed — action needed",
                    "html": f"""
                    <div style="font-family:Inter,sans-serif;max-width:520px">
                    <p>Hi {name},</p>
                    <p>Your recent FadeReach payment failed.</p>
                    <p>Your account stays active for 3 days while your payment provider retries.</p>
                    <p>
                      <a href="{APP_URL}/billing"
                         style="background:#FF6B35;color:#fff;padding:12px 24px;
                                border-radius:8px;text-decoration:none;font-weight:600">
                        Update payment method →
                      </a>
                    </p>
                    <p style="font-size:12px;color:#666">
                      Need help? Reply to this email.
                    </p>
                    </div>
                    """
                }
            )
    except Exception as e:
        print(f"Payment failed email error: {e}")

# ── Paddle signature verification ───────────────
def _verify_paddle_signature(body: bytes, signature: str, secret: str) -> bool:
    """Verify Paddle webhook signature (v1 format)"""
    try:
        # Parse Paddle signature header: ts=xxx;h1=xxx
        parts = dict(p.split("=", 1) for p in signature.split(";"))
        ts    = parts.get("ts", "")
        h1    = parts.get("h1", "")

        signed_payload = f"{ts}:{body.decode()}"
        expected = hmac.new(
            secret.encode(), signed_payload.encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, h1)
    except:
        return False
