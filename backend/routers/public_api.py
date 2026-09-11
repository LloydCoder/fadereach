"""
FadeReach — Public API
Third-party integrations · API key management
Rate limiting · OpenAPI-ready

Endpoints available to Agency+ plan tenants.
Used by: external CRMs, Zapier, Make, custom workflows.
"""
from fastapi import APIRouter, HTTPException, Request, Depends, Header
from pydantic import BaseModel
from .deps import get_current_tenant
from middleware.plan_enforcement import enforce_feature_flag
import secrets, hashlib, json
from datetime import datetime
from typing import Optional

router = APIRouter()

class APIKeyCreateReq(BaseModel):
    name:        str
    description: Optional[str] = None
    scopes:      list[str] = ["leads:read", "campaigns:read"]

VALID_SCOPES = [
    "leads:read", "leads:write",
    "campaigns:read", "campaigns:write",
    "inbox:read",
    "analytics:read",
    "opportunities:read",
    "domains:read",
    "webhooks:write",
]

async def get_api_tenant(
    request: Request,
    x_api_key: str = Header(None, alias="X-API-Key")
):
    """
    Authenticate via API key (for external integrations)
    Separate from JWT auth — API key persists across sessions
    """
    if not x_api_key:
        raise HTTPException(401, "API key required. Pass as X-API-Key header.")

    redis = request.app.state.redis
    db    = request.app.state.db

    # Hash the key for lookup (never store raw keys)
    key_hash  = hashlib.sha256(x_api_key.encode()).hexdigest()
    cache_key = f"apikey:{key_hash}"

    # Check Redis cache first
    cached = await redis.get(cache_key)
    if cached:
        key_data = json.loads(cached)
        if key_data.get("active"):
            # Rate limit check
            rl_key = f"apikey_rl:{key_hash}:{datetime.utcnow().strftime('%Y-%m-%dT%H')}"
            calls  = await redis.incr(rl_key)
            await redis.expire(rl_key, 3600)
            if calls > 1000:  # 1000 calls/hour per API key
                raise HTTPException(429, "API rate limit exceeded (1000 calls/hour)")
            return key_data

    # Lookup in DB
    async with db.acquire() as conn:
        key_record = await conn.fetchrow("""
            SELECT ak.tenant_id, ak.scopes, ak.active, ak.name,
                   t.plan, t.status
            FROM api_keys ak
            JOIN tenants t ON ak.tenant_id = t.id
            WHERE ak.key_hash = $1
        """, key_hash)

    if not key_record:
        raise HTTPException(401, "Invalid API key")
    if not key_record["active"]:
        raise HTTPException(401, "API key is disabled")
    if key_record["status"] == "suspended":
        raise HTTPException(403, "Account suspended")

    key_data = {
        "tenant_id": key_record["tenant_id"],
        "scopes":    json.loads(key_record["scopes"]),
        "plan":      key_record["plan"],
        "name":      key_record["name"],
        "active":    True,
    }

    # Cache for 5 minutes
    await redis.setex(cache_key, 300, json.dumps(key_data))

    # Update last used
    async with db.acquire() as conn:
        await conn.execute(
            "UPDATE api_keys SET last_used=NOW() WHERE key_hash=$1", key_hash
        )

    return key_data

# ── API Key Management ──────────────────────────
@router.post("/keys")
async def create_api_key(
    req:     APIKeyCreateReq,
    request: Request,
    auth:    dict = Depends(get_current_tenant),
):
    """Create a new API key (Agency plan required)"""
    db   = request.app.state.db
    plan = auth.get("plan", "trial")

    await enforce_feature_flag(plan, "api_access", "API Access")

    # Validate scopes
    invalid = [s for s in req.scopes if s not in VALID_SCOPES]
    if invalid:
        raise HTTPException(400, f"Invalid scopes: {invalid}. Valid: {VALID_SCOPES}")

    # Generate key
    raw_key  = f"fr_{'live' if plan != 'trial' else 'test'}_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    async with db.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id         SERIAL PRIMARY KEY,
                tenant_id  TEXT REFERENCES tenants(id) ON DELETE CASCADE,
                name       TEXT NOT NULL,
                description TEXT,
                key_hash   TEXT UNIQUE NOT NULL,
                key_prefix TEXT NOT NULL,
                scopes     JSONB NOT NULL,
                active     BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                last_used  TIMESTAMPTZ
            );
        """)

        # Limit to 5 API keys per tenant
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM api_keys WHERE tenant_id=$1 AND active=TRUE",
            auth["sub"]
        )
        if count >= 5:
            raise HTTPException(400, "Maximum 5 active API keys per account")

        key_id = await conn.fetchval("""
            INSERT INTO api_keys
            (tenant_id, name, description, key_hash, key_prefix, scopes)
            VALUES ($1,$2,$3,$4,$5,$6) RETURNING id
        """, auth["sub"], req.name, req.description,
            key_hash, raw_key[:12] + "...",
            json.dumps(req.scopes))

    return {
        "key_id":    key_id,
        "api_key":   raw_key,  # Only shown once — never retrievable again
        "key_prefix":raw_key[:12] + "...",
        "scopes":    req.scopes,
        "warning":   "Save this key now. It will never be shown again.",
    }

@router.get("/keys")
async def list_api_keys(
    request: Request,
    auth:    dict = Depends(get_current_tenant),
):
    """List API keys (without revealing the actual keys)"""
    db = request.app.state.db
    await enforce_feature_flag(auth.get("plan","trial"), "api_access", "API Access")

    async with db.acquire() as conn:
        keys = await conn.fetch("""
            SELECT id, name, description, key_prefix, scopes, active, created_at, last_used
            FROM api_keys WHERE tenant_id=$1 ORDER BY created_at DESC
        """, auth["sub"])

    return {"api_keys": [dict(k) for k in keys]}

@router.delete("/keys/{key_id}")
async def revoke_api_key(
    key_id:  int,
    request: Request,
    auth:    dict = Depends(get_current_tenant),
):
    """Revoke an API key"""
    db = request.app.state.db
    async with db.acquire() as conn:
        result = await conn.fetchrow(
            "UPDATE api_keys SET active=FALSE WHERE id=$1 AND tenant_id=$2 RETURNING id",
            key_id, auth["sub"]
        )
    if not result:
        raise HTTPException(404, "API key not found")
    return {"revoked": True, "key_id": key_id}

# ── External API Endpoints ──────────────────────
# These are called by external systems using X-API-Key

@router.get("/v1/leads")
async def api_list_leads(
    request:  Request,
    limit:    int = 50,
    offset:   int = 0,
    status:   Optional[str] = None,
    api_auth: dict = Depends(get_api_tenant),
):
    """[API] List leads"""
    if "leads:read" not in api_auth["scopes"]:
        raise HTTPException(403, "Scope 'leads:read' required")

    db = request.app.state.db
    async with db.acquire() as conn:
        where  = "WHERE tenant_id=$1"
        params = [api_auth["tenant_id"]]
        if status:
            where += " AND status=$2"
            params.append(status)

        leads = await conn.fetch(
            f"SELECT id,email,first_name,last_name,company,title,status,"
            f"icp_score,ai_first_line,created_at FROM leads {where} "
            f"ORDER BY created_at DESC LIMIT {limit} OFFSET {offset}",
            *params
        )
    return {"leads": [dict(l) for l in leads], "limit": limit, "offset": offset}

@router.post("/v1/leads")
async def api_create_lead(
    lead:     dict,
    request:  Request,
    api_auth: dict = Depends(get_api_tenant),
):
    """[API] Create a lead"""
    if "leads:write" not in api_auth["scopes"]:
        raise HTTPException(403, "Scope 'leads:write' required")

    db = request.app.state.db
    email = lead.get("email", "")
    if not email or "@" not in email:
        raise HTTPException(400, "Valid email required")

    async with db.acquire() as conn:
        lead_id = await conn.fetchval("""
            INSERT INTO leads
            (tenant_id, email, first_name, last_name, company,
             title, domain, signal_type)
            VALUES ($1,$2,$3,$4,$5,$6,$7,'api_import')
            ON CONFLICT DO NOTHING
            RETURNING id
        """, api_auth["tenant_id"], email,
            lead.get("first_name"), lead.get("last_name"),
            lead.get("company"), lead.get("title"), lead.get("domain"))

    return {"lead_id": lead_id, "email": email, "created": bool(lead_id)}

@router.get("/v1/campaigns")
async def api_list_campaigns(
    request:  Request,
    api_auth: dict = Depends(get_api_tenant),
):
    """[API] List campaigns"""
    if "campaigns:read" not in api_auth["scopes"]:
        raise HTTPException(403, "Scope 'campaigns:read' required")

    db = request.app.state.db
    async with db.acquire() as conn:
        campaigns = await conn.fetch("""
            SELECT id,name,subject,status,product,emails_sent,
                   replies,bounce_rate,reply_rate,created_at
            FROM campaigns WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT 50
        """, api_auth["tenant_id"])
    return {"campaigns": [dict(c) for c in campaigns]}

@router.get("/v1/inbox")
async def api_list_replies(
    request:  Request,
    is_hot:   Optional[bool] = None,
    api_auth: dict = Depends(get_api_tenant),
):
    """[API] List inbox replies"""
    if "inbox:read" not in api_auth["scopes"]:
        raise HTTPException(403, "Scope 'inbox:read' required")

    db        = request.app.state.db
    where     = "WHERE tenant_id=$1"
    params    = [api_auth["tenant_id"]]
    if is_hot is not None:
        where += " AND is_hot=$2"
        params.append(is_hot)

    async with db.acquire() as conn:
        replies = await conn.fetch(
            f"SELECT id,from_email,subject,intent,sentiment,is_hot,received_at "
            f"FROM replies {where} ORDER BY received_at DESC LIMIT 50",
            *params
        )
    return {"replies": [dict(r) for r in replies]}

@router.get("/v1/analytics")
async def api_analytics(
    request:  Request,
    api_auth: dict = Depends(get_api_tenant),
):
    """[API] Get analytics overview"""
    if "analytics:read" not in api_auth["scopes"]:
        raise HTTPException(403, "Scope 'analytics:read' required")

    db = request.app.state.db
    async with db.acquire() as conn:
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*)             as campaigns,
                SUM(emails_sent)     as emails_sent,
                SUM(replies)         as replies,
                SUM(bounces)         as bounces,
                CASE WHEN SUM(emails_sent) > 0
                     THEN ROUND(SUM(replies)::numeric/SUM(emails_sent)*100,2)
                     ELSE 0 END as reply_rate
            FROM campaigns WHERE tenant_id=$1
        """, api_auth["tenant_id"])
    return dict(stats)

@router.get("/v1/docs")
async def api_docs(auth: dict = Depends(get_current_tenant)):
    """Public API documentation"""
    return {
        "version":  "1.0.0",
        "base_url": "https://fadereach.tinlance.com/api/public/v1",
        "auth":     "Pass API key as X-API-Key header",
        "rate_limit":"1000 requests/hour per API key",
        "scopes":    VALID_SCOPES,
        "endpoints": [
            {"method":"GET",  "path":"/leads",           "scope":"leads:read",      "description":"List leads"},
            {"method":"POST", "path":"/leads",            "scope":"leads:write",     "description":"Create lead"},
            {"method":"GET",  "path":"/campaigns",        "scope":"campaigns:read",  "description":"List campaigns"},
            {"method":"GET",  "path":"/inbox",            "scope":"inbox:read",      "description":"List replies"},
            {"method":"GET",  "path":"/analytics",        "scope":"analytics:read",  "description":"Analytics overview"},
            {"method":"GET",  "path":"/docs",             "scope":"none",            "description":"This documentation"},
        ],
        "integration_examples": {
            "zapier":    "Use webhook trigger with X-API-Key header",
            "make":      "HTTP module → Custom request → X-API-Key header",
            "n8n":       "HTTP Request node → Headers: X-API-Key",
            "curl":      "curl -H 'X-API-Key: fr_live_...' https://fadereach.tinlance.com/api/public/v1/leads",
        }
    }
