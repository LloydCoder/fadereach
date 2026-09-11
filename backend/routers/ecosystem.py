"""
FadeReach — Ecosystem Orchestrator
The 17-wire flywheel. Every Tinlance product connected.

This is the moat. Each wire takes competitors years to replicate
because they don't have the other 17 products.

Wire map:
01. ThreatFade    → security gaps → campaign triggers
02. FusionOps     → SOC gaps → prospect signals
03. ReconOS OFE   → OSINT → Opportunity Feed (Phase 3)
04. BugFlow Elite → vuln seeds → AppSec outreach
05. TwinGuard     → AI safety gaps → EU enterprise outreach
06. AI Shield     → LLM findings → runtime security outreach
07. KalevioAI     → compliance content → sequence assets
08. HezCast       → auto-generated campaign copy
09. FederX AI     → FL platform → EU HealthTech/DefenceTech outreach
10. ResonaForge   → content engagement → warm leads (Phase 3)
11. RealtyScreen  → US PropTech → waitlist campaigns
12. FadeForge AI  → synthetic threats → EU pen test outreach
13. ResilientAI   → IT resilience → MSP outreach
14. GiftMode      → e-commerce → gifting brand outreach
15. FDSE Toolkit  → enterprise security → CISO outreach
16. Web-Temify    → email templates → template marketplace
17. Olvrix        → CRM + widgets → largest data generator (Phase 3)
"""
from fastapi import APIRouter, Request, Depends, BackgroundTasks, HTTPException
from pydantic import BaseModel
from .deps import get_current_tenant
import httpx, os, json
from datetime import datetime
from typing import Optional

router = APIRouter()

# ── Service registry ────────────────────────────
SERVICES = {
    "threatfade":    os.getenv("THREATFADE_URL",   "http://localhost:8504"),
    "fusionops":     os.getenv("FUSIONOPS_URL",    "http://13.50.16.19:8000"),
    "reconos":       os.getenv("RECONOS_URL",      "http://localhost:8503"),
    "bugflow":       os.getenv("BUGFLOW_URL",       "http://localhost:8502"),
    "twinguard":     os.getenv("TWINGUARD_URL",     "http://localhost:8506"),
    "ai_shield":     os.getenv("AI_SHIELD_URL",     "http://localhost:8507"),
    "kalevioai":     os.getenv("KALEVIOAI_URL",     "http://localhost:8508"),
    "hezcast":       os.getenv("HEZCAST_URL",       "http://localhost:8509"),
    "federx":        os.getenv("FEDERX_URL",        "http://localhost:8510"),
    "resonaforge":   os.getenv("RESONAFORGE_URL",   "http://localhost:8010"),
    "realtyscreen":  os.getenv("REALTYSCREEN_URL",  "http://localhost:8511"),
    "fadeforge":     os.getenv("FADEFORGE_URL",     "http://localhost:8512"),
    "resilientai":   os.getenv("RESILIENTAI_URL",   "http://localhost:8513"),
    "giftmode":      os.getenv("GIFTMODE_URL",      "http://localhost:8514"),
    "fdse":          os.getenv("FDSE_URL",           "http://localhost:8515"),
    "webtemify":     os.getenv("WEBTEMIFY_URL",      "http://localhost:8516"),
    "olvrix":        os.getenv("OLVRIX_URL",         "http://localhost:8505"),
}

INTERNAL_KEY = os.getenv("INTERNAL_API_KEY", "fr-internal-key")

# ── Campaign templates per product ──────────────
PRODUCT_CAMPAIGNS = {
    "threatfade": {
        "segments": ["nigerian_fintech", "african_bank", "eu_security_team", "us_enterprise"],
        "sequences": {
            "nigerian_fintech": {
                "subject_templates": [
                    "Your email infrastructure has a gap",
                    "{company}'s DMARC is missing",
                    "Security question about {domain}",
                ],
                "step1": "Noticed {company}'s DMARC policy is set to p=none — meaning spoofed emails sent in your name currently land in customer inboxes undetected.",
                "step2_subject": "Following up — {company} email security",
                "step2": "Sent a note last week about {company}'s email authentication gap. Most Nigerian fintechs don't discover this until a customer calls about a phishing email that appeared to come from you.",
                "step3_subject": "One thing before I go",
                "step3": "I'll keep this brief — we built ThreatFade specifically to detect C2 traffic and email security gaps in Nigerian fintech infrastructure. Happy to run a free scan on {domain} if that would be useful.",
                "cta": "Worth a 15-minute call to review what we find?",
            },
            "eu_security_team": {
                "subject_templates": [
                    "NIS2 technical requirement most teams miss",
                    "{company}'s threat detection blind spot",
                    "C2 detection at {company}",
                ],
                "step1": "NIS2 Article 21 requires documented threat detection capabilities — most EU security teams have SIEM coverage but miss the C2 beacon patterns that bypass standard signatures.",
                "cta": "Open to a technical conversation about your current detection stack?",
            },
        },
        "product_url": os.getenv("THREATFADE_PUBLIC_URL", "https://github.com/LloydCoder/tinlance-threatfade"),
    },
    "kalevioai": {
        "segments": ["eu_compliance_officer", "nис2_affected_company", "dora_fintech"],
        "sequences": {
            "eu_compliance_officer": {
                "subject_templates": [
                    "NIS2 deadline — {company}'s readiness",
                    "DORA compliance gap we see often",
                    "Question about {company}'s NIS2 posture",
                ],
                "step1": "With NIS2 enforcement now active, most compliance officers at companies like {company} are managing a manual documentation burden that KalevioAI was built to eliminate.",
                "cta": "Is NIS2 documentation still a manual process at {company}?",
            },
        },
        "product_url": os.getenv("KALEVIOAI_URL", ""),
    },
    "realtyscreen": {
        "segments": ["us_landlord", "property_manager", "proptech_company"],
        "sequences": {
            "us_landlord": {
                "subject_templates": [
                    "FCRA-compliant tenant screening for {company}",
                    "Tenant screening question",
                    "{company} + RealtyScreen AI",
                ],
                "step1": "Most property managers at {company}'s scale run into the same FCRA compliance gap during tenant screening — the process is manual, slow, and one mistake away from a lawsuit.",
                "cta": "Worth 15 minutes to see how RealtyScreen AI handles this automatically?",
            },
        },
        "product_url": os.getenv("REALTYSCREEN_URL", ""),
    },
    "giftmode": {
        "segments": ["ecommerce_brand", "corporate_gifting", "hr_team"],
        "sequences": {
            "ecommerce_brand": {
                "subject_templates": [
                    "AI gifting for {company} customers",
                    "Increase repeat purchases at {company}",
                    "Question about {company}'s gifting experience",
                ],
                "step1": "E-commerce brands at {company}'s scale typically see a 23% drop in repeat purchases because the gifting experience feels generic — GiftMode AI personalizes at scale without the manual overhead.",
                "cta": "Worth exploring for {company}'s next gifting campaign?",
            },
        },
        "product_url": os.getenv("GIFTMODE_PUBLIC_URL", "https://giftmode.app"),
    },
    "webtemify": {
        "segments": ["african_developer", "freelance_designer", "digital_agency"],
        "sequences": {
            "african_developer": {
                "subject_templates": [
                    "Premium templates for {company}",
                    "Save 40 hours on your next project",
                    "Question for the team at {company}",
                ],
                "step1": "Developers at agencies like {company} typically spend 30-40 hours per project on UI components that Web-Temify ships as production-ready templates — designed specifically for the African market.",
                "cta": "Want to see the library? First template is free.",
            },
        },
        "product_url": os.getenv("WEBTEMIFY_URL", ""),
    },
    "olvrix": {
        "segments": ["small_agency", "smb_owner", "freelance_consultant"],
        "sequences": {
            "small_agency": {
                "subject_templates": [
                    "All-in-one platform for {company}",
                    "Replace 6 tools with one at {company}",
                    "Quick question about {company}'s stack",
                ],
                "step1": "Agencies at {company}'s stage typically run 6-8 separate tools — CRM, invoicing, project management, client portal, scheduling, and reporting. Olvrix consolidates all of them into one.",
                "cta": "Is managing multiple tools costing {company} more time than it should?",
            },
        },
        "product_url": os.getenv("OLVRIX_PUBLIC_URL", ""),
    },
    "federx": {
        "segments": ["eu_healthtech", "eu_defencetech", "research_institution"],
        "sequences": {
            "eu_healthtech": {
                "subject_templates": [
                    "Federated learning for {company}'s data",
                    "GDPR-compliant ML at {company}",
                    "{company} + FederX AI",
                ],
                "step1": "HealthTech companies at {company}'s stage typically can't share patient data across sites for ML training — FederX AI runs federated learning that keeps data on your servers while models improve across the network.",
                "cta": "Is cross-site ML training a constraint at {company} right now?",
            },
        },
        "product_url": os.getenv("FEDERX_PUBLIC_URL", ""),
    },
    "twinguard": {
        "segments": ["eu_ai_team", "enterprise_ml", "ai_governance"],
        "sequences": {
            "eu_ai_team": {
                "subject_templates": [
                    "AI Act compliance at {company}",
                    "Agent containment question for {company}",
                    "{company}'s agentic AI risk",
                ],
                "step1": "EU AI Act Article 9 requires documented risk management for high-risk AI systems — most teams at {company}'s stage have deployed agentic workflows without the containment layer Article 9 requires.",
                "cta": "Is EU AI Act compliance on {company}'s roadmap this quarter?",
            },
        },
        "product_url": os.getenv("TWINGUARD_PUBLIC_URL", "https://twinguard.ai"),
    },
    "ai_shield": {
        "segments": ["llm_deployer", "ai_startup", "enterprise_ai"],
        "sequences": {
            "llm_deployer": {
                "subject_templates": [
                    "Runtime security for {company}'s LLM",
                    "Prompt injection at {company}",
                    "{company}'s AI attack surface",
                ],
                "step1": "Companies shipping LLM features at {company}'s velocity typically add runtime protection after the first incident — AI Shield adds the guardrail before that happens.",
                "cta": "Is runtime LLM security in {company}'s security roadmap?",
            },
        },
        "product_url": os.getenv("AI_SHIELD_PUBLIC_URL", ""),
    },
    "fadeforge": {
        "segments": ["eu_pentest_firm", "red_team", "security_trainer"],
        "sequences": {
            "eu_pentest_firm": {
                "subject_templates": [
                    "Synthetic threat PCAPs for {company}",
                    "Red team tooling question",
                    "{company} + FadeForge AI",
                ],
                "step1": "Pen testing firms at {company}'s scale spend significant time generating realistic threat scenarios — FadeForge AI synthesizes validated QUIC C2 PCAPs so your red team focuses on analysis, not generation.",
                "cta": "Worth seeing a sample PCAP set we generated last week?",
            },
        },
        "product_url": os.getenv("FADEFORGE_PUBLIC_URL", ""),
    },
    "resilientai": {
        "segments": ["it_manager", "msp", "enterprise_it"],
        "sequences": {
            "it_manager": {
                "subject_templates": [
                    "Proactive IT resilience for {company}",
                    "{company}'s IT incident pattern",
                    "Before the next outage at {company}",
                ],
                "step1": "IT teams at {company}'s scale typically discover infrastructure weaknesses during incidents rather than before them — ResilientAI monitors proactively and flags issues before they become outages.",
                "cta": "Is reactive IT management still the norm at {company}?",
            },
        },
        "product_url": os.getenv("RESILIENTAI_PUBLIC_URL", ""),
    },
    "bugflow": {
        "segments": ["security_researcher", "appsec_team", "bug_bounty"],
        "sequences": {
            "appsec_team": {
                "subject_templates": [
                    "Autonomous vuln discovery for {company}",
                    "AppSec question for {company}",
                    "{company}'s attack surface",
                ],
                "step1": "AppSec teams at {company}'s scale typically run manual vulnerability scans that miss the chained vulnerability scenarios BugFlow Elite discovers autonomously across 51 modules.",
                "cta": "Worth running BugFlow against {company}'s staging environment?",
            },
        },
        "product_url": os.getenv("BUGFLOW_PUBLIC_URL", "https://github.com/LloydCoder/bugflow-elite"),
    },
    "fdse": {
        "segments": ["ciso", "enterprise_security", "security_consultant"],
        "sequences": {
            "ciso": {
                "subject_templates": [
                    "Security delivery toolkit for {company}",
                    "IR playbook question for {company}",
                    "{company} security posture",
                ],
                "step1": "Security teams at {company}'s scale often spend significant time on deliverable formatting — the FDSE Toolkit v2.0 ships IR playbooks, ROI calculators, and identity threat scanners pre-built and ready to deploy.",
                "cta": "Would a pre-built security deliverable kit save {company}'s team meaningful time?",
            },
        },
        "product_url": os.getenv("FDSE_PUBLIC_URL", ""),
    },
}

# ── Routes ──────────────────────────────────────
@router.get("/status")
async def ecosystem_status(
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    """Health check all 17 connected services"""
    results = {}
    async with httpx.AsyncClient(timeout=3.0) as client:
        for name, url in SERVICES.items():
            try:
                resp = await client.get(f"{url}/health")
                results[name] = {
                    "status": "online" if resp.status_code == 200 else "error",
                    "url": url,
                }
            except:
                results[name] = {"status": "offline", "url": url}

    online = sum(1 for v in results.values() if v["status"] == "online")
    return {
        "total_services": len(SERVICES),
        "online":         online,
        "offline":        len(SERVICES) - online,
        "services":       results,
        "flywheel_active": online >= 3,
    }

@router.get("/campaigns/available")
async def available_campaigns(
    auth: dict = Depends(get_current_tenant),
):
    """
    All pre-built campaign sequences across all 17 products
    Ready to launch immediately
    """
    campaigns = []
    for product, data in PRODUCT_CAMPAIGNS.items():
        for segment, seq in data["sequences"].items():
            campaigns.append({
                "product":      product,
                "segment":      segment,
                "segment_label":segment.replace("_", " ").title(),
                "subject_options": seq.get("subject_templates", []),
                "step1_preview":   seq.get("step1", "")[:120] + "...",
                "cta":             seq.get("cta", ""),
                "product_url":     data.get("product_url", ""),
                "steps":           4,
            })
    return {
        "total":     len(campaigns),
        "campaigns": campaigns,
        "products":  list(PRODUCT_CAMPAIGNS.keys()),
    }

@router.post("/campaigns/launch")
async def launch_ecosystem_campaign(
    request: Request,
    background_tasks: BackgroundTasks,
    auth: dict = Depends(get_current_tenant),
    product: str = "threatfade",
    segment: str = "nigerian_fintech",
):
    """
    Launch a pre-built ecosystem campaign
    Pulls sequence from product library, creates campaign, assigns leads
    """
    db        = request.app.state.db
    tenant_id = auth["sub"]

    prod_data = PRODUCT_CAMPAIGNS.get(product)
    if not prod_data:
        raise HTTPException(404, f"No campaign template for product: {product}")

    seq = prod_data["sequences"].get(segment)
    if not seq:
        raise HTTPException(404, f"No sequence for segment: {segment}")

    # Create campaign
    subject = seq.get("subject_templates", ["Outreach campaign"])[0]
    async with db.acquire() as conn:
        campaign_id = await conn.fetchval("""
            INSERT INTO campaigns
            (tenant_id, name, subject, product, target_segment, status, sequence_steps)
            VALUES ($1,$2,$3,$4,$5,'draft',4) RETURNING id
        """, tenant_id,
            f"{product.title()} → {segment.replace('_',' ').title()}",
            subject, product, segment)

    return {
        "campaign_id":    campaign_id,
        "product":        product,
        "segment":        segment,
        "subject":        subject,
        "sequence_steps": 4,
        "status":         "draft",
        "next_step":      f"Add leads from Opportunity Feed → launch campaign #{campaign_id}",
    }

@router.get("/hezcast/copy")
async def get_hezcast_copy(
    product: str,
    segment: str,
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    """
    Pull campaign copy from HezCast Engine
    HezCast auto-generates fresh copy for all Tinlance products
    287 tests, ready to deploy
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{SERVICES['hezcast']}/api/generate-campaign-copy",
                headers={"X-Internal": INTERNAL_KEY},
                json={"product": product, "segment": segment, "steps": 4}
            )
        if resp.status_code == 200:
            return resp.json()
    except:
        pass

    # Fallback: return from PRODUCT_CAMPAIGNS library
    seq = PRODUCT_CAMPAIGNS.get(product, {}).get("sequences", {}).get(segment, {})
    return {
        "product":  product,
        "segment":  segment,
        "source":   "template_library",
        "copy": {
            "step1_subject": seq.get("subject_templates", ["Outreach"])[0],
            "step1_body":    seq.get("step1", ""),
            "step2_subject": seq.get("step2_subject", "Following up"),
            "step2_body":    seq.get("step2", ""),
            "step3_subject": seq.get("step3_subject", "One last thing"),
            "step3_body":    seq.get("step3", ""),
            "step4_subject": "Closing the loop",
            "step4_body":    "No worries if the timing isn't right — I'll reach back out in a few months. If anything changes before then, you know where to find us.",
            "cta":           seq.get("cta", "Worth a quick call?"),
        }
    }

@router.get("/kalevioai/content")
async def get_kalevioai_content(
    content_type: str,
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    """
    Pull compliance content from KalevioAI
    NIS2/DORA guides → sequence value-add assets
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{SERVICES['kalevioai']}/api/content/{content_type}",
                headers={"X-Internal": INTERNAL_KEY}
            )
        if resp.status_code == 200:
            return resp.json()
    except:
        pass

    # Fallback content
    content_library = {
        "nis2_checklist": {
            "title":       "NIS2 Compliance Checklist",
            "description": "12-point NIS2 readiness assessment for EU organizations",
            "cta":         "Download the free NIS2 checklist",
            "url":         "https://fadereach.tinlance.com/resources/nis2-checklist",
        },
        "dora_guide": {
            "title":       "DORA Technical Implementation Guide",
            "description": "Step-by-step DORA compliance roadmap for EU fintechs",
            "cta":         "Get the DORA guide",
            "url":         "https://fadereach.tinlance.com/resources/dora-guide",
        },
        "email_security_report": {
            "title":       "Nigerian Fintech Email Security Report 2026",
            "description": "Analysis of email authentication gaps across 500 Nigerian fintechs",
            "cta":         "Download the security report",
            "url":         "https://fadereach.tinlance.com/resources/ng-fintech-security",
        },
    }
    return content_library.get(content_type, {
        "error":   f"Content type '{content_type}' not found",
        "available": list(content_library.keys()),
    })

@router.post("/resonaforge/sync")
async def sync_resonaforge_signals(
    background_tasks: BackgroundTasks,
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    """
    Sync ResonaForge content engagement signals
    into FadeReach Opportunity Feed
    """
    tenant_id = auth["sub"]
    background_tasks.add_task(
        _sync_resonaforge_background,
        request.app.state.db,
        request.app.state.redis,
        tenant_id
    )
    return {
        "syncing":  True,
        "message":  "ResonaForge signals syncing — Opportunity Feed updates in ~30 seconds",
        "wire":     "resonaforge → fadereach",
    }

@router.post("/olvrix/sync")
async def sync_olvrix_data(
    background_tasks: BackgroundTasks,
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    """
    Sync Olvrix CRM contacts + Widget signals
    into FadeReach via fadereach_sync bridge
    """
    tenant_id = auth["sub"]
    background_tasks.add_task(
        _sync_olvrix_background,
        request.app.state.db,
        request.app.state.redis,
        tenant_id
    )
    return {
        "syncing":  True,
        "message":  "Olvrix data syncing — leads appear in Opportunity Feed in ~60 seconds",
        "wire":     "olvrix → fadereach",
        "bridges":  ["fadereach_sync", "widget_signals"],
    }

@router.get("/webtemify/templates")
async def get_webtemify_templates(
    category: Optional[str] = None,
    auth: dict = Depends(get_current_tenant),
):
    """
    Web-Temify marketplace inside FadeReach
    Email templates, sequence packs, vertical kits
    """
    try:
        url = f"{SERVICES['webtemify']}/api/templates"
        if category:
            url += f"?category={category}"
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers={"X-Internal": INTERNAL_KEY})
        if resp.status_code == 200:
            return resp.json()
    except:
        pass

    # Fallback catalogue
    return {
        "templates": [
            {
                "id":          "cold-email-cybersecurity",
                "name":        "Cybersecurity Cold Email Pack",
                "description": "8 battle-tested sequences for ThreatFade, AI Shield, and security services",
                "category":    "cold_email",
                "price_usd":   19,
                "items":       8,
                "product_fit": ["threatfade", "ai_shield", "bugflow", "fdse"],
            },
            {
                "id":          "cold-email-saas-africa",
                "name":        "African SaaS Outreach Pack",
                "description": "12 sequences tailored for Nigerian fintech, dev agencies, and SMBs",
                "category":    "cold_email",
                "price_usd":   24,
                "items":       12,
                "product_fit": ["webtemify", "olvrix", "giftmode"],
            },
            {
                "id":          "cold-email-eu-compliance",
                "name":        "EU Compliance Outreach Kit",
                "description": "6 sequences for NIS2, DORA, and EU AI Act audiences",
                "category":    "cold_email",
                "price_usd":   29,
                "items":       6,
                "product_fit": ["kalevioai", "twinguard", "federx", "ai_shield"],
            },
            {
                "id":          "cold-email-proptech",
                "name":        "US PropTech Sequence Pack",
                "description": "4 FCRA-sensitive sequences for RealtyScreen AI campaigns",
                "category":    "cold_email",
                "price_usd":   14,
                "items":       4,
                "product_fit": ["realtyscreen"],
            },
        ],
        "source": "template_library",
        "note":   "Connect Web-Temify to access full 44-product catalogue",
    }

@router.get("/flywheel/metrics")
async def flywheel_metrics(
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    """
    The complete ecosystem flywheel metrics
    Shows how each product feeds FadeReach and vice versa
    """
    db        = request.app.state.db
    redis     = request.app.state.redis
    tenant_id = auth["sub"]

    async with db.acquire() as conn:
        total_leads = await conn.fetchval(
            "SELECT COUNT(*) FROM leads WHERE tenant_id=$1", tenant_id
        )
        total_campaigns = await conn.fetchval(
            "SELECT COUNT(*) FROM campaigns WHERE tenant_id=$1", tenant_id
        )
        total_replies = await conn.fetchval(
            "SELECT COUNT(*) FROM replies WHERE tenant_id=$1", tenant_id
        )
        hot_leads = await conn.fetchval(
            "SELECT COUNT(*) FROM replies WHERE tenant_id=$1 AND is_hot=TRUE", tenant_id
        )
        product_breakdown = await conn.fetch("""
            SELECT product, COUNT(*) as campaigns,
                   SUM(emails_sent) as sent, SUM(replies) as replies
            FROM campaigns WHERE tenant_id=$1 AND product IS NOT NULL
            GROUP BY product ORDER BY replies DESC
        """, tenant_id)

    # Signal counts per source from opportunity feed cache
    opp_cache = await redis.get(f"opportunity_feed:{tenant_id}:60")
    opps      = json.loads(opp_cache) if opp_cache else []
    by_source = {}
    for opp in opps:
        src = opp.get("source", "unknown")
        by_source[src] = by_source.get(src, 0) + 1

    return {
        "flywheel": {
            "total_leads":      int(total_leads),
            "total_campaigns":  int(total_campaigns),
            "total_replies":    int(total_replies),
            "hot_leads":        int(hot_leads),
            "opportunity_signals": len(opps),
        },
        "signal_sources":    by_source,
        "product_breakdown": [dict(r) for r in product_breakdown],
        "wires_active":      len([s for s in by_source if s in SERVICES]),
        "wires_total":       17,
        "flywheel_velocity": round(int(total_replies) / max(int(total_campaigns), 1), 2),
        "ecosystem_health":  "active" if int(total_campaigns) > 0 else "warming_up",
    }

# ── Background tasks ────────────────────────────
async def _sync_resonaforge_background(db, redis, tenant_id: str):
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{SERVICES['resonaforge']}/api/fadereach-signals/{tenant_id}",
                headers={"X-Internal": INTERNAL_KEY}
            )
        if resp.status_code == 200:
            signals = resp.json().get("signals", [])
            async with db.acquire() as conn:
                for sig in signals:
                    if sig.get("email"):
                        await conn.execute("""
                            INSERT INTO leads
                            (tenant_id, email, first_name, company,
                             signal_type, signal_data, icp_score)
                            VALUES ($1,$2,$3,$4,'resonaforge_engaged',$5,72)
                            ON CONFLICT DO NOTHING
                        """, tenant_id,
                            sig.get("email"), sig.get("first_name"),
                            sig.get("company"),
                            json.dumps(sig))
            # Invalidate opportunity feed cache
            await redis.delete(f"opportunity_feed:{tenant_id}:60")
    except Exception as e:
        print(f"ResonaForge sync error: {e}")

async def _sync_olvrix_background(db, redis, tenant_id: str):
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{SERVICES['olvrix']}/api/fadereach-sync/{tenant_id}",
                headers={"X-Internal": INTERNAL_KEY}
            )
        if resp.status_code == 200:
            contacts = resp.json().get("contacts", [])
            async with db.acquire() as conn:
                for contact in contacts:
                    if contact.get("email"):
                        await conn.execute("""
                            INSERT INTO leads
                            (tenant_id, email, first_name, last_name,
                             company, title, signal_type, signal_data)
                            VALUES ($1,$2,$3,$4,$5,$6,'olvrix_sync',$7)
                            ON CONFLICT DO NOTHING
                        """, tenant_id,
                            contact.get("email"),
                            contact.get("first_name"),
                            contact.get("last_name"),
                            contact.get("company"),
                            contact.get("title"),
                            json.dumps(contact))
            await redis.delete(f"opportunity_feed:{tenant_id}:60")
    except Exception as e:
        print(f"Olvrix sync error: {e}")
