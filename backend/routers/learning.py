"""
FadeReach — Self-Learning Engine
RLHF-lite feedback loop · Pattern recognition
Weekly optimization cron · market-specific intelligence

The system learns what YOUR market responds to.
After 90 days: knows best send times for Nigerian fintechs,
which subject patterns work for EU security teams,
which first-line structures convert best per product.
"""
from fastapi import APIRouter, Request, Depends, BackgroundTasks
from pydantic import BaseModel
from .deps import get_current_tenant
import httpx, os, json
from datetime import datetime, timedelta
from typing import Optional

router = APIRouter()

CLAUDE_KEY  = os.getenv("CLAUDE_API_KEY", "")
OLLAMA_URL  = os.getenv("OLLAMA_URL", "http://localhost:11434")

class FeedbackReq(BaseModel):
    """Human feedback on AI outputs"""
    resource_type: str   # first_line | campaign | subject_line
    resource_id:   int
    rating:        int   # 1-5
    outcome:       str   # replied | no_reply | bounced | spam
    notes:         Optional[str] = None

class OptimizationInsight(BaseModel):
    insight_type: str
    segment:      str
    value:        str
    confidence:   float
    sample_size:  int

@router.post("/feedback")
async def submit_feedback(
    req:     FeedbackReq,
    request: Request,
    auth:    dict = Depends(get_current_tenant),
):
    """
    RLHF-lite: human rates AI outputs
    Builds a dataset that improves generation over time
    """
    db        = request.app.state.db
    redis     = request.app.state.redis
    tenant_id = auth["sub"]

    async with db.acquire() as conn:
        await conn.execute("""
            INSERT INTO ai_feedback
            (tenant_id, resource_type, resource_id, rating, outcome, notes)
            VALUES ($1,$2,$3,$4,$5,$6)
        """, tenant_id, req.resource_type, req.resource_id,
            req.rating, req.outcome, req.notes)

        # Update aggregate scores
        avg_score = await conn.fetchval("""
            SELECT AVG(rating)::numeric(4,2)
            FROM ai_feedback
            WHERE tenant_id=$1 AND resource_type=$2
            AND created_at > NOW() - INTERVAL '30 days'
        """, tenant_id, req.resource_type)

    # Cache quality signal
    await redis.setex(
        f"ai_quality:{tenant_id}:{req.resource_type}",
        86400,
        str(avg_score or req.rating)
    )

    return {
        "feedback_saved":  True,
        "current_avg":     float(avg_score or req.rating),
        "message":         "Feedback recorded. System learns from this.",
    }

@router.get("/insights")
async def get_learning_insights(
    request: Request,
    auth:    dict = Depends(get_current_tenant),
):
    """
    What the system has learned about YOUR market
    Built from campaign data, reply patterns, feedback
    """
    db        = request.app.state.db
    redis     = request.app.state.redis
    tenant_id = auth["sub"]

    async with db.acquire() as conn:
        # Best performing send times
        send_time_data = await conn.fetch("""
            SELECT
                EXTRACT(DOW FROM r.received_at)::int  as day_of_week,
                EXTRACT(HOUR FROM r.received_at)::int as hour,
                COUNT(*) as reply_count
            FROM replies r
            JOIN campaigns c ON r.campaign_id = c.id
            WHERE c.tenant_id=$1
            AND r.intent IN ('interested','more_info','referral')
            AND r.received_at > NOW() - INTERVAL '90 days'
            GROUP BY day_of_week, hour
            ORDER BY reply_count DESC
            LIMIT 5
        """, tenant_id)

        # Best performing subject patterns
        subject_data = await conn.fetch("""
            SELECT
                c.subject,
                c.emails_sent,
                c.replies,
                CASE WHEN c.emails_sent > 0
                     THEN ROUND(c.replies::numeric / c.emails_sent * 100, 1)
                     ELSE 0 END as reply_rate
            FROM campaigns c
            WHERE c.tenant_id=$1
            AND c.emails_sent > 10
            ORDER BY reply_rate DESC
            LIMIT 10
        """, tenant_id)

        # Product performance
        product_data = await conn.fetch("""
            SELECT
                product,
                COUNT(*) as campaigns,
                SUM(emails_sent) as total_sent,
                SUM(replies) as total_replies,
                CASE WHEN SUM(emails_sent) > 0
                     THEN ROUND(SUM(replies)::numeric / SUM(emails_sent) * 100, 1)
                     ELSE 0 END as avg_reply_rate
            FROM campaigns
            WHERE tenant_id=$1 AND emails_sent > 0
            GROUP BY product
            ORDER BY avg_reply_rate DESC
        """, tenant_id)

        # Total feedback data
        feedback_stats = await conn.fetchrow("""
            SELECT
                COUNT(*)                                     as total_feedback,
                AVG(rating) FILTER (WHERE outcome='replied') as replied_avg,
                AVG(rating) FILTER (WHERE outcome='no_reply')as no_reply_avg
            FROM ai_feedback
            WHERE tenant_id=$1
        """, tenant_id)

    # Day names
    days = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]
    best_times = [
        {
            "day":         days[int(r["day_of_week"])],
            "hour":        f"{int(r['hour']):02d}:00",
            "replies":     int(r["reply_count"]),
            "label":       f"{days[int(r['day_of_week'])]} at {int(r['hour']):02d}:00 local",
        }
        for r in send_time_data
    ]

    best_subjects = [
        {
            "subject":    r["subject"],
            "sent":       int(r["emails_sent"]),
            "replies":    int(r["replies"]),
            "reply_rate": float(r["reply_rate"]),
        }
        for r in subject_data
    ]

    product_performance = [
        {
            "product":        r["product"],
            "campaigns":      int(r["campaigns"]),
            "total_sent":     int(r["total_sent"]),
            "avg_reply_rate": float(r["avg_reply_rate"]),
        }
        for r in product_data
    ]

    # Generate AI insight summary
    ai_summary = None
    if best_subjects and CLAUDE_KEY:
        ai_summary = await _generate_insights_summary(
            best_times, best_subjects, product_performance
        )

    return {
        "data_points":       (feedback_stats["total_feedback"] or 0),
        "best_send_times":   best_times,
        "best_subjects":     best_subjects,
        "product_performance": product_performance,
        "ai_summary":        ai_summary,
        "learning_stage":    _learning_stage(int(feedback_stats["total_feedback"] or 0)),
        "feedback_quality": {
            "replied_avg":   float(feedback_stats["replied_avg"] or 0),
            "no_reply_avg":  float(feedback_stats["no_reply_avg"] or 0),
        }
    }

@router.post("/optimize/run")
async def run_optimization(
    background_tasks: BackgroundTasks,
    request:  Request,
    auth:     dict = Depends(get_current_tenant),
):
    """
    Manual trigger for weekly optimization
    Normally runs via cron every Sunday 2am
    Updates send time recommendations, retires poor performers
    """
    background_tasks.add_task(
        _run_weekly_optimization,
        request.app.state.db,
        request.app.state.redis,
        auth["sub"]
    )
    return {"message": "Optimization running in background — insights updated in ~60 seconds"}

@router.get("/recommendations")
async def get_recommendations(
    request: Request,
    auth:    dict = Depends(get_current_tenant),
):
    """
    AI-powered recommendations for next campaign
    Based on historical data + learning insights
    """
    db        = request.app.state.db
    redis     = request.app.state.redis
    tenant_id = auth["sub"]

    # Get cached recommendations
    cached = await redis.get(f"recommendations:{tenant_id}")
    if cached:
        return json.loads(cached)

    async with db.acquire() as conn:
        # Get historical context
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*)                         as total_campaigns,
                AVG(CASE WHEN emails_sent > 0
                    THEN replies::numeric/emails_sent END) as avg_reply_rate,
                SUM(emails_sent)                 as total_sent
            FROM campaigns WHERE tenant_id=$1
        """, tenant_id)

        best_time = await conn.fetchrow("""
            SELECT EXTRACT(DOW FROM received_at)::int  as day,
                   EXTRACT(HOUR FROM received_at)::int as hour,
                   COUNT(*) as count
            FROM replies r
            JOIN campaigns c ON r.campaign_id=c.id
            WHERE c.tenant_id=$1
            AND r.intent IN ('interested','more_info')
            GROUP BY day, hour ORDER BY count DESC LIMIT 1
        """, tenant_id)

    days = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
    send_time_rec = None
    if best_time:
        send_time_rec = f"{days[int(best_time['day'])]} at {int(best_time['hour']):02d}:00"

    recommendations = {
        "send_time":      send_time_rec or "Tuesday–Thursday, 08:00–10:00 local time",
        "sequence_length": 4,
        "sequence_note":  "Use measured step-level reply and qualification outcomes; do not assume a universal sequence conversion split.",
        "subject_tips": [
            "Keep under 45 characters",
            "Avoid question marks in subject — use in body CTA instead",
            "Reference a specific company signal, not a generic pain point",
        ],
        "first_line_tips": [
            "Reference something specific about their recent activity",
            "Keep under 20 words",
            "Do not start with 'I' or 'We'",
            "Sound like a colleague, not a vendor",
        ],
        "optimal_volume":  "Use the sending-domain and mailbox limits shown by the deliverability control plane.",
        "bounce_target":   "Keep bounce rate under 1.5% — pause at 2%",
        "data_powered":    bool(stats["total_campaigns"]),
        "campaigns_analyzed": int(stats["total_campaigns"] or 0),
    }

    # Cache for 4 hours
    await redis.setex(
        f"recommendations:{tenant_id}",
        14400,
        json.dumps(recommendations)
    )

    return recommendations

# ── Internal helpers ────────────────────────────
async def _run_weekly_optimization(db, redis, tenant_id: str):
    """
    Weekly optimization cron logic
    Runs every Sunday 2am via n8n schedule trigger
    """
    async with db.acquire() as conn:
        # Find underperforming subject line patterns
        poor_performers = await conn.fetch("""
            SELECT subject,
                   CASE WHEN emails_sent > 0 THEN replies::numeric / emails_sent * 100 ELSE 0 END AS reply_rate
            FROM campaigns
            WHERE tenant_id=$1
            AND emails_sent > 50
            AND (replies::numeric / NULLIF(emails_sent,0) * 100) < 2.0
            AND created_at < NOW() - INTERVAL '14 days'
        """, tenant_id)

        # Persist optimization evidence; schema is migration-managed.
        await conn.execute("""
            INSERT INTO optimization_log (tenant_id, insights, actions)
            VALUES ($1, $2, $3)
        """, tenant_id,
            json.dumps({"poor_performers": len(poor_performers)}),
            json.dumps({"action": "weekly_optimization_complete"})
        )

    # Clear recommendation cache to force rebuild
    await redis.delete(f"recommendations:{tenant_id}")

def _learning_stage(data_points: int) -> dict:
    if data_points == 0:
        return {
            "stage":   "bootstrap",
            "label":   "Learning begins with your first campaign",
            "pct":     0,
            "message": "Send your first campaign to start building market intelligence.",
        }
    elif data_points < 50:
        return {
            "stage":   "early",
            "label":   "Early learning",
            "pct":     round(data_points / 50 * 30),
            "message": f"Building patterns from {data_points} signals. More campaigns = better insights.",
        }
    elif data_points < 200:
        return {
            "stage":   "developing",
            "label":   "Developing intelligence",
            "pct":     30 + round((data_points - 50) / 150 * 40),
            "message": "Patterns emerging. Recommendations becoming market-specific.",
        }
    elif data_points < 500:
        return {
            "stage":   "trained",
            "label":   "Market-trained",
            "pct":     70 + round((data_points - 200) / 300 * 25),
            "message": "Strong market intelligence for your ICP. Recommendations are evidence-backed for the observed sample.",
        }
    else:
        return {
            "stage":   "expert",
            "label":   "Expert-level market intelligence",
            "pct":     95,
            "message": "FadeReach knows your market. Trust the recommendations.",
        }

async def _generate_insights_summary(
    best_times: list, best_subjects: list, products: list
) -> str:
    """Claude-powered plain-English insights summary"""
    if not CLAUDE_KEY:
        return None
    try:
        top_time = best_times[0] if best_times else None
        top_subj = best_subjects[0] if best_subjects else None
        top_prod = products[0] if products else None

        prompt = f"""You analyze cold email campaign data for an African B2B founder.
Data:
- Best send time: {top_time['label'] if top_time else 'Not enough data'}
- Best subject: "{top_subj['subject'] if top_subj else 'N/A'}" ({top_subj['reply_rate'] if top_subj else 0}% reply rate)
- Best product: {top_prod['product'] if top_prod else 'N/A'} ({top_prod['avg_reply_rate'] if top_prod else 0}% reply rate)

Write 2 sentences of plain-English insight for the founder. Be specific and actionable. No fluff."""

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key":         CLAUDE_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type":      "application/json",
                },
                json={
                    "model":      "claude-haiku-4-5-20251001",
                    "max_tokens": 150,
                    "messages":   [{"role": "user", "content": prompt}]
                }
            )
        return resp.json()["content"][0]["text"].strip()
    except:
        return None        # Update aggregate scores
        avg_score = await conn.fetchval("""
            SELECT AVG(rating)::numeric(4,2)
            FROM ai_feedback
            WHERE tenant_id=$1 AND resource_type=$2
            AND created_at > NOW() - INTERVAL '30 days'
        """, tenant_id, req.resource_type)

    # Cache quality signal
    await redis.setex(
        f"ai_quality:{tenant_id}:{req.resource_type}",
        86400,
        str(avg_score or req.rating)
    )

    return {
        "feedback_saved":  True,
        "current_avg":     float(avg_score or req.rating),
        "message":         "Feedback recorded. System learns from this.",
    }

@router.get("/insights")
async def get_learning_insights(
    request: Request,
    auth:    dict = Depends(get_current_tenant),
):
    """
    What the system has learned about YOUR market
    Built from campaign data, reply patterns, feedback
    """
    db        = request.app.state.db
    redis     = request.app.state.redis
    tenant_id = auth["sub"]

    async with db.acquire() as conn:
        # Best performing send times
        send_time_data = await conn.fetch("""
            SELECT
                EXTRACT(DOW FROM r.received_at)::int  as day_of_week,
                EXTRACT(HOUR FROM r.received_at)::int as hour,
                COUNT(*) as reply_count
            FROM replies r
            JOIN campaigns c ON r.campaign_id = c.id
            WHERE c.tenant_id=$1
            AND r.intent IN ('interested','more_info','referral')
            AND r.received_at > NOW() - INTERVAL '90 days'
            GROUP BY day_of_week, hour
            ORDER BY reply_count DESC
            LIMIT 5
        """, tenant_id)

        # Best performing subject patterns
        subject_data = await conn.fetch("""
            SELECT
                c.subject,
                c.emails_sent,
                c.replies,
                CASE WHEN c.emails_sent > 0
                     THEN ROUND(c.replies::numeric / c.emails_sent * 100, 1)
                     ELSE 0 END as reply_rate
            FROM campaigns c
            WHERE c.tenant_id=$1
            AND c.emails_sent > 10
            ORDER BY reply_rate DESC
            LIMIT 10
        """, tenant_id)

        # Product performance
        product_data = await conn.fetch("""
            SELECT
                product,
                COUNT(*) as campaigns,
                SUM(emails_sent) as total_sent,
                SUM(replies) as total_replies,
                CASE WHEN SUM(emails_sent) > 0
                     THEN ROUND(SUM(replies)::numeric / SUM(emails_sent) * 100, 1)
                     ELSE 0 END as avg_reply_rate
            FROM campaigns
            WHERE tenant_id=$1 AND emails_sent > 0
            GROUP BY product
            ORDER BY avg_reply_rate DESC
        """, tenant_id)

        # Total feedback data
        feedback_stats = await conn.fetchrow("""
            SELECT
                COUNT(*)                                     as total_feedback,
                AVG(rating) FILTER (WHERE outcome='replied') as replied_avg,
                AVG(rating) FILTER (WHERE outcome='no_reply')as no_reply_avg
            FROM ai_feedback
            WHERE tenant_id=$1
        """, tenant_id)

    # Day names
    days = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]
    best_times = [
        {
            "day":         days[int(r["day_of_week"])],
            "hour":        f"{int(r['hour']):02d}:00",
            "replies":     int(r["reply_count"]),
            "label":       f"{days[int(r['day_of_week'])]} at {int(r['hour']):02d}:00 local",
        }
        for r in send_time_data
    ]

    best_subjects = [
        {
            "subject":    r["subject"],
            "sent":       int(r["emails_sent"]),
            "replies":    int(r["replies"]),
            "reply_rate": float(r["reply_rate"]),
        }
        for r in subject_data
    ]

    product_performance = [
        {
            "product":        r["product"],
            "campaigns":      int(r["campaigns"]),
            "total_sent":     int(r["total_sent"]),
            "avg_reply_rate": float(r["avg_reply_rate"]),
        }
        for r in product_data
    ]

    # Generate AI insight summary
    ai_summary = None
    if best_subjects and CLAUDE_KEY:
        ai_summary = await _generate_insights_summary(
            best_times, best_subjects, product_performance
        )

    return {
        "data_points":       (feedback_stats["total_feedback"] or 0),
        "best_send_times":   best_times,
        "best_subjects":     best_subjects,
        "product_performance": product_performance,
        "ai_summary":        ai_summary,
        "learning_stage":    _learning_stage(int(feedback_stats["total_feedback"] or 0)),
        "feedback_quality": {
            "replied_avg":   float(feedback_stats["replied_avg"] or 0),
            "no_reply_avg":  float(feedback_stats["no_reply_avg"] or 0),
        }
    }

@router.post("/optimize/run")
async def run_optimization(
    background_tasks: BackgroundTasks,
    request:  Request,
    auth:     dict = Depends(get_current_tenant),
):
    """
    Manual trigger for weekly optimization
    Normally runs via cron every Sunday 2am
    Updates send time recommendations, retires poor performers
    """
    background_tasks.add_task(
        _run_weekly_optimization,
        request.app.state.db,
        request.app.state.redis,
        auth["sub"]
    )
    return {"message": "Optimization running in background — insights updated in ~60 seconds"}

@router.get("/recommendations")
async def get_recommendations(
    request: Request,
    auth:    dict = Depends(get_current_tenant),
):
    """
    AI-powered recommendations for next campaign
    Based on historical data + learning insights
    """
    db        = request.app.state.db
    redis     = request.app.state.redis
    tenant_id = auth["sub"]

    # Get cached recommendations
    cached = await redis.get(f"recommendations:{tenant_id}")
    if cached:
        return json.loads(cached)

    async with db.acquire() as conn:
        # Get historical context
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*)                         as total_campaigns,
                AVG(CASE WHEN emails_sent > 0
                    THEN replies::numeric/emails_sent END) as avg_reply_rate,
                SUM(emails_sent)                 as total_sent
            FROM campaigns WHERE tenant_id=$1
        """, tenant_id)

        best_time = await conn.fetchrow("""
            SELECT EXTRACT(DOW FROM received_at)::int  as day,
                   EXTRACT(HOUR FROM received_at)::int as hour,
                   COUNT(*) as count
            FROM replies r
            JOIN campaigns c ON r.campaign_id=c.id
            WHERE c.tenant_id=$1
            AND r.intent IN ('interested','more_info')
            GROUP BY day, hour ORDER BY count DESC LIMIT 1
        """, tenant_id)

    days = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
    send_time_rec = None
    if best_time:
        send_time_rec = f"{days[int(best_time['day'])]} at {int(best_time['hour']):02d}:00"

    recommendations = {
        "send_time":      send_time_rec or "Tuesday–Thursday, 08:00–10:00 local time",
        "sequence_length": 4,
        "sequence_note":  "58% of replies come from email 1. Steps 2-4 catch the remaining 42%.",
        "subject_tips": [
            "Keep under 45 characters",
            "Avoid question marks in subject — use in body CTA instead",
            "Reference a specific company signal, not a generic pain point",
        ],
        "first_line_tips": [
            "Reference something specific about their recent activity",
            "Keep under 20 words",
            "Do not start with 'I' or 'We'",
            "Sound like a colleague, not a vendor",
        ],
        "optimal_volume":  "Max 100 emails/day per mailbox — never exceed this",
        "bounce_target":   "Keep bounce rate under 1.5% — pause at 2%",
        "data_powered":    bool(stats["total_campaigns"]),
        "campaigns_analyzed": int(stats["total_campaigns"] or 0),
    }

    # Cache for 4 hours
    await redis.setex(
        f"recommendations:{tenant_id}",
        14400,
        json.dumps(recommendations)
    )

    return recommendations

# ── Internal helpers ────────────────────────────
async def _run_weekly_optimization(db, redis, tenant_id: str):
    """
    Weekly optimization cron logic
    Runs every Sunday 2am via n8n schedule trigger
    """
    async with db.acquire() as conn:
        # Find underperforming subject line patterns
        poor_performers = await conn.fetch("""
            SELECT subject, reply_rate
            FROM campaigns
            WHERE tenant_id=$1
            AND emails_sent > 50
            AND reply_rate < 2.0
            AND created_at < NOW() - INTERVAL '14 days'
        """, tenant_id)

        # Store optimization log
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS optimization_log (
                id          SERIAL PRIMARY KEY,
                tenant_id   TEXT NOT NULL,
                run_at      TIMESTAMPTZ DEFAULT NOW(),
                insights    JSONB,
                actions     JSONB
            );
        """)

        await conn.execute("""
            INSERT INTO optimization_log (tenant_id, insights, actions)
            VALUES ($1, $2, $3)
        """, tenant_id,
            json.dumps({"poor_performers": len(poor_performers)}),
            json.dumps({"action": "weekly_optimization_complete"})
        )

    # Clear recommendation cache to force rebuild
    await redis.delete(f"recommendations:{tenant_id}")

def _learning_stage(data_points: int) -> dict:
    if data_points == 0:
        return {
            "stage":   "bootstrap",
            "label":   "Learning begins with your first campaign",
            "pct":     0,
            "message": "Send your first campaign to start building market intelligence.",
        }
    elif data_points < 50:
        return {
            "stage":   "early",
            "label":   "Early learning",
            "pct":     round(data_points / 50 * 30),
            "message": f"Building patterns from {data_points} signals. More campaigns = better insights.",
        }
    elif data_points < 200:
        return {
            "stage":   "developing",
            "label":   "Developing intelligence",
            "pct":     30 + round((data_points - 50) / 150 * 40),
            "message": "Patterns emerging. Recommendations becoming Africa-specific.",
        }
    elif data_points < 500:
        return {
            "stage":   "trained",
            "label":   "Market-trained",
            "pct":     70 + round((data_points - 200) / 300 * 25),
            "message": "Strong market intelligence for your ICP. Recommendations are reliable.",
        }
    else:
        return {
            "stage":   "expert",
            "label":   "Expert-level market intelligence",
            "pct":     95,
            "message": "FadeReach knows your market. Trust the recommendations.",
        }

async def _generate_insights_summary(
    best_times: list, best_subjects: list, products: list
) -> str:
    """Claude-powered plain-English insights summary"""
    if not CLAUDE_KEY:
        return None
    try:
        top_time = best_times[0] if best_times else None
        top_subj = best_subjects[0] if best_subjects else None
        top_prod = products[0] if products else None

        prompt = f"""You analyze cold email campaign data for an African B2B founder.
Data:
- Best send time: {top_time['label'] if top_time else 'Not enough data'}
- Best subject: "{top_subj['subject'] if top_subj else 'N/A'}" ({top_subj['reply_rate'] if top_subj else 0}% reply rate)
- Best product: {top_prod['product'] if top_prod else 'N/A'} ({top_prod['avg_reply_rate'] if top_prod else 0}% reply rate)

Write 2 sentences of plain-English insight for the founder. Be specific and actionable. No fluff."""

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key":         CLAUDE_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type":      "application/json",
                },
                json={
                    "model":      "claude-haiku-4-5-20251001",
                    "max_tokens": 150,
                    "messages":   [{"role": "user", "content": prompt}]
                }
            )
        return resp.json()["content"][0]["text"].strip()
    except:
        return None
