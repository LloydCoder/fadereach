"""FadeReach — Campaigns Router
Create · Audit · Send · Reply detection · Auto-stop
"""
from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from pydantic import BaseModel
from .deps import get_current_tenant
import httpx, os
from datetime import datetime
from typing import Optional

router = APIRouter()
CLAUDE_KEY = os.getenv("CLAUDE_API_KEY", "")

SPAM_WORDS = [
    "guaranteed","free money","act now","limited time","click here",
    "buy now","earn extra","work from home","risk free","no obligation",
    "winner","congratulations","urgent","dear friend","once in a lifetime",
    "make money fast","100% free","eliminate debt","lose weight"
]

class CampaignCreateReq(BaseModel):
    name:           str
    subject:        str
    body_html:      str
    product:        str | None = None
    target_segment: str | None = None
    sequence_steps: int = 4

class CampaignAuditReq(BaseModel):
    subject:   str
    body_html: str
    sequence:  list[dict] | None = None

@router.post("/create")
async def create_campaign(
    req: CampaignCreateReq,
    background_tasks: BackgroundTasks,
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    db        = request.app.state.db
    tenant_id = auth["sub"]

    async with db.acquire() as conn:
        tenant = await conn.fetchrow(
            "SELECT listmonk_url, plan, status, trial_ends_at FROM tenants WHERE id=$1",
            tenant_id
        )
        if not tenant:
            raise HTTPException(404, "Tenant not found")
        if not tenant["listmonk_url"]:
            raise HTTPException(503,
                "Workspace still setting up. Try again in 60 seconds."
            )
        # Trial: limited sends
        if tenant["status"] == "trial":
            sent = await conn.fetchval(
                "SELECT COALESCE(SUM(emails_sent),0) FROM campaigns WHERE tenant_id=$1",
                tenant_id
            )
            if sent >= 50:
                raise HTTPException(403,
                    "Trial limit reached (50 emails). Upgrade to continue sending."
                )

        campaign_id = await conn.fetchval("""
            INSERT INTO campaigns
            (tenant_id, name, subject, product, target_segment, sequence_steps, status)
            VALUES ($1,$2,$3,$4,$5,$6,'draft') RETURNING id
        """, tenant_id, req.name, req.subject,
            req.product, req.target_segment, req.sequence_steps)

    # Auto-run AI Campaign Auditor
    background_tasks.add_task(
        _run_campaign_audit, db, campaign_id,
        req.subject, req.body_html
    )

    return {
        "campaign_id": campaign_id,
        "status":      "draft",
        "message":     "Campaign created. AI auditor running...",
        "next_step":   "Check audit results before sending"
    }

@router.post("/audit")
async def audit_campaign(
    req: CampaignAuditReq,
    auth: dict = Depends(get_current_tenant)
):
    """
    AI Campaign Auditor — Phase 3 killer feature, available from Phase 1
    Scores subject line, body, CTA, spam words, personalization, length
    """
    score  = 100
    issues = []
    recommendations = []

    # ── Subject line analysis ──────────────────
    subject = req.subject
    if len(subject) > 50:
        score -= 10
        issues.append("Subject line too long")
        recommendations.append(
            f"Shorten subject to under 50 chars. Current: {len(subject)}. "
            f"Try: '{subject[:45]}...'"
        )
    if len(subject) < 15:
        score -= 5
        issues.append("Subject line too short — may seem cryptic")
        recommendations.append("Add more context to subject. Aim for 30-45 characters.")

    subject_lower = subject.lower()
    if any(w in subject_lower for w in ["re:", "fwd:"]):
        score -= 15
        issues.append("Fake reply prefix detected")
        recommendations.append(
            "Remove 'Re:' or 'Fwd:' prefixes — treating prospects as stupid "
            "destroys trust and can get you blacklisted."
        )
    if "?" in subject and subject.count("?") > 1:
        score -= 5
        issues.append("Multiple question marks in subject")
        recommendations.append("Use one question mark maximum. Multiple reads as desperate.")

    # ── Spam word detection ───────────────────
    body_lower = req.body_html.lower()
    found_spam = [w for w in SPAM_WORDS if w in body_lower or w in subject_lower]
    if found_spam:
        score -= len(found_spam) * 8
        issues.append(f"Spam trigger words: {', '.join(found_spam)}")
        recommendations.append(
            f"Remove these words: {', '.join(found_spam)}. "
            f"They trigger spam filters before a human reads your email."
        )

    # ── Body length analysis ──────────────────
    # Strip HTML for word count
    import re
    clean_body = re.sub(r'<[^>]+>', ' ', req.body_html)
    word_count = len(clean_body.split())
    if word_count > 200:
        score -= 10
        issues.append(f"Email too long ({word_count} words)")
        recommendations.append(
            f"Cut to under 150 words. Current: {word_count}. "
            f"Cold emails are not proposals — get to the point."
        )
    if word_count < 30:
        score -= 5
        issues.append("Email too short — may lack context")
        recommendations.append(
            "Add a brief value statement and clear CTA. Aim for 60-120 words."
        )

    # ── CTA analysis ──────────────────────────
    cta_signals = ["book", "call", "schedule", "demo", "reply", "interested", "learn more"]
    cta_count = sum(1 for c in cta_signals if c in body_lower)
    if cta_count == 0:
        score -= 15
        issues.append("No clear call-to-action detected")
        recommendations.append(
            "Add one clear CTA. Best performing: "
            "'Would a 15-minute call this week make sense?' or "
            "'Is this worth a quick chat?'"
        )
    if cta_count > 2:
        score -= 10
        issues.append("Multiple CTAs — choice paralysis")
        recommendations.append(
            f"Found {cta_count} CTAs. Reduce to exactly ONE. "
            f"Multiple CTAs decrease reply rates by up to 40%."
        )

    # ── Personalization check ─────────────────
    personal_signals = ["{first_name}", "{company}", "{{first_name}}", "{{company}}",
                        "first_line", "ai_first_line"]
    has_personalization = any(p in req.body_html for p in personal_signals)
    if not has_personalization:
        score -= 10
        issues.append("No personalization tokens found")
        recommendations.append(
            "Add at minimum {{first_name}} and {{company}}. "
            "Better: use AI first-line generation for unique openers."
        )

    # ── Grade calculation ─────────────────────
    score = max(0, min(100, score))
    grade = "A" if score>=90 else "B" if score>=75 else "C" if score>=60 else "D"

    # ── Claude enhancement ────────────────────
    ai_suggestions = []
    if CLAUDE_KEY and issues:
        ai_suggestions = await _claude_audit_suggestions(
            req.subject, req.body_html, issues
        )

    return {
        "score":           score,
        "grade":           grade,
        "ready_to_send":   score >= 70 and len([i for i in issues if "spam" in i.lower() or "CTA" in i]) == 0,
        "issues_count":    len(issues),
        "issues":          issues,
        "recommendations": recommendations,
        "ai_suggestions":  ai_suggestions,
        "metrics": {
            "word_count":           word_count,
            "subject_length":       len(subject),
            "spam_words_found":     len(found_spam),
            "cta_count":            cta_count,
            "has_personalization":  has_personalization,
        }
    }

@router.get("")
async def list_campaigns(
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    db = request.app.state.db
    async with db.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, name, subject, status, product, target_segment,
                   emails_sent, opens, clicks, replies, bounces,
                   audit_score,
                   CASE WHEN emails_sent > 0
                        THEN ROUND(opens::numeric/emails_sent*100, 1)
                        ELSE 0 END as open_rate,
                   CASE WHEN emails_sent > 0
                        THEN ROUND(replies::numeric/emails_sent*100, 1)
                        ELSE 0 END as reply_rate,
                   CASE WHEN emails_sent > 0
                        THEN ROUND(bounces::numeric/emails_sent*100, 1)
                        ELSE 0 END as bounce_rate,
                   created_at, updated_at
            FROM campaigns WHERE tenant_id=$1
            ORDER BY created_at DESC
        """, auth["sub"])
    return {"campaigns": [dict(r) for r in rows]}

@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: int,
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    db = request.app.state.db
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, status FROM campaigns WHERE id=$1 AND tenant_id=$2",
            campaign_id, auth["sub"]
        )
        if not row:
            raise HTTPException(404, "Campaign not found")
        await conn.execute(
            "UPDATE campaigns SET status='paused', updated_at=NOW() WHERE id=$1",
            campaign_id
        )
    return {"campaign_id": campaign_id, "status": "paused"}

@router.post("/{campaign_id}/resume")
async def resume_campaign(
    campaign_id: int,
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    db = request.app.state.db
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, status FROM campaigns WHERE id=$1 AND tenant_id=$2",
            campaign_id, auth["sub"]
        )
        if not row:
            raise HTTPException(404, "Campaign not found")
        if row["status"] == "active":
            raise HTTPException(400, "Campaign is already active")
        await conn.execute(
            "UPDATE campaigns SET status='active', updated_at=NOW() WHERE id=$1",
            campaign_id
        )
    return {"campaign_id": campaign_id, "status": "active"}

# ── Internal helpers ────────────────────────────
async def _run_campaign_audit(db, campaign_id: int, subject: str, body: str):
    """Background: auto-score campaign on creation"""
    try:
        import re
        score  = 100
        issues = []

        body_lower    = body.lower()
        subject_lower = subject.lower()
        clean_body    = re.sub(r'<[^>]+>', ' ', body)
        word_count    = len(clean_body.split())

        if len(subject) > 50:
            score -= 10; issues.append("Subject too long")
        found_spam = [w for w in SPAM_WORDS if w in body_lower or w in subject_lower]
        if found_spam:
            score -= len(found_spam) * 8; issues.append(f"Spam words: {found_spam}")
        if word_count > 200:
            score -= 10; issues.append("Body too long")
        cta_count = sum(1 for c in ["book","call","demo","reply","interested"] if c in body_lower)
        if cta_count == 0:
            score -= 15; issues.append("No CTA")
        if cta_count > 2:
            score -= 10; issues.append("Multiple CTAs")

        score = max(0, min(100, score))

        async with db.acquire() as conn:
            await conn.execute("""
                UPDATE campaigns
                SET audit_score=$1, audit_issues=$2, updated_at=NOW()
                WHERE id=$3
            """, score, __import__('json').dumps(issues), campaign_id)
    except Exception as e:
        print(f"Campaign audit error [{campaign_id}]: {e}")

async def _claude_audit_suggestions(subject: str, body: str, issues: list) -> list:
    """Claude-powered audit suggestions"""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key":         CLAUDE_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type":      "application/json"
                },
                json={
                    "model":      "claude-haiku-4-5-20251001",
                    "max_tokens": 300,
                    "messages": [{
                        "role": "user",
                        "content": f"""You are a cold email expert. Review this email and give 3 specific improvement suggestions.

Subject: {subject}
Issues found: {issues}

Give 3 concrete, actionable suggestions as a JSON array:
[{{"issue": "...", "fix": "...", "example": "..."}}]

Return ONLY the JSON array, no explanation."""
                    }]
                }
            )
        import json, re
        text = resp.json()["content"][0]["text"].strip()
        text = re.sub(r'```json|```', '', text).strip()
        return json.loads(text)
    except:
        return []
