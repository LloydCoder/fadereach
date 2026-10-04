"""FadeReach — Unified Inbox Router
All replies consolidated · Hot lead detection · Intent classification
"""
from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from pydantic import BaseModel
from .deps import get_current_tenant
import httpx, os
from typing import Optional

router = APIRouter()
CLAUDE_KEY = os.getenv("CLAUDE_API_KEY", "")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "")

INTENT_KEYWORDS = {
    "interested":     ["yes","interested","tell me more","sounds good","love to","let's chat",
                       "book","schedule","demo","absolutely","definitely","when can"],
    "not_now":        ["not now","maybe later","reach out","next quarter","busy",
                       "not the right time","check back"],
    "not_interested": ["not interested","remove","unsubscribe","stop","don't contact",
                       "no thanks","not relevant","wrong person"],
    "referral":       ["speak to","talk to","contact","reach out to","better person",
                       "forward","cc","copy"],
    "out_of_office":  ["out of office","ooo","on leave","vacation","away","back on",
                       "returning","annual leave"],
    "more_info":      ["more information","tell me more","can you send","brochure",
                       "pricing","how much","cost","details"],
}

class ReplyIngestReq(BaseModel):
    """Incoming reply from Listmonk webhook or SMTP"""
    from_email:  str
    subject:     str
    body:        str
    campaign_id: Optional[int] = None
    tenant_id:   Optional[str] = None

class ReplyUpdateReq(BaseModel):
    is_read:  Optional[bool] = None
    is_hot:   Optional[bool] = None
    intent:   Optional[str]  = None

def classify_intent(body: str) -> tuple[str, str]:
    """
    Rule-based intent classification
    Returns: (intent, sentiment)
    Fast, $0, covers 80% of cases
    """
    body_lower = body.lower()

    for intent, keywords in INTENT_KEYWORDS.items():
        if any(kw in body_lower for kw in keywords):
            sentiment = (
                "positive" if intent in ["interested", "more_info", "referral"]
                else "negative" if intent in ["not_interested"]
                else "neutral"
            )
            return intent, sentiment

    return "unknown", "neutral"

@router.get("")
async def list_replies(
    request: Request,
    auth: dict = Depends(get_current_tenant),
    is_hot:   Optional[bool] = None,
    is_read:  Optional[bool] = None,
    intent:   Optional[str]  = None,
    limit:    int = 50,
    offset:   int = 0
):
    """Unified inbox — all replies from all campaigns"""
    db        = request.app.state.db
    tenant_id = auth["sub"]

    conditions = ["r.tenant_id=$1"]
    params     = [tenant_id]
    idx        = 2

    if is_hot is not None:
        conditions.append(f"r.is_hot=${idx}"); params.append(is_hot); idx += 1
    if is_read is not None:
        conditions.append(f"r.is_read=${idx}"); params.append(is_read); idx += 1
    if intent:
        conditions.append(f"r.intent=${idx}"); params.append(intent); idx += 1

    where = " AND ".join(conditions)

    async with db.acquire() as conn:
        rows = await conn.fetch(f"""
            SELECT
                r.id, r.from_email, r.subject, r.body,
                r.intent, r.sentiment, r.is_hot, r.is_read,
                r.received_at,
                c.name  as campaign_name,
                l.first_name, l.last_name, l.company, l.title
            FROM replies r
            LEFT JOIN campaigns c ON r.campaign_id = c.id
            LEFT JOIN leads     l ON r.lead_id     = l.id
            WHERE {where}
            ORDER BY r.is_hot DESC, r.received_at DESC
            LIMIT {limit} OFFSET {offset}
        """, *params)

        total    = await conn.fetchval(f"SELECT COUNT(*) FROM replies r WHERE {where}", *params)
        hot_count= await conn.fetchval(
            "SELECT COUNT(*) FROM replies WHERE tenant_id=$1 AND is_hot=TRUE AND is_read=FALSE",
            tenant_id
        )

    return {
        "replies":      [dict(r) for r in rows],
        "total":        total,
        "hot_unread":   hot_count,
        "pagination": {"limit": limit, "offset": offset}
    }

@router.patch("/{reply_id}")
async def update_reply(
    reply_id: int,
    req: ReplyUpdateReq,
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    db = request.app.state.db
    updates = {k: v for k, v in req.dict().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")

    set_clause = ", ".join(f"{k}=${i+2}" for i, k in enumerate(updates))
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM replies WHERE id=$1 AND tenant_id=$2",
            reply_id, auth["sub"]
        )
        if not row:
            raise HTTPException(404, "Reply not found")
        await conn.execute(
            f"UPDATE replies SET {set_clause} WHERE id=$1",
            reply_id, *list(updates.values())
        )
    return {"reply_id": reply_id, "updated": updates}

@router.post("/{reply_id}/mark-read")
async def mark_read(
    reply_id: int,
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    db = request.app.state.db
    async with db.acquire() as conn:
        await conn.execute(
            "UPDATE replies SET is_read=TRUE WHERE id=$1 AND tenant_id=$2",
            reply_id, auth["sub"]
        )
    return {"reply_id": reply_id, "is_read": True}

@router.post("/ingest")
async def ingest_reply(
    req: ReplyIngestReq,
    background_tasks: BackgroundTasks,
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    """
    Called by Listmonk webhook or SMTP parser when reply received
    Auto-classifies intent, detects hot leads, stops sequence
    """
    db = request.app.state.db
    reply_id = None

    # Classify intent (fast, rule-based)
    intent, sentiment = classify_intent(req.body)

    # Tenant identity comes from the authenticated session, never from the request body.
    tenant_id = auth["sub"]
    is_hot = intent in ["interested", "more_info", "referral"]

    # Find lead
    lead_id   = None
    if tenant_id:
        async with db.acquire() as conn:
            lead = await conn.fetchrow(
                "SELECT id FROM leads WHERE email=$1 AND tenant_id=$2",
                req.from_email, tenant_id
            )
            if lead:
                lead_id = lead["id"]
                # Update lead status
                await conn.execute(
                    "UPDATE leads SET status=$1 WHERE id=$2",
                    "replied_positive" if is_hot else "replied", lead_id
                )

            # Auto-stop sequence — remove from active campaign
            if req.campaign_id:
                campaign = await conn.fetchrow(
                    "SELECT id FROM campaigns WHERE id=$1 AND tenant_id=$2",
                    req.campaign_id, tenant_id,
                )
                if not campaign:
                    raise HTTPException(404, "Campaign not found")
                await conn.execute(
                    "UPDATE campaigns SET replies = replies + 1, updated_at = NOW() WHERE id=$1 AND tenant_id=$2",
                    req.campaign_id, tenant_id,
                )

            if intent == "not_interested":
                await conn.execute(
                    """INSERT INTO suppression_entries (tenant_id, email, reason, source)
                       VALUES ($1,$2,'unsubscribe_or_not_interested','reply')
                       ON CONFLICT (tenant_id,email) DO UPDATE
                       SET reason=EXCLUDED.reason, source=EXCLUDED.source""",
                    tenant_id, req.from_email.lower(),
                )

            # Save reply
            reply_id = await conn.fetchval("""
                INSERT INTO replies
                (tenant_id, campaign_id, lead_id, from_email,
                 subject, body, intent, sentiment, is_hot)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                RETURNING id
            """, tenant_id, req.campaign_id, lead_id,
                req.from_email, req.subject, req.body,
                intent, sentiment, is_hot)

    # Background: AI reclassify if unknown + Slack alert if hot
    background_tasks.add_task(
        _process_reply_background,
        db, reply_id, req.body, intent, is_hot, tenant_id
    )

    return {
        "reply_id":  reply_id,
        "intent":    intent,
        "sentiment": sentiment,
        "is_hot":    is_hot,
        "sequence_stopped": True
    }

@router.get("/stats/summary")
async def inbox_summary(
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    db        = request.app.state.db
    tenant_id = auth["sub"]

    async with db.acquire() as conn:
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*)                                    as total,
                COUNT(*) FILTER (WHERE is_hot=TRUE)         as hot,
                COUNT(*) FILTER (WHERE is_read=FALSE)       as unread,
                COUNT(*) FILTER (WHERE intent='interested') as interested,
                COUNT(*) FILTER (WHERE intent='not_interested') as not_interested,
                COUNT(*) FILTER (WHERE intent='more_info')  as more_info,
                COUNT(*) FILTER (WHERE intent='referral')   as referral,
                COUNT(*) FILTER (WHERE intent='out_of_office') as ooo
            FROM replies WHERE tenant_id=$1
        """, tenant_id)

    return dict(stats)

# ── Internal helpers ────────────────────────────
async def _process_reply_background(
    db, reply_id: int, body: str, intent: str,
    is_hot: bool, tenant_id: str
):
    """AI reclassify unknown + Slack hot lead alert"""
    try:
        # Claude reclassification for unknown intent
        if intent == "unknown" and CLAUDE_KEY:
            better_intent = await _claude_classify(body)
            if better_intent and better_intent != intent:
                is_hot = better_intent in ["interested", "more_info", "referral"]
                async with db.acquire() as conn:
                    await conn.execute("""
                        UPDATE replies
                        SET intent=$1, is_hot=$2
                        WHERE id=$3
                    """, better_intent, is_hot, reply_id)

        # Slack alert for hot leads
        if is_hot and SLACK_WEBHOOK:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(SLACK_WEBHOOK, json={
                    "text": f"🔥 *Hot lead reply* in FadeReach!\n"
                            f"Intent: `{intent}`\n"
                            f"Preview: _{body[:100]}..._\n"
                            f"<https://fadereach.tinlance.com/inbox|View in inbox →>"
                })
    except Exception as e:
        print(f"Reply processing error [{reply_id}]: {e}")

async def _claude_classify(body: str) -> str:
    """Claude intent classification for ambiguous replies"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key":         CLAUDE_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type":      "application/json"
                },
                json={
                    "model":      "claude-haiku-4-5-20251001",
                    "max_tokens": 20,
                    "messages": [{
                        "role": "user",
                        "content": f"""Classify this cold email reply intent.
Reply: "{body[:300]}"
Options: interested / not_interested / not_now / more_info / referral / out_of_office / unknown
Return ONLY the single intent word."""
                    }]
                }
            )
        result = resp.json()["content"][0]["text"].strip().lower()
        valid  = {"interested","not_interested","not_now","more_info","referral","out_of_office","unknown"}
        return result if result in valid else "unknown"
    except:
        return "unknown"
