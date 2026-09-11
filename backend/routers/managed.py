"""
FadeReach — Managed Services Router
Done-For-You tier ($999/mo) operations
Client onboarding · Campaign management · Weekly reports

Lloyd runs everything for Managed clients:
- Domain purchase + DNS setup
- 35-day warmup managed
- 500 verified leads/month built
- AI-written 4-email sequence
- Campaign launch + monitoring
- Weekly performance report
- Hot lead flagging + routing
- Monthly strategy call (60 min)
- ThreatFade email security audit
"""
from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from pydantic import BaseModel
from .deps import get_current_tenant, require_admin
import httpx, os, json
from datetime import datetime, timedelta
from typing import Optional

router = APIRouter()

RESEND_KEY = os.getenv("RESEND_API_KEY", "")
APP_URL    = os.getenv("APP_URL", "https://fadereach.tinlance.com")
CLAUDE_KEY = os.getenv("CLAUDE_API_KEY", "")

class ManagedClientReq(BaseModel):
    tenant_id:       str
    company:         str
    contact_name:    str
    contact_email:   str
    target_market:   str   # nigerian_fintech | african_agency | eu_security | us_proptech
    product_focus:   str   # Which Tinlance product to pitch
    sending_domain:  Optional[str] = None
    notes:           Optional[str] = None

class WeeklyReportReq(BaseModel):
    client_tenant_id: str
    week_start:       str  # ISO date
    week_end:         str

class StrategyCallReq(BaseModel):
    client_tenant_id: str
    scheduled_at:     str  # ISO datetime
    notes:            Optional[str] = None

# ── Managed client management (Lloyd-only) ──────
@router.post("/clients/onboard")
async def onboard_managed_client(
    req:              ManagedClientReq,
    background_tasks: BackgroundTasks,
    request:          Request,
    admin:            dict = Depends(require_admin),
):
    """
    Onboard a new Managed DFY client
    Triggers full setup workflow:
    1. Upgrade tenant to managed plan
    2. Set up managed client record
    3. Send welcome + next steps email
    4. Schedule first strategy call prompt
    """
    db = request.app.state.db

    async with db.acquire() as conn:
        # Create managed clients table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS managed_clients (
                id               SERIAL PRIMARY KEY,
                tenant_id        TEXT REFERENCES tenants(id),
                company          TEXT NOT NULL,
                contact_name     TEXT NOT NULL,
                contact_email    TEXT NOT NULL,
                target_market    TEXT,
                product_focus    TEXT,
                sending_domain   TEXT,
                notes            TEXT,
                status           TEXT DEFAULT 'onboarding',
                warmup_started   TIMESTAMPTZ,
                first_campaign   TIMESTAMPTZ,
                leads_delivered  INTEGER DEFAULT 0,
                campaigns_run    INTEGER DEFAULT 0,
                total_replies    INTEGER DEFAULT 0,
                contract_start   TIMESTAMPTZ DEFAULT NOW(),
                contract_months  INTEGER DEFAULT 3,
                monthly_fee      NUMERIC DEFAULT 999,
                created_at       TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        # Upgrade to managed plan
        await conn.execute("""
            UPDATE tenants
            SET plan='managed', status='active', updated_at=NOW()
            WHERE id=$1
        """, req.tenant_id)

        client_id = await conn.fetchval("""
            INSERT INTO managed_clients
            (tenant_id, company, contact_name, contact_email,
             target_market, product_focus, sending_domain, notes)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8) RETURNING id
        """, req.tenant_id, req.company, req.contact_name,
            req.contact_email, req.target_market,
            req.product_focus, req.sending_domain, req.notes)

    background_tasks.add_task(
        _send_managed_welcome,
        req.contact_email, req.contact_name, req.company
    )

    return {
        "client_id":  client_id,
        "tenant_id":  req.tenant_id,
        "status":     "onboarding",
        "next_steps": [
            f"Register sending domain for {req.company} (not their main domain)",
            "Configure DNS: SPF + DKIM (2048-bit) + DMARC",
            "Begin 35-day warmup — starts at 5 emails/day",
            "Build 500-lead verified list for target market",
            f"Write 4-step sequence for {req.product_focus} → {req.target_market}",
            "Book first strategy call within 7 days",
        ],
        "timeline": {
            "week_1":   "Domain setup + DNS + warmup start",
            "week_2_3": "Lead building + sequence writing",
            "week_4":   "Campaign launch + first sends",
            "ongoing":  "Weekly reports + hot lead routing",
        }
    }

@router.get("/clients")
async def list_managed_clients(
    request: Request,
    admin:   dict = Depends(require_admin),
):
    """List all managed DFY clients"""
    db = request.app.state.db
    async with db.acquire() as conn:
        clients = await conn.fetch("""
            SELECT mc.*, t.email as tenant_email
            FROM managed_clients mc
            JOIN tenants t ON mc.tenant_id = t.id
            ORDER BY mc.created_at DESC
        """)
    return {"clients": [dict(c) for c in clients]}

@router.get("/clients/{client_id}")
async def get_managed_client(
    client_id: int,
    request:   Request,
    admin:     dict = Depends(require_admin),
):
    """Get managed client details + performance"""
    db = request.app.state.db
    async with db.acquire() as conn:
        client = await conn.fetchrow(
            "SELECT * FROM managed_clients WHERE id=$1", client_id
        )
        if not client:
            raise HTTPException(404, "Client not found")

        campaigns = await conn.fetch("""
            SELECT name, status, emails_sent, replies,
                   open_rate, reply_rate, created_at
            FROM campaigns WHERE tenant_id=$1
            ORDER BY created_at DESC LIMIT 10
        """, client["tenant_id"])

        hot_leads = await conn.fetchval("""
            SELECT COUNT(*) FROM replies
            WHERE tenant_id=$1 AND is_hot=TRUE
        """, client["tenant_id"])

    return {
        "client":     dict(client),
        "campaigns":  [dict(c) for c in campaigns],
        "hot_leads":  int(hot_leads),
        "roi_estimate": {
            "monthly_fee": float(client["monthly_fee"]),
            "meetings_needed": 2,  # To break even assuming $500 average deal
            "current_hot_leads": int(hot_leads),
        }
    }

@router.post("/reports/weekly")
async def generate_weekly_report(
    req:              WeeklyReportReq,
    background_tasks: BackgroundTasks,
    request:          Request,
    admin:            dict = Depends(require_admin),
):
    """
    Generate and send weekly performance report to managed client
    White-label PDF delivered via Resend
    """
    db = request.app.state.db

    async with db.acquire() as conn:
        client = await conn.fetchrow("""
            SELECT mc.*, t.email
            FROM managed_clients mc
            JOIN tenants t ON mc.tenant_id = t.id
            WHERE mc.tenant_id=$1
        """, req.client_tenant_id)

        if not client:
            raise HTTPException(404, "Managed client not found")

        # Get week's stats
        week_stats = await conn.fetchrow("""
            SELECT
                COALESCE(SUM(emails_sent), 0) as sent,
                COALESCE(SUM(opens), 0)       as opens,
                COALESCE(SUM(replies), 0)      as replies,
                COALESCE(SUM(bounces), 0)      as bounces,
                COUNT(*)                        as campaigns
            FROM campaigns
            WHERE tenant_id=$1
            AND created_at BETWEEN $2 AND $3
        """, req.client_tenant_id, req.week_start, req.week_end)

        hot_leads_week = await conn.fetchval("""
            SELECT COUNT(*) FROM replies
            WHERE tenant_id=$1
            AND is_hot=TRUE
            AND received_at BETWEEN $2 AND $3
        """, req.client_tenant_id, req.week_start, req.week_end)

        interested_replies = await conn.fetch("""
            SELECT from_email, body, received_at
            FROM replies
            WHERE tenant_id=$1
            AND intent='interested'
            AND received_at BETWEEN $2 AND $3
            ORDER BY received_at DESC LIMIT 5
        """, req.client_tenant_id, req.week_start, req.week_end)

    stats = dict(week_stats)
    sent  = int(stats["sent"])

    # Build report data
    report = {
        "client":        dict(client),
        "week":          f"{req.week_start} to {req.week_end}",
        "stats": {
            "sent":       sent,
            "opens":      int(stats["opens"]),
            "replies":    int(stats["replies"]),
            "bounces":    int(stats["bounces"]),
            "open_rate":  round(int(stats["opens"]) / sent * 100, 1) if sent > 0 else 0,
            "reply_rate": round(int(stats["replies"]) / sent * 100, 1) if sent > 0 else 0,
            "hot_leads":  int(hot_leads_week),
        },
        "hot_leads": [dict(r) for r in interested_replies],
        "generated_at": datetime.utcnow().isoformat(),
    }

    # Send via Resend
    background_tasks.add_task(
        _send_weekly_report_email,
        client["email"], client["contact_name"],
        client["company"], report
    )

    return {
        "report_sent": True,
        "recipient":   client["email"],
        "week":        f"{req.week_start} to {req.week_end}",
        "stats":       report["stats"],
    }

@router.post("/strategy-call/schedule")
async def schedule_strategy_call(
    req:     StrategyCallReq,
    request: Request,
    admin:   dict = Depends(require_admin),
):
    """Schedule and notify managed client of strategy call"""
    db = request.app.state.db
    async with db.acquire() as conn:
        client = await conn.fetchrow("""
            SELECT mc.contact_email, mc.contact_name, mc.company
            FROM managed_clients mc
            WHERE mc.tenant_id=$1
        """, req.client_tenant_id)

    if not client:
        raise HTTPException(404, "Client not found")

    if RESEND_KEY:
        call_dt = datetime.fromisoformat(req.scheduled_at)
        async with httpx.AsyncClient(timeout=10.0) as client_http:
            await client_http.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_KEY}"},
                json={
                    "from":    "Lloyd at FadeReach <hello@fadereach.tinlance.com>",
                    "to":      client["contact_email"],
                    "subject": f"Strategy call scheduled — {call_dt.strftime('%A, %B %d at %I:%M %p')}",
                    "html":    f"""
                    <div style="font-family:Inter,sans-serif;max-width:520px">
                    <h2>Monthly strategy call confirmed</h2>
                    <p>Hi {client['contact_name']},</p>
                    <p>Your strategy call is confirmed for:</p>
                    <p style="font-size:18px;font-weight:700;color:#00E5A0">
                      {call_dt.strftime('%A, %B %d, %Y at %I:%M %p UTC')}
                    </p>
                    <p>We'll review campaign performance, discuss what's working, 
                    identify opportunities in your Opportunity Feed, and plan 
                    next month's campaigns.</p>
                    {f'<p><strong>Notes:</strong> {req.notes}</p>' if req.notes else ''}
                    <p style="font-size:12px;color:#666">
                      Questions before the call? Reply to this email.<br>
                      — Lloyd, Tinlance Limited
                    </p>
                    </div>
                    """
                }
            )

    return {
        "scheduled":  True,
        "client":     client["contact_name"],
        "company":    client["company"],
        "call_at":    req.scheduled_at,
        "email_sent": bool(RESEND_KEY),
    }

# ── Internal helpers ────────────────────────────
async def _send_managed_welcome(email: str, name: str, company: str):
    if not RESEND_KEY:
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_KEY}"},
                json={
                    "from":    "Lloyd at FadeReach <hello@fadereach.tinlance.com>",
                    "to":      email,
                    "subject": f"Welcome to FadeReach Managed Growth, {name}",
                    "html":    f"""
                    <div style="font-family:Inter,sans-serif;max-width:520px">
                    <h2>You're in. Let's build your outreach engine. ✦</h2>
                    <p>Hi {name},</p>
                    <p>Welcome to FadeReach Managed Growth for {company}. 
                    I'll be managing your entire outreach operation personally.</p>
                    <p><strong>Here's what happens in the next 7 days:</strong></p>
                    <ol>
                      <li>I'll register and configure a dedicated sending domain for {company}</li>
                      <li>DNS records set up (SPF, DKIM, DMARC)</li>
                      <li>35-day warmup begins — starts at 5 emails/day</li>
                      <li>I'll reach out to schedule your first strategy call</li>
                    </ol>
                    <p>While warmup runs (takes 35 days), I'll be building your 
                    500-lead verified list and writing your 4-step campaign sequences.</p>
                    <p>First sends go live on day 35. Then we monitor, optimize, 
                    and report weekly.</p>
                    <p>Questions? Reply directly to this email — I read every one.</p>
                    <p>— Lloyd<br>Tinlance Limited</p>
                    </div>
                    """
                }
            )
    except Exception as e:
        print(f"Managed welcome email error: {e}")

async def _send_weekly_report_email(
    email: str, name: str, company: str, report: dict
):
    if not RESEND_KEY:
        return
    stats = report["stats"]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_KEY}"},
                json={
                    "from":    "FadeReach Reports <reports@fadereach.tinlance.com>",
                    "to":      email,
                    "subject": f"{company} — Weekly Campaign Report",
                    "html":    f"""
                    <div style="font-family:Inter,sans-serif;max-width:600px;color:#1a1a2e">
                    <div style="background:#080C14;padding:24px;border-radius:12px;margin-bottom:24px">
                      <h2 style="color:#00E5A0;margin:0">Weekly Report</h2>
                      <p style="color:#94A3B8;margin:4px 0 0">{company} · {report['week']}</p>
                    </div>

                    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px">
                      {''.join(f"""
                      <div style="background:#F8FAFC;padding:16px;border-radius:8px;text-align:center">
                        <div style="font-size:24px;font-weight:800;color:#080C14">{v}</div>
                        <div style="font-size:11px;color:#94A3B8;margin-top:4px;text-transform:uppercase">{k}</div>
                      </div>
                      """ for k, v in [
                          ("Sent", stats['sent']),
                          ("Opens", f"{stats['open_rate']}%"),
                          ("Replies", f"{stats['reply_rate']}%"),
                          ("Hot leads", stats['hot_leads']),
                      ])}
                    </div>

                    {f"""
                    <div style="margin-bottom:24px">
                      <h3>Hot leads this week</h3>
                      {''.join(f'<div style="padding:12px;background:#F0FDF4;border-left:3px solid #00E5A0;margin-bottom:8px;border-radius:0 6px 6px 0"><strong>{r["from_email"]}</strong><br><small style="color:#666">{r["body"][:100]}...</small></div>' for r in report['hot_leads'][:3])}
                    </div>
                    """ if report['hot_leads'] else ''}

                    <p style="font-size:12px;color:#94A3B8">
                      Full analytics at {APP_URL}/dashboard<br>
                      Questions? Reply to this email.
                    </p>
                    </div>
                    """
                }
            )
    except Exception as e:
        print(f"Weekly report email error: {e}")
