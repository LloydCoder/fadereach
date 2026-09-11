"""FadeReach — Analytics Router
Overview · Campaign performance · Domain health · Reply trends
"""
from fastapi import APIRouter, Request, Depends
from .deps import get_current_tenant
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/overview")
async def analytics_overview(
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    """Main dashboard stats — the numbers that matter"""
    db        = request.app.state.db
    tenant_id = auth["sub"]

    async with db.acquire() as conn:
        # All-time totals
        totals = await conn.fetchrow("""
            SELECT
                COALESCE(SUM(emails_sent), 0)    as total_sent,
                COALESCE(SUM(opens), 0)          as total_opens,
                COALESCE(SUM(replies), 0)        as total_replies,
                COALESCE(SUM(bounces), 0)        as total_bounces,
                COALESCE(SUM(unsubscribes), 0)   as total_unsubs,
                COUNT(*)                          as total_campaigns,
                COUNT(*) FILTER (WHERE status='active') as active_campaigns
            FROM campaigns WHERE tenant_id=$1
        """, tenant_id)

        # This month
        this_month = await conn.fetchrow("""
            SELECT
                COALESCE(SUM(emails_sent), 0)  as sent_mo,
                COALESCE(SUM(replies), 0)      as replies_mo,
                COALESCE(SUM(bounces), 0)      as bounces_mo
            FROM campaigns
            WHERE tenant_id=$1
            AND created_at >= date_trunc('month', NOW())
        """, tenant_id)

        # This week
        this_week = await conn.fetchrow("""
            SELECT
                COALESCE(SUM(emails_sent), 0) as sent_wk,
                COALESCE(SUM(replies), 0)     as replies_wk
            FROM campaigns
            WHERE tenant_id=$1
            AND created_at >= NOW() - INTERVAL '7 days'
        """, tenant_id)

        # Reply breakdown by intent
        intent_breakdown = await conn.fetch("""
            SELECT intent, COUNT(*) as count
            FROM replies WHERE tenant_id=$1
            GROUP BY intent ORDER BY count DESC
        """, tenant_id)

        # Hot leads count
        hot_leads = await conn.fetchval(
            "SELECT COUNT(*) FROM replies WHERE tenant_id=$1 AND is_hot=TRUE",
            tenant_id
        )

        # Domain health
        domains = await conn.fetch("""
            SELECT domain, health_score, inbox_prob, warmup_day,
                   spf_valid, dkim_valid, dmarc_valid, bounce_rate
            FROM domains WHERE tenant_id=$1
        """, tenant_id)

        # Lead counts
        lead_stats = await conn.fetchrow("""
            SELECT
                COUNT(*)                                              as total,
                COUNT(*) FILTER (WHERE status='uncontacted')         as uncontacted,
                COUNT(*) FILTER (WHERE status='replied_positive')    as replied_positive,
                COUNT(*) FILTER (WHERE verify_status='valid')        as verified
            FROM leads WHERE tenant_id=$1
        """, tenant_id)

    t = dict(totals)
    total_sent = int(t["total_sent"])

    def rate(num, denom):
        return round(int(num) / denom * 100, 1) if denom > 0 else 0

    return {
        "totals": {
            "emails_sent":      total_sent,
            "opens":            int(t["total_opens"]),
            "replies":          int(t["total_replies"]),
            "bounces":          int(t["total_bounces"]),
            "campaigns":        int(t["total_campaigns"]),
            "active_campaigns": int(t["active_campaigns"]),
            "hot_leads":        int(hot_leads),
        },
        "rates": {
            "open_rate":    rate(t["total_opens"],   total_sent),
            "reply_rate":   rate(t["total_replies"], total_sent),
            "bounce_rate":  rate(t["total_bounces"], total_sent),
            "unsub_rate":   rate(t["total_unsubs"],  total_sent),
        },
        "benchmarks": {
            "open_rate":   {"yours": rate(t["total_opens"], total_sent),   "industry": 21.3},
            "reply_rate":  {"yours": rate(t["total_replies"], total_sent), "industry": 3.4},
            "bounce_rate": {"yours": rate(t["total_bounces"], total_sent), "limit": 2.0},
        },
        "this_month": {
            "sent":    int(this_month["sent_mo"]),
            "replies": int(this_month["replies_mo"]),
            "bounces": int(this_month["bounces_mo"]),
        },
        "this_week": {
            "sent":    int(this_week["sent_wk"]),
            "replies": int(this_week["replies_wk"]),
        },
        "intent_breakdown": [dict(r) for r in intent_breakdown],
        "domains":          [dict(d) for d in domains],
        "leads": dict(lead_stats),
    }

@router.get("/campaigns/{campaign_id}")
async def campaign_analytics(
    campaign_id: int,
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    """Per-campaign detailed analytics"""
    db = request.app.state.db
    async with db.acquire() as conn:
        campaign = await conn.fetchrow("""
            SELECT id, name, subject, status, product,
                   emails_sent, opens, clicks, replies,
                   bounces, unsubscribes, audit_score,
                   created_at, updated_at
            FROM campaigns
            WHERE id=$1 AND tenant_id=$2
        """, campaign_id, auth["sub"])

        if not campaign:
            from fastapi import HTTPException
            raise HTTPException(404, "Campaign not found")

        # Reply intent breakdown for this campaign
        intents = await conn.fetch("""
            SELECT intent, COUNT(*) as count
            FROM replies
            WHERE campaign_id=$1 AND tenant_id=$2
            GROUP BY intent
        """, campaign_id, auth["sub"])

        # Sequence step performance (if tracked)
        steps = await conn.fetch("""
            SELECT
                COALESCE(sequence_step, 1) as step,
                COUNT(*) as sends,
                COUNT(*) FILTER (WHERE intent IN ('interested','more_info','referral')) as positive_replies
            FROM replies
            WHERE campaign_id=$1 AND tenant_id=$2
            GROUP BY sequence_step
            ORDER BY step
        """, campaign_id, auth["sub"])

    c         = dict(campaign)
    sent      = int(c["emails_sent"])

    def pct(n): return round(int(n) / sent * 100, 1) if sent > 0 else 0

    return {
        "campaign":  c,
        "rates": {
            "open_rate":   pct(c["opens"]),
            "click_rate":  pct(c["clicks"]),
            "reply_rate":  pct(c["replies"]),
            "bounce_rate": pct(c["bounces"]),
            "unsub_rate":  pct(c["unsubscribes"]),
        },
        "intent_breakdown": [dict(r) for r in intents],
        "sequence_performance": [dict(s) for s in steps],
        "audit_score": c["audit_score"],
    }

@router.get("/warmup/progress")
async def warmup_progress(
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    """Warmup progress across all domains"""
    db = request.app.state.db
    async with db.acquire() as conn:
        domains = await conn.fetch("""
            SELECT domain, warmup_day, warmup_status,
                   daily_limit, sent_today, health_score,
                   bounce_rate, complaint_rate
            FROM domains
            WHERE tenant_id=$1
            ORDER BY added_at
        """, auth["sub"])

    schedule = [
        {"week": 1, "days": "0–7",   "limit": 5,   "label": "Building reputation"},
        {"week": 2, "days": "7–14",  "limit": 15,  "label": "Establishing trust"},
        {"week": 3, "days": "14–21", "limit": 30,  "label": "Scaling carefully"},
        {"week": 4, "days": "21–28", "limit": 60,  "label": "Approaching full volume"},
        {"week": 5, "days": "28–35", "limit": 100, "label": "Full send capacity"},
    ]

    return {
        "domains":  [dict(d) for d in domains],
        "schedule": schedule,
    }
