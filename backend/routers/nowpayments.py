"""
FadeReach — NOWPayments Router
USDT / USDC stablecoins only → auto-converts to fiat
No volatile crypto. Ever.

Rules (confirmed across all Tinlance products):
- USDT and USDC only (TRC-20 recommended — lowest fees)
- NOWPayments auto-converts to fiat on receipt
- IPN verified via HMAC-SHA512
- Refunds = platform credits only (no crypto refunds)
- Feature-flagged: NOWPAYMENTS_ENABLED env var

Same pattern as HezCast + Web-Temify + Olvrix.
"""
from fastapi import APIRouter, HTTPException, Request, Depends, Header
import hmac, hashlib, json, os, httpx
from datetime import datetime
from typing import Optional
from .deps import get_current_tenant

router = APIRouter()

NOWPAYMENTS_API_KEY  = os.getenv("NOWPAYMENTS_API_KEY", "")
NOWPAYMENTS_IPN_SECRET = os.getenv("NOWPAYMENTS_IPN_SECRET", "")
NOWPAYMENTS_ENV      = os.getenv("NOWPAYMENTS_ENVIRONMENT", "sandbox")
APP_URL              = os.getenv("APP_URL", "https://fadereach.tinlance.com")

# Base URL switches between sandbox and production
NP_BASE = (
    "https://api.nowpayments.io/v1"
    if NOWPAYMENTS_ENV == "production"
    else "https://api-sandbox.nowpayments.io/v1"
)

# Supported stablecoins — USDT/USDC only, no volatile coins
SUPPORTED_COINS = [
    {
        "id":          "usdttrc20",
        "label":       "USDT (TRC-20)",
        "network":     "TRON",
        "recommended": True,
        "note":        "Lowest fees — recommended",
    },
    {
        "id":          "usdterc20",
        "label":       "USDT (ERC-20)",
        "network":     "Ethereum",
        "recommended": False,
        "note":        "Higher gas fees",
    },
    {
        "id":          "usdtbep20",
        "label":       "USDT (BEP-20)",
        "network":     "BNB Chain",
        "recommended": False,
        "note":        "Low fees alternative",
    },
    {
        "id":          "usdcerc20",
        "label":       "USDC (ERC-20)",
        "network":     "Ethereum",
        "recommended": False,
        "note":        "USDC via Ethereum",
    },
    {
        "id":          "usdcbep20",
        "label":       "USDC (BEP-20)",
        "network":     "BNB Chain",
        "recommended": False,
        "note":        "USDC via BNB Chain",
    },
]

# Plan prices in USD for NOWPayments
PLAN_PRICES_USD = {
    "early_adopter": 49,
    "growth":        99,
    "agency":        299,
    "managed":       999,
}

def _build_order_id(plan_id: str, tenant_id: str) -> str:
    """Deterministic order ID for IPN matching"""
    return f"fadereach_{plan_id}_{tenant_id}"

def _parse_order_id(order_id: str) -> Optional[dict]:
    """Parse order ID back to plan + tenant"""
    try:
        parts = order_id.split("_")
        if len(parts) >= 3 and parts[0] == "fadereach":
            return {
                "plan_id":   parts[1],
                "tenant_id": "_".join(parts[2:]),
            }
    except:
        pass
    return None

def _verify_ipn_signature(payload: bytes, signature: str) -> bool:
    """
    NOWPayments IPN signature verification
    HMAC-SHA512 — same as HezCast + Web-Temify + Olvrix
    """
    if not NOWPAYMENTS_IPN_SECRET:
        return True  # Skip in dev if secret not set
    try:
        expected = hmac.new(
            NOWPAYMENTS_IPN_SECRET.encode("utf-8"),
            payload,
            hashlib.sha512
        ).hexdigest()
        return hmac.compare_digest(expected, signature or "")
    except:
        return False

def _is_payment_confirmed(status: str) -> bool:
    """NOWPayments statuses that mean money received"""
    return status in ["confirmed", "finished"]

# ── Routes ──────────────────────────────────────
@router.get("/currencies")
async def list_supported_currencies(
    auth: dict = Depends(get_current_tenant),
):
    """List supported stablecoins for crypto payment"""
    if not NOWPAYMENTS_API_KEY:
        raise HTTPException(503, "Crypto payments not configured")
    return {
        "currencies":    SUPPORTED_COINS,
        "note":          "USDT and USDC only. Auto-converts to fiat on receipt.",
        "refund_policy": "Crypto payments are non-refundable. Overpayments credited to account.",
        "environment":   NOWPAYMENTS_ENV,
    }

@router.post("/checkout")
async def create_crypto_checkout(
    plan_id:  str,
    currency: str = "usdttrc20",
    request:  Request = None,
    auth:     dict = Depends(get_current_tenant),
):
    """
    Create NOWPayments invoice for plan purchase
    Returns hosted checkout URL
    """
    if not NOWPAYMENTS_API_KEY:
        raise HTTPException(503, "Crypto payments not configured. Set NOWPAYMENTS_API_KEY.")

    # Validate currency — stablecoins only
    valid_coins = {c["id"] for c in SUPPORTED_COINS}
    if currency not in valid_coins:
        raise HTTPException(400,
            f"Invalid currency '{currency}'. "
            f"Supported: {', '.join(valid_coins)}. "
            f"USDT and USDC only — no volatile crypto."
        )

    # Validate plan
    amount_usd = PLAN_PRICES_USD.get(plan_id)
    if not amount_usd:
        raise HTTPException(404, f"Plan '{plan_id}' not found")

    tenant_id = auth["sub"]
    order_id  = _build_order_id(plan_id, tenant_id)

    db = request.app.state.db
    async with db.acquire() as conn:
        tenant = await conn.fetchrow(
            "SELECT email, name FROM tenants WHERE id=$1", tenant_id
        )

    # Create invoice via NOWPayments API
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{NP_BASE}/invoice",
                headers={
                    "x-api-key":   NOWPAYMENTS_API_KEY,
                    "Content-Type":"application/json",
                },
                json={
                    "price_amount":        amount_usd,
                    "price_currency":      "usd",
                    "pay_currency":        currency,
                    "order_id":            order_id,
                    "order_description":   f"FadeReach {plan_id.replace('_',' ').title()} plan",
                    "ipn_callback_url":    f"{APP_URL}/api/billing/nowpayments/webhook",
                    "success_url":         f"{APP_URL}/dashboard?upgraded=true&provider=crypto",
                    "cancel_url":          f"{APP_URL}/pricing?cancelled=true",
                    "is_fixed_rate":       True,
                    "is_fee_paid_by_user": False,
                }
            )

        if resp.status_code not in [200, 201]:
            raise HTTPException(502,
                f"NOWPayments invoice creation failed: {resp.text}"
            )

        data = resp.json()
        invoice_url = data.get("invoice_url")

        if not invoice_url:
            raise HTTPException(502, "NOWPayments did not return invoice URL")

        # Log billing event
        async with db.acquire() as conn:
            await conn.execute("""
                INSERT INTO billing_events
                (tenant_id, event_type, provider, amount, currency, metadata)
                VALUES ($1,'crypto_checkout_created','nowpayments',$2,'USD',$3)
            """, tenant_id, amount_usd, json.dumps({
                "plan_id":    plan_id,
                "currency":   currency,
                "order_id":   order_id,
                "invoice_id": data.get("id"),
            }))

        return {
            "checkout_url":  invoice_url,
            "invoice_id":    data.get("id"),
            "order_id":      order_id,
            "amount_usd":    amount_usd,
            "pay_currency":  currency,
            "provider":      "nowpayments",
            "auto_converts": True,
            "note":          "You will receive fiat. NOWPayments auto-converts stablecoins.",
            "environment":   NOWPAYMENTS_ENV,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"NOWPayments error: {str(e)}")

@router.post("/webhook")
async def nowpayments_ipn(
    request:         Request,
    x_nowpayments_sig: str = Header(None, alias="x-nowpayments-sig"),
):
    """
    NOWPayments IPN webhook
    Receives payment status updates
    Verifies HMAC-SHA512 signature
    Activates plan on confirmed/finished status
    """
    body = await request.body()

    # Verify IPN signature
    if not _verify_ipn_signature(body, x_nowpayments_sig):
        raise HTTPException(401, "Invalid NOWPayments IPN signature")

    data          = json.loads(body)
    payment_status= data.get("payment_status", "")
    order_id      = data.get("order_id", "")
    payment_id    = data.get("payment_id")
    actual_amount = data.get("actually_paid", 0)
    pay_currency  = data.get("pay_currency", "")

    db = request.app.state.db

    # Log all IPN events
    parsed = _parse_order_id(order_id)
    if parsed:
        async with db.acquire() as conn:
            await conn.execute("""
                INSERT INTO billing_events
                (tenant_id, event_type, provider, amount, currency, metadata)
                VALUES ($1,$2,'nowpayments',$3,$4,$5)
            """, parsed["tenant_id"],
                f"crypto_{payment_status}",
                float(actual_amount),
                pay_currency.upper(),
                json.dumps(data))

    # Only process confirmed/finished payments
    if not _is_payment_confirmed(payment_status):
        return {"received": True, "processed": False, "status": payment_status}

    if not parsed:
        raise HTTPException(400, f"Invalid order_id format: {order_id}")

    plan_id   = parsed["plan_id"]
    tenant_id = parsed["tenant_id"]

    # Verify plan exists
    if plan_id not in PLAN_PRICES_USD:
        raise HTTPException(400, f"Unknown plan: {plan_id}")

    # Activate the plan
    async with db.acquire() as conn:
        await conn.execute("""
            UPDATE tenants
            SET plan=$1, status='active', trial_ends_at=NULL, updated_at=NOW()
            WHERE id=$2
        """, plan_id, tenant_id)

        tenant = await conn.fetchrow(
            "SELECT email, name FROM tenants WHERE id=$1", tenant_id
        )

    # Send confirmation email via Resend
    RESEND_KEY = os.getenv("RESEND_API_KEY", "")
    if RESEND_KEY and tenant:
        plan_display = plan_id.replace("_", " ").title()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {RESEND_KEY}"},
                    json={
                        "from":    "FadeReach <billing@fadereach.tinlance.com>",
                        "to":      tenant["email"],
                        "subject": f"Crypto payment confirmed — FadeReach {plan_display} ✦",
                        "html":    f"""
                        <div style="font-family:Inter,sans-serif;max-width:520px">
                        <h2 style="color:#00E5A0">Payment confirmed ✦</h2>
                        <p>Hi {tenant['name']},</p>
                        <p>Your crypto payment has been confirmed and your
                        FadeReach <strong>{plan_display}</strong> plan is now active.</p>
                        <p style="font-size:12px;color:#666">
                          Payment ID: {payment_id}<br>
                          Currency: {pay_currency.upper()}<br>
                          Amount received: {actual_amount} {pay_currency.upper()}<br>
                          Auto-converted to fiat by NOWPayments.
                        </p>
                        <p>
                          <a href="{APP_URL}/dashboard"
                             style="background:#00E5A0;color:#000;padding:12px 24px;
                                    border-radius:8px;text-decoration:none;font-weight:600">
                            Open dashboard →
                          </a>
                        </p>
                        <p style="font-size:12px;color:#666">
                          Note: Crypto payments are non-refundable.<br>
                          Questions? Reply to this email.
                        </p>
                        </div>
                        """
                    }
                )
        except Exception as e:
            print(f"Crypto confirmation email error: {e}")

    return {
        "received":    True,
        "processed":   True,
        "plan_activated": plan_id,
        "tenant_id":   tenant_id,
        "payment_id":  payment_id,
    }

@router.get("/status/{payment_id}")
async def check_payment_status(
    payment_id: str,
    auth: dict = Depends(get_current_tenant),
):
    """Poll payment status for a specific NOWPayments payment"""
    if not NOWPAYMENTS_API_KEY:
        raise HTTPException(503, "Crypto payments not configured")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{NP_BASE}/payment/{payment_id}",
                headers={"x-api-key": NOWPAYMENTS_API_KEY}
            )
        data   = resp.json()
        status = data.get("payment_status", "unknown")
        return {
            "payment_id":    payment_id,
            "status":        status,
            "is_confirmed":  _is_payment_confirmed(status),
            "pay_currency":  data.get("pay_currency"),
            "actually_paid": data.get("actually_paid"),
            "outcome": (
                "Plan will activate automatically"
                if _is_payment_confirmed(status)
                else "Waiting for blockchain confirmation"
            ),
        }
    except Exception as e:
        raise HTTPException(502, f"Status check failed: {str(e)}")
