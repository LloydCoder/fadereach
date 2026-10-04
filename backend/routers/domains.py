"""FadeReach — Domains Router
DNS verification · Warmup engine · Deliverability Copilot
"""
from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from pydantic import BaseModel
from .deps import get_current_tenant
import httpx, os
from datetime import datetime
import socket
import ipaddress
import re

router = APIRouter()

HUNTER_KEY      = os.getenv("HUNTER_API_KEY", "")
REACHER_URL     = os.getenv("REACHER_URL", "http://localhost:8083")
CLAUDE_API_KEY  = os.getenv("CLAUDE_API_KEY", "")

# Plan domain limits
PLAN_LIMITS = {"trial": 1, "early_adopter": 1, "growth": 3, "agency": 10}

# Warmup schedule: day → daily limit
WARMUP_SCHEDULE = [
    (0,  7,  5),   # Days 0-7:   5/day
    (7,  14, 15),  # Days 7-14:  15/day
    (14, 21, 30),  # Days 14-21: 30/day
    (21, 28, 60),  # Days 21-28: 60/day
    (28, 35, 100), # Days 28-35: 100/day
]

class DomainAddReq(BaseModel):
    domain: str
    dkim_selector: str = "mail"
    sending_ip: str | None = None


def normalize_domain(value: str) -> str:
    value = value.strip().rstrip(".").lower()
    if len(value) > 253 or not value or "@" in value or "/" in value:
        raise HTTPException(400, "Invalid sending domain")
    try:
        ipaddress.ip_address(value)
        raise HTTPException(400, "Sending domain must be a hostname, not an IP address")
    except ValueError:
        pass
    try:
        value = value.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise HTTPException(400, "Invalid internationalized domain name") from exc
    labels = value.split(".")
    if len(labels) < 2 or any(
        not label or len(label) > 63 or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
        for label in labels
    ):
        raise HTTPException(400, "Invalid sending domain")
    return value

async def check_dns(domain: str, dkim_selector: str = "mail", sending_ip: str | None = None) -> dict:
    """Check observable sender controls without predicting inbox placement."""
    result = {"spf": False, "dkim": False, "dmarc": False, "mx": False, "ptr": None, "dmarc_policy": None}
    try:
        import dns.resolver
        try:
            answers = dns.resolver.resolve(domain, "TXT")
            result["spf"] = any("v=spf1" in str(r).lower() for r in answers)
        except Exception:
            pass
        try:
            answers = dns.resolver.resolve(f"{dkim_selector}._domainkey.{domain}", "TXT")
            result["dkim"] = any("v=DKIM1" in str(r).upper() or "P=" in str(r).upper() for r in answers)
        except Exception:
            pass
        try:
            answers = dns.resolver.resolve(f"_dmarc.{domain}", "TXT")
            for r in answers:
                value = str(r).replace('"', '')
                if "v=DMARC1" in value.upper():
                    result["dmarc"] = True
                    for part in value.split(";"):
                        if part.strip().lower().startswith("p="):
                            result["dmarc_policy"] = part.split("=", 1)[1].strip().lower()
        except Exception:
            pass
        try:
            dns.resolver.resolve(domain, "MX")
            result["mx"] = True
        except Exception:
            pass
        if sending_ip:
            try:
                result["ptr"] = bool(socket.gethostbyaddr(sending_ip)[0])
            except Exception:
                result["ptr"] = False
    except Exception as exc:
        print(f"DNS check error [{domain}]: {exc}")
    return result


def calculate_health_score(dns: dict, bounce_rate: float,
                            complaint_rate: float, warmup_day: int) -> tuple[int, int, list]:
    """
    Deliverability Copilot — core scoring logic
    Returns: (health_score 0-100, deliverability_readiness 0-100, issues[])
    """
    score  = 100
    issues = []

    # DNS scoring (60 points total)
    if not dns.get("spf"):
        score -= 20
        issues.append({
            "severity": "critical",
            "type": "spf_missing",
            "message": "SPF record missing",
            "fix": f"Add TXT record: v=spf1 ip4:YOUR_SENDING_IP ~all",
            "impact": "Emails may be rejected by recipient servers"
        })
    if not dns.get("dkim"):
        score -= 20
        issues.append({
            "severity": "critical",
            "type": "dkim_missing",
            "message": "DKIM not configured",
            "fix": "Run setup.sh to generate 2048-bit DKIM key, add TXT record to mail._domainkey",
            "impact": "Unauthenticated mail is more likely to be rejected or filtered; placement impact varies by provider and reputation."
        })
    if not dns.get("dmarc"):
        score -= 20
        issues.append({
            "severity": "high",
            "type": "dmarc_missing",
            "message": "DMARC policy missing",
            "fix": "Add TXT record to _dmarc: v=DMARC1; p=none; rua=mailto:dmarc@yourdomain.com",
            "impact": "Required by major mailbox providers for relevant bulk-sender scenarios; enforcement and placement outcomes vary by provider."
        })

    # Bounce rate (20 points)
    if bounce_rate > 2.0:
        score -= 20
        issues.append({
            "severity": "critical",
            "type": "bounce_rate_critical",
            "message": f"Bounce rate {bounce_rate:.1f}% — above 2% limit",
            "fix": "Pause campaigns immediately. Clean your list with Reacher before resuming.",
            "impact": "Elevated bounce rates can damage sender reputation and trigger provider enforcement."
        })
    elif bounce_rate > 1.5:
        score -= 10
        issues.append({
            "severity": "high",
            "type": "bounce_rate_high",
            "message": f"Bounce rate {bounce_rate:.1f}% — approaching limit",
            "fix": "Reduce volume by 30%. Verify remaining list before next send.",
            "impact": "Reputation declining — act before reaching 2%"
        })

    # Complaint rate (20 points)
    if complaint_rate > 0.08:
        score -= 20
        issues.append({
            "severity": "critical",
            "type": "complaint_rate_critical",
            "message": f"Complaint rate {complaint_rate:.3f}% — above 0.08% limit",
            "fix": "Stop all campaigns. Review targeting and ICP fit. Improve unsubscribe visibility.",
            "impact": "Elevated complaint rates can degrade sender reputation and trigger provider filtering."
        })
    elif complaint_rate > 0.05:
        score -= 10
        issues.append({
            "severity": "high",
            "type": "complaint_rate_high",
            "message": f"Complaint rate {complaint_rate:.3f}% — approaching limit",
            "fix": "Review recent campaigns for relevance. Tighten ICP targeting.",
            "impact": "Approaching Google's threshold for reputation downgrade"
        })

    # Warmup status
    if warmup_day < 7:
        issues.append({
            "severity": "info",
            "type": "warmup_early",
            "message": f"Warmup day {warmup_day}/35 — limit 5 emails/day",
            "fix": "Continue warmup process. Do not send beyond daily limit.",
            "impact": "Sending above limit will damage reputation before it is established"
        })

    # Deliverability readiness is a bounded readiness indicator, not a prediction
    # of inbox placement. It reflects observable controls and recent metrics.
    readiness = min(100, max(0, score))
    if warmup_day < 14:
        readiness = min(readiness, 75)

    return max(0, score), readiness, issues

async def generate_copilot_explanation(
    domain: str, score: int, readiness: int, issues: list
) -> str:
    """
    Deliverability Copilot — AI explains health in plain English
    Uses Claude API (existing key)
    """
    if not CLAUDE_API_KEY or not issues:
        if score >= 85:
            return f"Your domain {domain} is healthy. Deliverability readiness: {readiness}%. Keep monitoring bounce and complaint rates daily."
        return f"Your domain {domain} has {len(issues)} issue(s) affecting deliverability. Fix the critical items first — they have the biggest inbox impact."

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": CLAUDE_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 200,
                    "messages": [{
                        "role": "user",
                        "content": f"""You are FadeReach's Deliverability Copilot.
Domain: {domain}
Health score: {score}/100
Deliverability readiness: {readiness}%
Issues: {[i['message'] for i in issues[:3]]}

Write 2-3 sentences explaining this in plain English for a non-technical founder.
Focus on what it means for their campaigns, not the technical details.
Be direct and specific. No fluff."""
                    }]
                }
            )
        data = resp.json()
        return data["content"][0]["text"].strip()
    except:
        return f"Domain health: {score}/100. Deliverability readiness: {readiness}%. {len(issues)} issue(s) need attention."

@router.post("/add")
async def add_domain(
    req: DomainAddReq,
    background_tasks: BackgroundTasks,
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    db        = request.app.state.db
    tenant_id = auth["sub"]
    plan      = auth.get("plan", "trial")
    limit     = PLAN_LIMITS.get(plan, 1)
    domain = normalize_domain(req.domain)
    if len(req.dkim_selector) > 63 or not re.fullmatch(r"[A-Za-z0-9._-]+", req.dkim_selector):
        raise HTTPException(400, "Invalid DKIM selector")

    async with db.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM domains WHERE tenant_id=$1", tenant_id
        )
        if count >= limit:
            raise HTTPException(403,
                f"Domain limit reached for {plan} plan ({limit} domain{'s' if limit>1 else ''}). "
                f"Upgrade to add more."
            )
        # Check domain not already added
        existing = await conn.fetchrow(
            "SELECT id FROM domains WHERE tenant_id=$1 AND domain=$2",
            tenant_id, domain
        )
        if existing:
            raise HTTPException(409, "Domain already added to your workspace")

        domain_id = await conn.fetchval("""
            INSERT INTO domains (tenant_id, domain, warmup_status)
            VALUES ($1, $2, 'checking') RETURNING id
        """, tenant_id, req.domain.lower().strip())

    background_tasks.add_task(_verify_and_score_domain, db, domain_id, req.domain.lower().strip(), req.dkim_selector, req.sending_ip)

    return {
        "domain_id":  domain_id,
        "domain":     req.domain,
        "status":     "checking",
        "message":    "Domain added. Checking DNS records...",
        "dns_records_needed": _get_dns_guide(req.domain)
    }

@router.post("/{domain_id}/pause")
async def pause_domain(domain_id: int, request: Request, auth: dict = Depends(get_current_tenant)):
    db = request.app.state.db
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE domains SET sending_paused=TRUE, pause_reason='Manually paused', last_deliverability_check=NOW() WHERE id=$1 AND tenant_id=$2 RETURNING id",
            domain_id, auth["sub"],
        )
    if not row:
        raise HTTPException(404, "Domain not found")
    return {"domain_id": domain_id, "sending_paused": True}


@router.post("/{domain_id}/resume")
async def resume_domain(domain_id: int, request: Request, auth: dict = Depends(get_current_tenant)):
    db = request.app.state.db
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT id, spf_valid, dkim_valid, dmarc_valid, mx_valid
               FROM domains WHERE id=$1 AND tenant_id=$2""",
            domain_id, auth["sub"],
        )
        if not row:
            raise HTTPException(404, "Domain not found")
        if not all([row["spf_valid"], row["dkim_valid"], row["dmarc_valid"], row["mx_valid"]]):
            raise HTTPException(409, "Sender authentication and MX checks must pass before resuming")
        await conn.execute(
            "UPDATE domains SET sending_paused=FALSE, pause_reason=NULL, last_deliverability_check=NOW() WHERE id=$1 AND tenant_id=$2",
            domain_id, auth["sub"],
        )
    return {"domain_id": domain_id, "sending_paused": False}


@router.get("")
async def list_domains(request: Request, auth: dict = Depends(get_current_tenant)):
    db = request.app.state.db
    async with db.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, domain, spf_valid, dkim_valid, dmarc_valid, mx_valid,
                   warmup_day, warmup_status, daily_limit, sent_today,
                   bounce_rate, complaint_rate, health_score, deliverability_readiness,
                   sending_paused, pause_reason, last_checked, last_deliverability_check
            FROM domains WHERE tenant_id=$1 ORDER BY added_at DESC
        """, auth["sub"])
    return {"domains": [dict(r) for r in rows]}

@router.post("/{domain_id}/check")
async def recheck_domain(
    domain_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    db = request.app.state.db
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT domain FROM domains WHERE id=$1 AND tenant_id=$2",
            domain_id, auth["sub"]
        )
    if not row:
        raise HTTPException(404, "Domain not found")
    background_tasks.add_task(_verify_and_score_domain, db, domain_id, row["domain"])
    return {"message": "Re-checking DNS records...", "domain": row["domain"]}

@router.get("/{domain_id}/copilot")
async def deliverability_copilot(
    domain_id: int,
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    """
    Deliverability Copilot — full analysis with AI plain-English explanation
    The signature feature. Shows outcomes not protocols.
    """
    db = request.app.state.db
    async with db.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT domain, spf_valid, dkim_valid, dmarc_valid, mx_valid,
                   warmup_day, warmup_status, daily_limit,
                   bounce_rate, complaint_rate, health_score, deliverability_readiness, blacklisted
            FROM domains WHERE id=$1 AND tenant_id=$2
        """, domain_id, auth["sub"])
    if not row:
        raise HTTPException(404, "Domain not found")

    d = dict(row)
    dns_status = {"spf": d["spf_valid"], "dkim": d["dkim_valid"],
                  "dmarc": d["dmarc_valid"], "mx": d.get("mx_valid", False)}

    score, readiness, issues = calculate_health_score(
        dns_status, float(d["bounce_rate"]),
        float(d["complaint_rate"]), d["warmup_day"]
    )
    explanation = await generate_copilot_explanation(
        d["domain"], score, readiness, issues
    )

    # Warmup recommendation
    warmup_rec = next(
        (f"{lim}/day" for lo, hi, lim in WARMUP_SCHEDULE
         if lo <= d["warmup_day"] < hi), "100/day"
    )

    return {
        "domain":          d["domain"],
        "health_score":    score,
        "deliverability_readiness": readiness,
        "grade":           "A" if score>=90 else "B" if score>=75 else "C" if score>=60 else "D",
        "explanation":     explanation,
        "dns_status":      dns_status,
        "warmup": {
            "day":          d["warmup_day"],
            "status":       d["warmup_status"],
            "daily_limit":  d["daily_limit"],
            "recommended":  warmup_rec,
        },
        "metrics": {
            "bounce_rate":    float(d["bounce_rate"]),
            "complaint_rate": float(d["complaint_rate"]),
            "blacklisted":    d["blacklisted"],
        },
        "issues":   issues,
        "all_clear": len([i for i in issues if i["severity"] in ["critical","high"]]) == 0
    }

# ── Internal helpers ────────────────────────────
async def _verify_and_score_domain(db, domain_id: int, domain: str, dkim_selector: str = "mail", sending_ip: str | None = None):
    """Background: check DNS + score + update DB"""
    try:
        dns = await check_dns(domain, dkim_selector, sending_ip)
        score, readiness, _ = calculate_health_score(dns, 0.0, 0.0, 0)
        async with db.acquire() as conn:
            await conn.execute("""
                UPDATE domains
                SET spf_valid=$1, dkim_valid=$2, dmarc_valid=$3, mx_valid=$4,
                    dmarc_policy=$5, ptr_valid=$6,
                    health_score=$7, deliverability_readiness=$8,
                    sending_paused=NOT ($1 AND $2 AND $3 AND $4),
                    pause_reason=CASE WHEN NOT ($1 AND $2 AND $3 AND $4)
                        THEN 'Sender authentication/DNS controls incomplete' ELSE NULL END,
                    warmup_status=CASE WHEN warmup_status='checking'
                        THEN CASE WHEN $1 AND $2 AND $3 AND $4 THEN 'ready' ELSE 'dns_incomplete' END
                        ELSE warmup_status END,
                    last_checked=NOW(), last_deliverability_check=NOW()
                WHERE id=$9
            """, dns["spf"], dns["dkim"], dns["dmarc"], dns["mx"],
                dns["dmarc_policy"], dns["ptr"], score, readiness, domain_id)
    except Exception as e:
        print(f"Domain verify error [{domain}]: {e}")

def _get_dns_guide(domain: str) -> dict:
    return {
        "spf": {
            "type": "TXT", "name": "@",
            "value": "v=spf1 ip4:YOUR_VPS_IP ~all",
            "note": "Use the public sending IP assigned to your mail infrastructure."
        },
        "dkim": {
            "type": "TXT", "name": "mail._domainkey",
            "value": "Run setup.sh to generate — value printed after script completes",
            "note": "2048-bit key required. 1024-bit rejected by Microsoft."
        },
        "dmarc": {
            "type": "TXT", "name": "_dmarc",
            "value": f"v=DMARC1; p=none; rua=mailto:dmarc@{domain}",
            "note": "Start with p=none, graduate to p=reject after 60 days"
        },
        "mx": {
            "type": "MX", "name": "@",
            "value": f"mail.{domain}", "priority": 10,
            "note": "Required for reply tracking"
        }
    }
