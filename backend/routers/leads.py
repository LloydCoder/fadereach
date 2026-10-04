"""FadeReach — Leads Router
Hunter.io + Apollo waterfall · Reacher verification · Claude AI first lines
"""
from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from pydantic import BaseModel
from .deps import get_current_tenant
import httpx, os
from typing import Optional

router = APIRouter()

HUNTER_KEY     = os.getenv("HUNTER_API_KEY", "")
APOLLO_KEY     = os.getenv("APOLLO_API_KEY", "")
REACHER_URL    = os.getenv("REACHER_URL", "http://localhost:8083")
CLAUDE_KEY     = os.getenv("CLAUDE_API_KEY", "")
OLLAMA_URL     = os.getenv("OLLAMA_URL", "http://localhost:11434")
N8N_WEBHOOK    = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook")

AI_CREDITS = {"trial": 50, "early_adopter": 200, "growth": 1000, "agency": 5000}

class LeadSearchReq(BaseModel):
    company_domain: str
    limit: int = 10

class VerifyReq(BaseModel):
    email: str

class AIFirstLineReq(BaseModel):
    leads: list[dict]
    product: str
    tone: str = "professional"

class LeadImportReq(BaseModel):
    leads: list[dict]  # CSV import

# ── Lead finding waterfall ──────────────────────
@router.post("/search")
async def search_leads(
    req: LeadSearchReq,
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    """
    Waterfall: Hunter.io → Apollo.io → GetProspect
    Uses whichever API key is configured
    """
    results = []

    # Step 1: Hunter.io (primary)
    if HUNTER_KEY:
        results = await _hunter_search(req.company_domain, min(req.limit, 10))

    # Step 2: Apollo.io fallback
    if not results and APOLLO_KEY:
        results = await _apollo_search(req.company_domain, min(req.limit, 10))

    # Step 3: Graceful empty state
    if not results:
        return {
            "domain":        req.company_domain,
            "emails_found":  0,
            "leads":         [],
            "source":        "none",
            "message":       "No emails found. Try another domain or check your Hunter.io API key."
        }

    return {
        "domain":       req.company_domain,
        "emails_found": len(results),
        "leads":        results,
        "source":       "hunter" if HUNTER_KEY else "apollo"
    }

@router.post("/verify")
async def verify_email(
    req: VerifyReq,
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    """
    Verification waterfall:
    1. Reacher (self-hosted EC2, $0, unlimited)
    2. Hunter.io verifier (fallback)
    """
    result = await _reacher_verify(req.email)

    if result.get("error") and HUNTER_KEY:
        result = await _hunter_verify(req.email)

    return {"email": req.email, "verification": result}

@router.post("/verify/batch")
async def verify_batch(
    request: Request,
    emails: list[str],
    auth: dict = Depends(get_current_tenant)
):
    """Batch verify up to 100 emails via Reacher"""
    if len(emails) > 100:
        raise HTTPException(400, "Maximum 100 emails per batch")

    results = []
    for email in emails:
        result = await _reacher_verify(email)
        results.append({"email": email, **result})

    valid   = [r for r in results if r.get("is_valid")]
    invalid = [r for r in results if not r.get("is_valid")]

    return {
        "total":       len(emails),
        "valid":       len(valid),
        "invalid":     len(invalid),
        "results":     results,
        "bounce_risk": round(len(invalid) / len(emails) * 100, 1) if emails else 0
    }

@router.post("/ai/first-lines")
async def generate_first_lines(
    req: AIFirstLineReq,
    background_tasks: BackgroundTasks,
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    """
    AI first-line generation
    Primary:   Claude API (best quality)
    Secondary: DeepSeek via Ollama (local, $0)
    Fallback:  Qwen3 via Ollama (local, $0)
    """
    tenant_id = auth["sub"]
    plan      = auth.get("plan", "trial")
    redis     = request.app.state.redis
    db        = request.app.state.db

    # Check credit limit
    credit_key = f"ai_credits:{tenant_id}:{__import__('datetime').datetime.utcnow().strftime('%Y-%m')}"
    used        = int(await redis.get(credit_key) or 0)
    limit       = AI_CREDITS.get(plan, 50)

    if used + len(req.leads) > limit:
        remaining = max(0, limit - used)
        raise HTTPException(429,
            f"AI credit limit reached ({limit}/month on {plan} plan). "
            f"{remaining} credits remaining. "
            f"Upgrade for more or wait until next billing cycle."
        )

    # Try n8n pipeline first (full 5-AI ensemble)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{N8N_WEBHOOK}/ai-first-lines",
                json={
                    "tenant_id": tenant_id,
                    "leads":     req.leads,
                    "product":   req.product,
                    "tone":      req.tone
                }
            )
        if resp.status_code == 200:
            await redis.incrby(credit_key, len(req.leads))
            await redis.expire(credit_key, 2678400)
            return resp.json()
    except:
        pass  # n8n unavailable — fall through to direct generation

    # Direct Claude generation (fallback)
    results = []
    for lead in req.leads[:20]:  # Cap at 20 for direct calls
        first_line = await _generate_single_first_line(lead, req.product, req.tone)
        results.append({
            "email":         lead.get("email"),
            "first_name":    lead.get("first_name"),
            "company":       lead.get("company"),
            "ai_first_line": first_line,
            "source":        "claude_direct"
        })

    # Update credits
    await redis.incrby(credit_key, len(results))
    await redis.expire(credit_key, 2678400)

    # Save first lines to DB
    background_tasks.add_task(_save_first_lines, db, tenant_id, results)

    return {
        "success":   True,
        "generated": len(results),
        "results":   results,
        "credits_used": len(results),
        "credits_remaining": limit - used - len(results)
    }

@router.post("/import")
async def import_leads(
    req: LeadImportReq,
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    """Import leads from CSV (parsed client-side, sent as JSON)"""
    db        = request.app.state.db
    tenant_id = auth["sub"]

    if len(req.leads) > 5000:
        raise HTTPException(400, "Maximum 5,000 leads per import")

    imported = 0
    async with db.acquire() as conn:
        for lead in req.leads:
            email = lead.get("email", "").strip().lower()
            if not email or "@" not in email:
                continue
            try:
                await conn.execute("""
                    INSERT INTO leads
                    (tenant_id, email, first_name, last_name, company,
                     title, domain, linkedin_url, industry, location,
                     lawful_basis, subscriber_type, consent_status, objection_status)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                    ON CONFLICT DO NOTHING
                """, tenant_id, email,
                    lead.get("first_name"), lead.get("last_name"),
                    lead.get("company"),    lead.get("title"),
                    lead.get("domain"),     lead.get("linkedin_url"),
                    lead.get("industry"),   lead.get("location"),
                    lead.get("lawful_basis"), lead.get("subscriber_type", "unknown"),
                    lead.get("consent_status", "unknown"), lead.get("objection_status", "unknown"))
                imported += 1
            except: pass

    return {
        "imported": imported,
        "total":    len(req.leads),
        "skipped":  len(req.leads) - imported,
        "message":  f"{imported} leads imported successfully"
    }

@router.get("")
async def list_leads(
    request: Request,
    auth: dict = Depends(get_current_tenant),
    status: Optional[str] = None,
    limit:  int = 50,
    offset: int = 0
):
    db = request.app.state.db
    where = "WHERE tenant_id=$1"
    params = [auth["sub"]]
    if status:
        where += " AND status=$2"
        params.append(status)

    async with db.acquire() as conn:
        rows = await conn.fetch(f"""
            SELECT id, email, first_name, last_name, company, title,
                   status, verify_status, icp_score, ai_first_line,
                   ai_score, signal_type, created_at
            FROM leads {where}
            ORDER BY icp_score DESC, created_at DESC
            LIMIT {limit} OFFSET {offset}
        """, *params)
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM leads {where}", *params
        )

    return {"leads": [dict(r) for r in rows], "total": total}

# ── Internal helpers ────────────────────────────
async def _hunter_search(domain: str, limit: int) -> list:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.hunter.io/v2/domain-search",
                params={"domain": domain, "limit": limit, "api_key": HUNTER_KEY}
            )
        if resp.status_code != 200:
            return []
        data = resp.json().get("data", {}).get("emails", [])
        return [{
            "email":      e.get("value"),
            "first_name": e.get("first_name"),
            "last_name":  e.get("last_name"),
            "title":      e.get("position"),
            "company":    domain,
            "domain":     domain,
            "confidence": e.get("confidence", 0),
            "linkedin":   e.get("linkedin"),
            "source":     "hunter"
        } for e in data if e.get("value")]
    except:
        return []

async def _apollo_search(domain: str, limit: int) -> list:
    """Apollo.io — use tinlance.com account for 10K/mo free credits"""
    if not APOLLO_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.apollo.io/v1/mixed_people/search",
                headers={"Content-Type": "application/json", "X-Api-Key": APOLLO_KEY},
                json={"q_organization_domains": domain, "page": 1, "per_page": limit}
            )
        if resp.status_code != 200:
            return []
        people = resp.json().get("people", [])
        return [{
            "email":      p.get("email"),
            "first_name": p.get("first_name"),
            "last_name":  p.get("last_name"),
            "title":      p.get("title"),
            "company":    p.get("organization", {}).get("name"),
            "domain":     domain,
            "linkedin":   p.get("linkedin_url"),
            "source":     "apollo"
        } for p in people if p.get("email")]
    except:
        return []

async def _reacher_verify(email: str) -> dict:
    """Reacher — self-hosted on EC2, $0 forever"""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{REACHER_URL}/v0/check_email",
                json={
                    "to_email":    email,
                    "from_email":  "verify@fadereach.tinlance.com",
                    "hello_name":  "fadereach.tinlance.com"
                }
            )
        if resp.status_code != 200:
            return {"is_valid": None, "error": "reacher_unavailable"}

        data = resp.json()
        reachability = data.get("is_reachable", "unknown")
        return {
            "is_valid":     reachability == "safe",
            "reachability": reachability,
            "is_catch_all": data.get("misc", {}).get("is_catch_all", False),
            "is_disposable": data.get("misc", {}).get("is_disposable", False),
            "is_role":      "@" in email and email.split("@")[0] in
                            ["info","noreply","no-reply","admin","support","hello","contact"],
            "smtp":         data.get("smtp", {}),
            "source":       "reacher_self_hosted"
        }
    except:
        return {"is_valid": None, "error": "reacher_unavailable"}

async def _hunter_verify(email: str) -> dict:
    """Hunter.io verifier — fallback"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.hunter.io/v2/email-verifier",
                params={"email": email, "api_key": HUNTER_KEY}
            )
        data = resp.json().get("data", {})
        return {
            "is_valid":  data.get("result") == "deliverable",
            "result":    data.get("result"),
            "score":     data.get("score", 0),
            "source":    "hunter"
        }
    except:
        return {"is_valid": None, "error": "hunter_unavailable"}

async def _generate_single_first_line(lead: dict, product: str, tone: str) -> str:
    """Direct Claude call — used when n8n is unavailable"""
    company    = lead.get("company", "your company")
    first_name = lead.get("first_name", "")
    title      = lead.get("title", "")

    # Try Claude first
    if CLAUDE_KEY:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key":         CLAUDE_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type":      "application/json"
                    },
                    json={
                        "model":      "claude-haiku-4-5-20251001",
                        "max_tokens": 100,
                        "messages": [{
                            "role": "user",
                            "content": f"""Write ONE personalized cold email first line.

Prospect: {first_name}, {title} at {company}
Product being pitched: {product}
Tone: {tone}

Rules:
- Reference something SPECIFIC about their role or company
- Maximum 20 words
- Do NOT start with "I" or "We"
- Sound human, not AI-generated
- No generic phrases like "came across your profile"

Return ONLY the first line, nothing else."""
                        }]
                    }
                )
            data = resp.json()
            return data["content"][0]["text"].strip()
        except:
            pass

    # Fallback: DeepSeek via Ollama (local, $0)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model":  "deepseek-r1:latest",
                    "prompt": f"Write one personalized cold email opener (max 20 words, specific to {company}, pitching {product}). No explanation, just the line.",
                    "stream": False
                }
            )
        return resp.json().get("response", "").strip()
    except:
        pass

    # Final fallback: template
    return f"Noticed {company}'s work in this space — curious how you're handling {product.lower().replace('ai','').strip()} at your scale."

async def _save_first_lines(db, tenant_id: str, results: list):
    """Background: persist generated first lines"""
    async with db.acquire() as conn:
        for r in results:
            if r.get("email") and r.get("ai_first_line"):
                await conn.execute("""
                    UPDATE leads SET ai_first_line=$1, ai_score=80
                    WHERE tenant_id=$2 AND email=$3
                """, r["ai_first_line"], tenant_id, r["email"])
