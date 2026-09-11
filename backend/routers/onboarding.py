"""
FadeReach — Onboarding Router
Guided setup · Step tracking · < 30 min to first campaign
"""
from fastapi import APIRouter, Request, Depends, BackgroundTasks
from pydantic import BaseModel
from .deps import get_current_tenant
import httpx, os

router = APIRouter()
RESEND_KEY = os.getenv("RESEND_API_KEY", "")
APP_URL    = os.getenv("APP_URL", "https://fadereach.tinlance.com")

# Onboarding steps in order
STEPS = [
    {
        "id":          "workspace_ready",
        "title":       "Workspace is live",
        "description": "Your FadeReach workspace is set up and ready.",
        "auto":        True,  # Completed automatically on signup
        "cta":         None,
        "cta_url":     None,
        "time_est":    None,
    },
    {
        "id":          "domain_added",
        "title":       "Add your sending domain",
        "description": "Add a dedicated domain for cold outreach. Not your main brand domain.",
        "auto":        False,
        "cta":         "Add domain",
        "cta_url":     "/domains",
        "time_est":    "2 min",
        "tip":         "Use a domain variation — e.g. if you own tinlance.com, register tinlance-reach.com",
    },
    {
        "id":          "dns_verified",
        "title":       "Configure DNS records",
        "description": "Add SPF, DKIM, and DMARC records. We show you exactly what to paste in Cloudflare.",
        "auto":        False,
        "cta":         "Check DNS",
        "cta_url":     "/domains",
        "time_est":    "5 min",
        "tip":         "All three records are required. Missing DKIM alone costs 15% inbox placement.",
    },
    {
        "id":          "first_lead",
        "title":       "Find your first leads",
        "description": "Search for prospects by company domain. We verify emails automatically.",
        "auto":        False,
        "cta":         "Find leads",
        "cta_url":     "/leads",
        "time_est":    "3 min",
        "tip":         "Start with 10-20 leads. Quality beats quantity on your first campaign.",
    },
    {
        "id":          "ai_generated",
        "title":       "Generate AI first lines",
        "description": "Select your leads and generate personalized openers with one click.",
        "auto":        False,
        "cta":         "Generate first lines",
        "cta_url":     "/leads",
        "time_est":    "2 min",
        "tip":         "AI first lines get 2-3x more replies than generic openers. Use them.",
    },
    {
        "id":          "first_campaign",
        "title":       "Create your first campaign",
        "description": "Build a 4-step sequence. The AI auditor reviews it before you send.",
        "auto":        False,
        "cta":         "Create campaign",
        "cta_url":     "/campaigns",
        "time_est":    "10 min",
        "tip":         "Email 1: personalized opener + one value line + soft CTA. Keep it under 100 words.",
    },
    {
        "id":          "warmup_started",
        "title":       "Warmup is running",
        "description": "Your domain is warming up automatically. Starts at 5 emails/day.",
        "auto":        True,
        "cta":         "View warmup",
        "cta_url":     "/domains",
        "time_est":    None,
        "tip":         "Warmup takes 35 days. Do not skip it — it determines inbox placement for months.",
    },
]

class StepCompleteReq(BaseModel):
    step_id: str

@router.get("/status")
async def onboarding_status(
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    """Full onboarding status — which steps done, what's next"""
    db        = request.app.state.db
    redis     = request.app.state.redis
    tenant_id = auth["sub"]

    # Get completed steps from Redis
    completed = await redis.smembers(f"onboarding:{tenant_id}") or set()

    # Mark auto-complete steps
    auto_steps = {s["id"] for s in STEPS if s["auto"]}
    completed  = completed | auto_steps

    # Find next incomplete step
    next_step = None
    for step in STEPS:
        if step["id"] not in completed:
            next_step = step
            break

    # Calculate progress
    total     = len(STEPS)
    done      = len([s for s in STEPS if s["id"] in completed])
    progress  = round(done / total * 100)
    all_done  = done == total

    # Build steps with status
    steps_with_status = []
    for step in STEPS:
        steps_with_status.append({
            **step,
            "completed": step["id"] in completed,
            "is_next":   step == next_step,
        })

    # Update DB if all done
    if all_done:
        async with db.acquire() as conn:
            await conn.execute(
                "UPDATE tenants SET onboarded=TRUE WHERE id=$1 AND onboarded=FALSE",
                tenant_id
            )

    return {
        "progress":    progress,
        "steps_done":  done,
        "steps_total": total,
        "all_done":    all_done,
        "next_step":   next_step,
        "steps":       steps_with_status,
        "message":     _progress_message(progress),
    }

@router.post("/complete-step")
async def complete_step(
    req: StepCompleteReq,
    background_tasks: BackgroundTasks,
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    """Mark an onboarding step as complete"""
    redis     = request.app.state.redis
    tenant_id = auth["sub"]

    valid_ids = {s["id"] for s in STEPS}
    if req.step_id not in valid_ids:
        from fastapi import HTTPException
        raise HTTPException(400, f"Unknown step: {req.step_id}")

    await redis.sadd(f"onboarding:{tenant_id}", req.step_id)
    completed = await redis.smembers(f"onboarding:{tenant_id}")
    auto_steps = {s["id"] for s in STEPS if s["auto"]}
    completed  = completed | auto_steps
    done       = len([s for s in STEPS if s["id"] in completed])
    progress   = round(done / len(STEPS) * 100)

    # Send congrats email on first campaign
    if req.step_id == "first_campaign":
        background_tasks.add_task(
            _send_first_campaign_email,
            request.app.state.db, tenant_id
        )

    return {
        "step_id":  req.step_id,
        "completed": True,
        "progress":  progress,
        "message":   _step_complete_message(req.step_id),
    }

@router.get("/checklist")
async def quick_checklist(
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    """
    Lightweight checklist for dashboard sidebar widget
    Returns only incomplete steps
    """
    redis     = request.app.state.redis
    tenant_id = auth["sub"]
    completed = await redis.smembers(f"onboarding:{tenant_id}") or set()
    auto_steps = {s["id"] for s in STEPS if s["auto"]}
    completed  = completed | auto_steps

    pending = [
        {
            "id":       s["id"],
            "title":    s["title"],
            "cta":      s["cta"],
            "cta_url":  s["cta_url"],
            "time_est": s["time_est"],
        }
        for s in STEPS if s["id"] not in completed
    ]

    return {
        "pending":   pending,
        "remaining": len(pending),
        "all_done":  len(pending) == 0,
    }

# ── Helpers ──────────────────────────────────────
def _progress_message(pct: int) -> str:
    if pct == 0:   return "Let's get started — first campaign in under 30 minutes."
    if pct < 30:   return "Good start. Add your sending domain next."
    if pct < 60:   return "Halfway there. Build your lead list next."
    if pct < 90:   return "Almost ready. Create your first campaign."
    if pct < 100:  return "One step away from your first send."
    return "Setup complete. Your first campaign is live. 🚀"

def _step_complete_message(step_id: str) -> str:
    messages = {
        "domain_added":   "Domain added. Checking DNS records now...",
        "dns_verified":   "DNS verified. Warmup starting automatically.",
        "first_lead":     "First leads found. Generate AI first lines next.",
        "ai_generated":   "First lines generated. Create your campaign now.",
        "first_campaign": "Campaign created. AI auditor reviewing it now.",
        "warmup_started": "Warmup is running. Check back in 7 days.",
    }
    return messages.get(step_id, "Step complete.")

async def _send_first_campaign_email(db, tenant_id: str):
    """Celebrate first campaign via Resend"""
    if not RESEND_KEY:
        return
    try:
        async with db.acquire() as conn:
            tenant = await conn.fetchrow(
                "SELECT email, name FROM tenants WHERE id=$1", tenant_id
            )
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_KEY}"},
                json={
                    "from":    "Lloyd at FadeReach <hello@fadereach.tinlance.com>",
                    "to":      tenant["email"],
                    "subject": "First campaign created ✦",
                    "html":    f"""
                    <div style="font-family:Inter,sans-serif;max-width:520px;color:#1a1a2e">
                    <h2>First campaign created, {tenant['name']}.</h2>
                    <p>The AI auditor is reviewing your campaign now.
                    Check your score and fix any issues before sending.</p>
                    <p>A few things that dramatically improve reply rates:</p>
                    <ul>
                      <li>Keep email under 100 words</li>
                      <li>One CTA only</li>
                      <li>Reference something specific about the prospect</li>
                      <li>Send Tuesday–Thursday, 8–10am recipient timezone</li>
                    </ul>
                    <p>
                      <a href="{APP_URL}/campaigns"
                         style="background:#00E5A0;color:#000;padding:12px 24px;
                                border-radius:8px;text-decoration:none;font-weight:600">
                        Review your campaign →
                      </a>
                    </p>
                    <p style="font-size:12px;color:#666">— Lloyd, Tinlance Limited</p>
                    </div>
                    """
                }
            )
    except Exception as e:
        print(f"First campaign email error: {e}")
