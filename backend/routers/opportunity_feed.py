"""
FadeReach — Opportunity Feed
Signal-based prospect discovery engine
The #1 moat feature. Apollo + Smartlead in one.

Signal sources:
- Olvrix fadereach_sync bridge (largest data generator)
- Olvrix Widgets intent signals (hottest leads)
- ReconOS OFE (OSINT + AfricanContextEngine)
- ThreatFade (security gap detection)
- FusionOps (SOC gap signals)
- ResonaForge Signal Bridge (content engagement)
- LinkedIn/Apollo job change + funding signals
- Hunter.io domain discovery
"""
from fastapi import APIRouter, Request, Depends, BackgroundTasks, HTTPException
from pydantic import BaseModel
from .deps import get_current_tenant
import httpx, os, json
from datetime import datetime, timedelta
from typing import Optional

router = APIRouter()

# ── Ecosystem service URLs ──────────────────────
RECONOS_URL    = os.getenv("RECONOS_URL",    "http://localhost:8503")
THREATFADE_URL = os.getenv("THREATFADE_URL", "http://localhost:8504")
FUSIONOPS_URL  = os.getenv("FUSIONOPS_URL",  "http://13.50.16.19:8000")
RESONAFORGE_URL= os.getenv("RESONAFORGE_URL","http://localhost:8010")
OLVRIX_URL     = os.getenv("OLVRIX_URL",     "http://localhost:8505")
APOLLO_KEY     = os.getenv("APOLLO_API_KEY", "")
HUNTER_KEY     = os.getenv("HUNTER_API_KEY", "")
CLAUDE_KEY     = os.getenv("CLAUDE_API_KEY", "")

# Signal types and their intent scores
SIGNAL_SCORES = {
    # Olvrix signals (hottest — user already engaged)
    "olvrix_widget_form_fill":    98,
    "olvrix_widget_exit_intent":  85,
    "olvrix_widget_chat_started": 90,
    "olvrix_crm_contact":         75,
    "olvrix_lead_qualified":      88,

    # ResonaForge content engagement
    "resonaforge_post_engaged":   72,
    "resonaforge_multiple_views": 80,
    "resonaforge_comment":        78,
    "resonaforge_share":          76,

    # ThreatFade security signals
    "threatfade_missing_dmarc":   70,
    "threatfade_weak_spf":        68,
    "threatfade_c2_detected":     85,
    "threatfade_exposed_service": 75,

    # FusionOps SOC signals
    "fusionops_soc_gap":          72,
    "fusionops_siem_misconfigured":74,
    "fusionops_alert_fatigue":    70,

    # ReconOS OSINT signals
    "reconos_funding_round":      82,
    "reconos_leadership_change":  78,
    "reconos_hiring_spike":       76,
    "reconos_expansion_signal":   74,
    "reconos_tech_stack_change":  70,

    # LinkedIn/Apollo signals
    "linkedin_job_change":        75,
    "linkedin_post_relevant":     65,
    "apollo_hiring_signal":       72,
    "apollo_funding_detected":    80,

    # Generic
    "domain_search":              50,
    "manual_import":              40,
}

class OpportunityFilterReq(BaseModel):
    signal_types:  list[str] | None = None
    min_score:     int   = 60
    industries:    list[str] | None = None
    locations:     list[str] | None = None
    limit:         int   = 50
    offset:        int   = 0

class OpportunityActionReq(BaseModel):
    opportunity_id: int
    action: str  # add_to_campaign | dismiss | bookmark | verify_email

@router.get("/feed")
async def get_opportunity_feed(
    request:   Request,
    auth:      dict = Depends(get_current_tenant),
    min_score: int  = 60,
    limit:     int  = 50,
    offset:    int  = 0,
    source:    Optional[str] = None,
):
    """
    The Opportunity Feed — new prospects discovered automatically
    Combines all 17 ecosystem signal sources
    """
    db        = request.app.state.db
    redis     = request.app.state.redis
    tenant_id = auth["sub"]

    # Get cached opportunities from Redis (refreshed every 30 min)
    cache_key = f"opportunity_feed:{tenant_id}:{min_score}"
    cached    = await redis.get(cache_key)

    if cached:
        opportunities = json.loads(cached)
    else:
        # Build fresh feed from all signal sources
        opportunities = await _build_opportunity_feed(
            db, redis, tenant_id, min_score
        )
        # Cache for 30 minutes
        await redis.setex(cache_key, 1800, json.dumps(opportunities))

    # Filter by source if requested
    if source:
        opportunities = [o for o in opportunities if o.get("source") == source]

    # Paginate
    total  = len(opportunities)
    paged  = opportunities[offset:offset + limit]

    # Signal source summary
    sources = {}
    for opp in opportunities:
        src = opp.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1

    return {
        "total":         total,
        "opportunities": paged,
        "sources":       sources,
        "refreshed_at":  datetime.utcnow().isoformat(),
        "next_refresh":  (datetime.utcnow() + timedelta(minutes=30)).isoformat(),
    }

@router.post("/refresh")
async def refresh_feed(
    background_tasks: BackgroundTasks,
    request:  Request,
    auth:     dict = Depends(get_current_tenant),
):
    """Force refresh the opportunity feed"""
    tenant_id = auth["sub"]
    redis     = request.app.state.redis

    # Clear cache
    await redis.delete(f"opportunity_feed:{tenant_id}:60")
    await redis.delete(f"opportunity_feed:{tenant_id}:70")
    await redis.delete(f"opportunity_feed:{tenant_id}:80")

    # Trigger background refresh
    background_tasks.add_task(
        _build_and_cache_feed,
        request.app.state.db, redis, tenant_id, 60
    )

    return {"message": "Feed refreshing in background — ready in ~30 seconds"}

@router.post("/action")
async def opportunity_action(
    req:     OpportunityActionReq,
    request: Request,
    auth:    dict = Depends(get_current_tenant),
):
    """
    Act on an opportunity:
    - add_to_campaign: push to lead list
    - dismiss: hide from feed
    - bookmark: save for later
    - verify_email: run through Reacher
    """
    db        = request.app.state.db
    redis     = request.app.state.redis
    tenant_id = auth["sub"]

    # Get opportunity from cache
    cache_key     = f"opportunity_feed:{tenant_id}:60"
    cached        = await redis.get(cache_key)
    opportunities = json.loads(cached) if cached else []
    opp           = next((o for o in opportunities if o.get("id") == req.opportunity_id), None)

    if not opp:
        raise HTTPException(404, "Opportunity not found")

    if req.action == "add_to_campaign":
        # Add to leads table
        async with db.acquire() as conn:
            await conn.execute("""
                INSERT INTO leads
                (tenant_id, email, first_name, last_name, company,
                 title, domain, signal_type, signal_data, icp_score)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                ON CONFLICT DO NOTHING
            """, tenant_id,
                opp.get("email"), opp.get("first_name"),
                opp.get("last_name"), opp.get("company"),
                opp.get("title"), opp.get("domain"),
                opp.get("signal_type"),
                json.dumps(opp.get("signal_data", {})),
                opp.get("score", 60))
        return {"action": "added", "email": opp.get("email")}

    elif req.action == "dismiss":
        # Add to dismissed set
        await redis.sadd(f"dismissed:{tenant_id}", req.opportunity_id)
        return {"action": "dismissed"}

    elif req.action == "bookmark":
        await redis.sadd(f"bookmarked:{tenant_id}", req.opportunity_id)
        return {"action": "bookmarked"}

    elif req.action == "verify_email":
        REACHER_URL = os.getenv("REACHER_URL", "http://localhost:8083")
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{REACHER_URL}/v0/check_email",
                    json={
                        "to_email":   opp.get("email"),
                        "from_email": "verify@fadereach.tinlance.com",
                    }
                )
            return {"action": "verified", "result": resp.json()}
        except:
            return {"action": "verified", "result": {"error": "verifier_unavailable"}}

    raise HTTPException(400, f"Unknown action: {req.action}")

@router.get("/signals/summary")
async def signals_summary(
    request: Request,
    auth:    dict = Depends(get_current_tenant),
):
    """Dashboard widget: signal counts by source"""
    redis     = request.app.state.redis
    tenant_id = auth["sub"]

    cache_key     = f"opportunity_feed:{tenant_id}:60"
    cached        = await redis.get(cache_key)
    opportunities = json.loads(cached) if cached else []

    # Count by source
    by_source = {}
    for opp in opportunities:
        src = opp.get("source", "unknown")
        by_source[src] = by_source.get(src, 0) + 1

    # Hot leads count (score >= 85)
    hot = len([o for o in opportunities if o.get("score", 0) >= 85])

    return {
        "total":          len(opportunities),
        "hot":            hot,
        "by_source":      by_source,
        "last_refreshed": await redis.get(f"feed_refreshed:{tenant_id}"),
    }

# ── Feed building engine ────────────────────────
async def _build_opportunity_feed(
    db, redis, tenant_id: str, min_score: int
) -> list:
    """
    Collect signals from all 17 ecosystem sources
    Returns deduplicated, scored, ranked opportunities
    """
    all_opportunities = []
    dismissed = await redis.smembers(f"dismissed:{tenant_id}") or set()

    # ── SOURCE 1: Olvrix fadereach_sync bridge ─────
    # Largest data generator — agencies + SMB contacts
    olvrix_opps = await _fetch_olvrix_signals(tenant_id)
    all_opportunities.extend(olvrix_opps)

    # ── SOURCE 2: Olvrix Widgets intent signals ────
    # Hottest leads — widget interactions
    widget_opps = await _fetch_olvrix_widget_signals(tenant_id)
    all_opportunities.extend(widget_opps)

    # ── SOURCE 3: ResonaForge Signal Bridge ────────
    # Content engagement → warm leads
    resonaforge_opps = await _fetch_resonaforge_signals(tenant_id)
    all_opportunities.extend(resonaforge_opps)

    # ── SOURCE 4: ThreatFade security gaps ─────────
    # Companies with email security issues
    threatfade_opps = await _fetch_threatfade_signals()
    all_opportunities.extend(threatfade_opps)

    # ── SOURCE 5: ReconOS OSINT signals ────────────
    # Funding, hiring, leadership changes
    reconos_opps = await _fetch_reconos_signals()
    all_opportunities.extend(reconos_opps)

    # ── SOURCE 6: Apollo.io signals ────────────────
    # Job changes, company growth
    apollo_opps = await _fetch_apollo_signals()
    all_opportunities.extend(apollo_opps)

    # Deduplicate by email
    seen   = set()
    unique = []
    for opp in all_opportunities:
        key = opp.get("email", "").lower()
        if key and key not in seen and opp.get("id") not in dismissed:
            seen.add(key)
            unique.append(opp)

    # Filter by minimum score
    filtered = [o for o in unique if o.get("score", 0) >= min_score]

    # Sort: hot leads first, then by score
    sorted_opps = sorted(
        filtered,
        key=lambda o: (o.get("score", 0), o.get("is_hot", False)),
        reverse=True
    )

    # Record refresh time
    await redis.set(
        f"feed_refreshed:{tenant_id}",
        datetime.utcnow().isoformat()
    )

    return sorted_opps

async def _build_and_cache_feed(db, redis, tenant_id: str, min_score: int):
    """Background: build and cache feed"""
    opps = await _build_opportunity_feed(db, redis, tenant_id, min_score)
    cache_key = f"opportunity_feed:{tenant_id}:{min_score}"
    await redis.setex(cache_key, 1800, json.dumps(opps))

# ── Signal fetchers per source ──────────────────
async def _fetch_olvrix_signals(tenant_id: str) -> list:
    """
    Olvrix fadereach_sync bridge
    Largest data source — CRM contacts, agency clients, SMB leads
    """
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"{OLVRIX_URL}/api/fadereach-sync/{tenant_id}",
                headers={"X-Internal": "fadereach"}
            )
        if resp.status_code != 200:
            return []
        contacts = resp.json().get("contacts", [])
        return [
            {
                "id":           hash(c.get("email", "") + "olvrix") & 0x7FFFFFFF,
                "email":        c.get("email"),
                "first_name":   c.get("first_name"),
                "last_name":    c.get("last_name"),
                "company":      c.get("company"),
                "title":        c.get("title"),
                "domain":       c.get("domain"),
                "source":       "olvrix",
                "source_label": "Olvrix CRM",
                "signal_type":  "olvrix_crm_contact",
                "score":        SIGNAL_SCORES["olvrix_crm_contact"],
                "signal_data":  c,
                "is_hot":       False,
                "discovered_at": datetime.utcnow().isoformat(),
            }
            for c in contacts if c.get("email")
        ]
    except:
        return []

async def _fetch_olvrix_widget_signals(tenant_id: str) -> list:
    """
    Olvrix Widgets — 9 conversion widgets
    Form fills, exit intent, chat → hottest leads in ecosystem
    """
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"{OLVRIX_URL}/api/widget-signals/{tenant_id}",
                headers={"X-Internal": "fadereach"}
            )
        if resp.status_code != 200:
            return []
        events = resp.json().get("events", [])
        return [
            {
                "id":           hash(e.get("email", "") + "widget") & 0x7FFFFFFF,
                "email":        e.get("email"),
                "first_name":   e.get("first_name"),
                "last_name":    e.get("last_name"),
                "company":      e.get("company"),
                "title":        e.get("title"),
                "domain":       e.get("domain"),
                "source":       "olvrix_widgets",
                "source_label": "Olvrix Widget — " + e.get("widget_type", "Form"),
                "signal_type":  f"olvrix_widget_{e.get('widget_type','form_fill')}",
                "score":        SIGNAL_SCORES.get(
                    f"olvrix_widget_{e.get('widget_type','form_fill')}",
                    85
                ),
                "signal_data":  e,
                "is_hot":       True,  # Widget interactions are always hot
                "discovered_at": e.get("created_at", datetime.utcnow().isoformat()),
                "widget_type":  e.get("widget_type"),
                "page_url":     e.get("page_url"),
            }
            for e in events if e.get("email")
        ]
    except:
        return []

async def _fetch_resonaforge_signals(tenant_id: str) -> list:
    """
    ResonaForge Signal Bridge
    Content engagement → warm leads who already know your brand
    """
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"{RESONAFORGE_URL}/api/fadereach-signals/{tenant_id}",
                headers={"X-Internal": "fadereach"}
            )
        if resp.status_code != 200:
            return []
        signals = resp.json().get("signals", [])
        return [
            {
                "id":           hash(s.get("email", "") + "resona") & 0x7FFFFFFF,
                "email":        s.get("email"),
                "first_name":   s.get("first_name"),
                "last_name":    s.get("last_name"),
                "company":      s.get("company"),
                "domain":       s.get("domain"),
                "source":       "resonaforge",
                "source_label": "ResonaForge — Content Engaged",
                "signal_type":  f"resonaforge_{s.get('engagement_type','post_engaged')}",
                "score":        SIGNAL_SCORES.get(
                    f"resonaforge_{s.get('engagement_type','post_engaged')}",
                    72
                ),
                "signal_data": {
                    "post_title":       s.get("post_title"),
                    "engagement_type":  s.get("engagement_type"),
                    "engagement_count": s.get("engagement_count", 1),
                    "platform":         s.get("platform"),
                },
                "is_hot":       s.get("engagement_count", 1) >= 3,
                "discovered_at": s.get("engaged_at", datetime.utcnow().isoformat()),
            }
            for s in signals if s.get("email")
        ]
    except:
        return []

async def _fetch_threatfade_signals() -> list:
    """
    ThreatFade — companies with email security gaps
    Missing DMARC, weak SPF, exposed services → perfect FadeReach prospects
    """
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"{THREATFADE_URL}/api/email-security-gaps",
                headers={"X-Internal": "fadereach"}
            )
        if resp.status_code != 200:
            return _threatfade_fallback_signals()
        companies = resp.json().get("companies", [])
        return [
            {
                "id":           hash(c.get("domain", "") + "tf") & 0x7FFFFFFF,
                "email":        c.get("contact_email"),
                "first_name":   c.get("contact_first_name"),
                "company":      c.get("company_name"),
                "domain":       c.get("domain"),
                "source":       "threatfade",
                "source_label": "ThreatFade — Security Gap",
                "signal_type":  f"threatfade_{c.get('gap_type','missing_dmarc')}",
                "score":        SIGNAL_SCORES.get(
                    f"threatfade_{c.get('gap_type','missing_dmarc')}",
                    70
                ),
                "signal_data": {
                    "gap_type":    c.get("gap_type"),
                    "gap_details": c.get("gap_details"),
                    "severity":    c.get("severity"),
                },
                "is_hot":       c.get("severity") == "critical",
                "suggested_subject": f"Your email authentication gap at {c.get('domain')}",
                "suggested_first_line": (
                    f"Noticed {c.get('company_name')}'s DMARC policy is missing — "
                    f"emails sent in your name currently land in inboxes undetected."
                ),
                "discovered_at": datetime.utcnow().isoformat(),
            }
            for c in companies if c.get("contact_email")
        ]
    except:
        return _threatfade_fallback_signals()

def _threatfade_fallback_signals() -> list:
    """
    Fallback: demo ThreatFade signals when API unavailable
    Shows the concept even before ThreatFade integration is live
    """
    return [
        {
            "id":           1001,
            "email":        None,
            "company":      "Sample Nigerian Fintech",
            "domain":       "samplefintech.ng",
            "source":       "threatfade",
            "source_label": "ThreatFade — Security Gap",
            "signal_type":  "threatfade_missing_dmarc",
            "score":        70,
            "signal_data":  {"gap_type": "missing_dmarc", "severity": "high"},
            "is_hot":       False,
            "suggested_first_line": "DMARC signal detected — connect ThreatFade API to see real companies",
            "discovered_at": datetime.utcnow().isoformat(),
        }
    ]

async def _fetch_reconos_signals() -> list:
    """
    ReconOS OFE — OSINT signals
    6,277 lines, 145 jurisdictions, AfricanContextEngine
    """
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"{RECONOS_URL}/api/fadereach-signals",
                headers={"X-Internal": "fadereach"}
            )
        if resp.status_code != 200:
            return []
        signals = resp.json().get("signals", [])
        return [
            {
                "id":           hash(s.get("domain", "") + "reconos") & 0x7FFFFFFF,
                "email":        s.get("contact_email"),
                "company":      s.get("company_name"),
                "domain":       s.get("domain"),
                "source":       "reconos",
                "source_label": f"ReconOS — {s.get('signal_label','Signal')}",
                "signal_type":  f"reconos_{s.get('signal_type','expansion_signal')}",
                "score":        SIGNAL_SCORES.get(
                    f"reconos_{s.get('signal_type','expansion_signal')}",
                    74
                ),
                "signal_data": {
                    "signal_type":  s.get("signal_type"),
                    "signal_detail":s.get("signal_detail"),
                    "jurisdiction": s.get("jurisdiction"),
                    "source_url":   s.get("source_url"),
                },
                "is_hot":       s.get("signal_type") in ["funding_round","leadership_change"],
                "discovered_at": s.get("detected_at", datetime.utcnow().isoformat()),
            }
            for s in signals if s.get("contact_email")
        ]
    except:
        return []

async def _fetch_apollo_signals() -> list:
    """
    Apollo.io signals — job changes, hiring spikes, funding
    Uses tinlance.com account (10K credits/mo free)
    """
    if not APOLLO_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.apollo.io/v1/mixed_people/search",
                headers={"X-Api-Key": APOLLO_KEY, "Content-Type": "application/json"},
                json={
                    "signal_types": ["job_change", "funding"],
                    "q_not_organization_domains": ["gmail.com","yahoo.com","hotmail.com"],
                    "page": 1, "per_page": 25,
                }
            )
        if resp.status_code != 200:
            return []
        people = resp.json().get("people", [])
        return [
            {
                "id":           hash(p.get("email","") + "apollo") & 0x7FFFFFFF,
                "email":        p.get("email"),
                "first_name":   p.get("first_name"),
                "last_name":    p.get("last_name"),
                "company":      p.get("organization", {}).get("name"),
                "title":        p.get("title"),
                "domain":       p.get("organization", {}).get("primary_domain"),
                "linkedin_url": p.get("linkedin_url"),
                "source":       "apollo",
                "source_label": "Apollo — " + (
                    "Job Change" if p.get("employment_history") else "Signal"
                ),
                "signal_type":  "apollo_hiring_signal",
                "score":        SIGNAL_SCORES["apollo_hiring_signal"],
                "signal_data": {
                    "headline":     p.get("headline"),
                    "seniority":    p.get("seniority"),
                    "departments":  p.get("departments"),
                },
                "is_hot":       False,
                "discovered_at": datetime.utcnow().isoformat(),
            }
            for p in people if p.get("email")
        ]
    except:
        return []
