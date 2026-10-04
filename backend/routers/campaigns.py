"""FadeReach — Campaigns Router
Create · Audit · Send · Reply detection · Auto-stop
"""
from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from pydantic import BaseModel
from .deps import get_current_tenant
import httpx, os
from datetime import datetime
from typing import Optional
from .providers import get_listmonk_connection
from tenant_context import tenant_id_context
from audit import record_audit

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
            (tenant_id, name, subject, body_html, product, target_segment, sequence_steps, status)
            VALUES ($1,$2,$3,$4,$5,$6,$7,'draft') RETURNING id
        """, tenant_id, req.name, req.subject,
            req.body_html, req.product, req.target_segment, req.sequence_steps)

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

@router.post("/{campaign_id}/send")
async def send_campaign(
    campaign_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    """Validate, queue and submit a campaign to the configured Listmonk adapter."""
    db = request.app.state.db
    tenant_id = auth["sub"]

    async with db.acquire() as conn:
        campaign = await conn.fetchrow(
            """SELECT id, name, subject, status, body_html, audit_score
               FROM campaigns WHERE id=$1 AND tenant_id=$2""",
            campaign_id, tenant_id,
        )
        if not campaign:
            raise HTTPException(404, "Campaign not found")
        if campaign["status"] not in {"draft", "paused"}:
            raise HTTPException(409, f"Campaign cannot be sent from status '{campaign['status']}'")
        if campaign["audit_score"] is None or campaign["audit_score"] < 70:
            raise HTTPException(409, "Campaign must pass the send-readiness audit (score >= 70)")
        provider = await conn.fetchrow(
            """SELECT id, base_url, api_username, api_token_ciphertext, from_email
               FROM provider_connections
               WHERE tenant_id=$1 AND provider_type='listmonk' AND status='active'""",
            tenant_id,
        )
        if not provider:
            raise HTTPException(503, "Configure a Listmonk provider before sending")
        blocked = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM domains
            WHERE tenant_id=$1
              AND (
                  sending_paused=TRUE
                  OR spf_valid=FALSE
                  OR dkim_valid=FALSE
                  OR dmarc_valid=FALSE
                  OR mx_valid=FALSE
                  OR bounce_rate > 1.5
                  OR complaint_rate > 0.05
              )
            """,
            tenant_id,
        )
        if blocked:
            raise HTTPException(
                409,
                "Sending is paused because deliverability controls or recent "
                "bounce/complaint thresholds are not healthy",
            )

        leads = await conn.fetch(
            """SELECT l.id, l.email, l.first_name, l.last_name, l.company, l.ai_first_line
               FROM leads l
               WHERE l.tenant_id=$1
                 AND l.status NOT IN ('replied','replied_positive','unsubscribed','bounced')
                 AND NOT EXISTS (
                     SELECT 1 FROM suppression_entries s
                     WHERE s.tenant_id=l.tenant_id AND lower(s.email)=lower(l.email)
                 )
               ORDER BY l.id
               LIMIT 10000""",
            tenant_id,
        )
        if not leads:
            raise HTTPException(409, "No eligible recipients remain after suppression and status checks")

        execution = None

    async with db.acquire() as conn:
        execution = await conn.fetchrow(
            """INSERT INTO campaign_executions
               (tenant_id, campaign_id, provider_connection_id, status, recipient_count)
               VALUES ($1,$2,$3,'queued',$4)
               RETURNING id""",
            tenant_id, campaign_id, provider["id"], len(leads),
        )
        await conn.execute(
            """INSERT INTO execution_jobs (tenant_id, execution_id, status)
               VALUES ($1,$2,'queued')""",
            tenant_id, execution["id"],
        )

    await record_audit(
        db, tenant_id, tenant_id, "campaign.send.queued",
        f"campaign:{campaign_id}",
        {"execution_id": execution["id"], "recipient_count": len(leads)},
    )
    return {
        "campaign_id": campaign_id,
        "execution_id": execution["id"],
        "status": "queued",
        "recipient_count": len(leads),
    }


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
            "UPDATE campaigns SET status='paused', updated_at=NOW() WHERE id=$1 AND tenant_id=$2",
            campaign_id, auth["sub"]
        )
        await conn.execute(
            """
            UPDATE campaign_executions
            SET cancel_requested=TRUE, updated_at=NOW()
            WHERE campaign_id=$1
              AND tenant_id=$2
              AND status IN ('queued','running')
            """,
            campaign_id, auth["sub"],
        )
        await conn.execute(
            """
            UPDATE execution_jobs
            SET status='cancelled', completed_at=NOW(), updated_at=NOW()
            WHERE execution_id IN (
                SELECT id FROM campaign_executions
                WHERE campaign_id=$1 AND tenant_id=$2 AND status='queued'
            )
              AND tenant_id=$2
              AND status='queued'
            """,
            campaign_id, auth["sub"],
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

async def _execute_listmonk_campaign(
    db, execution_id: int, tenant_id: str, campaign_id: int,
    leads: list[dict], provider: dict, campaign_name: str,
    subject: str, body_html: str,
):
    """Submit one idempotent campaign to Listmonk; delivery is tracked separately."""
    token = tenant_id_context.set(tenant_id)
    try:
        async with db.acquire() as conn:
            await conn.execute(
                "UPDATE campaign_executions SET status='running', started_at=NOW() WHERE id=$1",
                execution_id,
            )

        auth = (provider["api_username"], await _decrypt_provider_token(provider["api_token_ciphertext"]))
        base = provider["base_url"].rstrip("/")
        async with httpx.AsyncClient(timeout=20.0) as client:
            list_resp = await client.post(
                f"{base}/api/lists",
                auth=auth,
                json={
                    "name": f"FadeReach {campaign_name} #{execution_id}",
                    "type": "private",
                    "optin": "single",
                    "status": "active",
                },
            )
            if list_resp.status_code >= 300:
                raise RuntimeError(f"Listmonk list creation failed: HTTP {list_resp.status_code}")
            list_id = list_resp.json()["data"]["id"]

            eligible = 0
            for lead in leads:
                first = lead.get("first_name") or ""
                last = lead.get("last_name") or ""
                name = " ".join(x for x in [first, last] if x).strip() or lead["email"]
                resp = await client.post(
                    f"{base}/api/subscribers",
                    auth=auth,
                    json={
                        "email": lead["email"],
                        "name": name,
                        "status": "enabled",
                        "lists": [list_id],
                        "preconfirm_subscriptions": True,
                        "attribs": {
                            "company": lead.get("company") or "",
                            "ai_first_line": lead.get("ai_first_line") or "",
                            "fade_reach_lead_id": lead["id"],
                        },
                    },
                )
                if resp.status_code >= 300:
                    raise RuntimeError(f"Listmonk subscriber creation failed: HTTP {resp.status_code}")
                eligible += 1

            body = _to_listmonk_template(body_html)
            create = await client.post(
                f"{base}/api/campaigns",
                auth=auth,
                json={
                    "name": f"FadeReach {campaign_name} #{execution_id}",
                    "subject": subject,
                    "lists": [list_id],
                    "from_email": provider["from_email"],
                    "content_type": "html",
                    "messenger": "email",
                    "type": "regular",
                    "body": body,
                },
            )
            if create.status_code >= 300:
                raise RuntimeError(f"Listmonk campaign creation failed: HTTP {create.status_code}")
            external_id = create.json()["data"]["id"]

            start = await client.put(
                f"{base}/api/campaigns/{external_id}/status",
                auth=auth,
                json={"status": "running"},
            )
            if start.status_code >= 300:
                raise RuntimeError(f"Listmonk campaign start failed: HTTP {start.status_code}")

        async with db.acquire() as conn:
            await conn.execute(
                """UPDATE campaign_executions
                   SET status='succeeded', external_campaign_id=$1,
                       sent_count=0, completed_at=NOW()
                   WHERE id=$2""",
                external_id, execution_id,
            )
            await conn.execute(
                """UPDATE campaigns SET status='active', updated_at=NOW() WHERE id=$1 AND tenant_id=$2""",
                campaign_id, tenant_id,
            )
            await conn.executemany(
                """INSERT INTO messages
                   (tenant_id, campaign_id, execution_id, lead_id, recipient_email, subject, status, sent_at)
                   VALUES ($1,$2,$3,$4,$5,$6,'submitted',NOW())""",
                [
                    (tenant_id, campaign_id, execution_id, lead["id"], lead["email"], subject)
                    for lead in leads
                ],
            )
    except Exception as exc:
        async with db.acquire() as conn:
            await conn.execute(
                """UPDATE campaign_executions
                   SET status='failed', error_count=recipient_count,
                       error_message=$1, completed_at=NOW()
                   WHERE id=$2""",
                str(exc)[:1000], execution_id,
            )
    finally:
        tenant_id_context.reset(token)


async def _decrypt_provider_token(ciphertext: str) -> str:
    from cryptography.fernet import Fernet
    key = os.getenv("CREDENTIAL_ENCRYPTION_KEY", "")
    if not key:
        raise RuntimeError("Credential encryption is not configured")
    return Fernet(key.encode()).decrypt(ciphertext.encode()).decode()


def _to_listmonk_template(body: str) -> str:
    replacements = {
        "{{first_name}}": "{{ .Subscriber.FirstName }}",
        "{first_name}": "{{ .Subscriber.FirstName }}",
        "{{company}}": "{{ .Subscriber.Attribs.company }}",
        "{company}": "{{ .Subscriber.Attribs.company }}",
        "{{ai_first_line}}": "{{ .Subscriber.Attribs.ai_first_line }}",
        "{ai_first_line}": "{{ .Subscriber.Attribs.ai_first_line }}",
    }
    for source, target in replacements.items():
        body = body.replace(source, target)
    return body


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
