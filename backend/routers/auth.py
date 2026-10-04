"""FadeReach — Auth Router | Signup · Login · Welcome"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, EmailStr, Field
import bcrypt, jwt, os, json
from datetime import datetime, timedelta

try:
    import nanoid
    def gen_id(): return nanoid.generate(size=12)
except:
    import uuid
    def gen_id(): return uuid.uuid4().hex[:12]

router = APIRouter()
JWT_SECRET   = os.getenv("JWT_SECRET", "")
if os.getenv("ENVIRONMENT") == "production" and len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET must be configured with sufficient entropy")
JWT_EXPIRE_H = 24
RESEND_KEY   = os.getenv("RESEND_API_KEY", "")
APP_URL      = os.getenv("APP_URL", "https://fadereach.tinlance.com")

class SignupReq(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=15, max_length=72)
    company: str | None = None

class LoginReq(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)

def make_token(tenant_id: str, plan: str, ttl_minutes: int = JWT_EXPIRE_H * 60, mfa_verified: bool = False) -> str:
    now = datetime.utcnow()
    return jwt.encode(
        {"sub": tenant_id, "iat": now, "mfa_verified": mfa_verified,
         "exp": now + timedelta(minutes=ttl_minutes),
         "iss": "fadereach", "aud": "fadereach-api"},
        JWT_SECRET, algorithm="HS256"
    )

async def _rate_limit(request: Request, bucket: str, limit: int, window: int) -> None:
    """Fail closed on malformed Redis state, but do not turn Redis outage into auth outage."""
    redis = request.app.state.redis
    key = f"auth_rl:{bucket}"
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window)
        if count > limit:
            raise HTTPException(429, "Too many authentication attempts; try again later")
    except HTTPException:
        raise
    except HTTPException:
        raise
    except Exception as exc:
        # Authentication throttling is a security control. Do not silently
        # bypass it when the backing state store is unavailable.
        raise HTTPException(503, "Authentication rate limiting is temporarily unavailable") from exc


async def send_welcome_email(email: str, name: str):
    """Resend — existing Tinlance KalevioAI account"""
    if not RESEND_KEY:
        return
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_KEY}"},
                json={
                    "from": "Lloyd at FadeReach <hello@fadereach.tinlance.com>",
                    "to": email,
                    "subject": "Your FadeReach workspace is live",
                    "html": f"""
                    <div style="font-family:Inter,sans-serif;max-width:520px;margin:0 auto;color:#1a1a2e">
                    <h2 style="color:#00E5A0">Welcome, {name} ✦</h2>
                    <p>Your FadeReach workspace is setting up — takes about 60 seconds.</p>
                    <p><strong>Your next 3 steps:</strong></p>
                    <ol>
                      <li>Add your first sending domain</li>
                      <li>We check DNS records and guide you through any fixes</li>
                      <li>Warmup starts automatically — you just watch the graph</li>
                    </ol>
                    <p style="margin-top:24px">
                      <a href="{APP_URL}/dashboard"
                         style="background:#00E5A0;color:#000;padding:12px 24px;
                                border-radius:8px;text-decoration:none;font-weight:600">
                        Open dashboard →
                      </a>
                    </p>
                    <p style="margin-top:32px;font-size:13px;color:#666">
                      Questions? Reply to this email.<br>
                      — Lloyd, Tinlance Limited
                    </p>
                    </div>
                    """
                }
            )
    except Exception as e:
        print(f"Welcome email failed: {e}")

async def enqueue_provisioning(db, tenant_id: str, plan: str):
    """Queue provisioning for an isolated worker; never execute host commands in API."""
    async with db.acquire() as conn:
        await conn.execute(
            """INSERT INTO provisioning_jobs (tenant_id, job_type, payload)
               VALUES ($1, 'listmonk', $2::jsonb)""",
            tenant_id,
            json.dumps({
                "plan": plan,
                "tenant_domain": f"{tenant_id}.fadereach.tinlance.com",
            }),
        )


@router.post("/signup")
async def signup(req: SignupReq, background_tasks: BackgroundTasks, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    await _rate_limit(request, f"signup:{client_ip}", 5, 600)
    db = request.app.state.db
    tenant_id = gen_id()
    pw_hash   = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()

    async with db.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM tenants WHERE email=$1", req.email
        )
        if existing:
            raise HTTPException(409, "Email already registered")

        await conn.execute("""
            INSERT INTO tenants (id, email, name, company, password_hash, plan, status)
            VALUES ($1,$2,$3,$4,$5,'trial','trial')
        """, tenant_id, req.email, req.name, req.company, pw_hash)

    background_tasks.add_task(send_welcome_email, req.email, req.name)
    background_tasks.add_task(enqueue_provisioning, db, tenant_id, "trial")

    return {
        "token":         make_token(tenant_id, "trial"),
        "tenant_id":     tenant_id,
        "plan":          "trial",
        "trial_ends_at": (datetime.utcnow() + timedelta(days=14)).isoformat(),
        "message":       "Workspace setting up — ready in ~60 seconds.",
        "next_step":     f"{APP_URL}/onboarding"
    }

@router.post("/login")
async def login(req: LoginReq, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    await _rate_limit(request, f"login:{client_ip}:{req.email.lower()}", 10, 300)
    db = request.app.state.db
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, password_hash, plan, status FROM tenants WHERE email=$1",
            req.email
        )
    if not row:
        raise HTTPException(401, "Invalid email or password")
    if not bcrypt.checkpw(req.password.encode(), row["password_hash"].encode()):
        raise HTTPException(401, "Invalid email or password")
    if row["status"] == "suspended":
        raise HTTPException(403, "Account suspended — contact support@fadereach.tinlance.com")

    async with db.acquire() as conn:
        policy = await conn.fetchrow(
            "SELECT session_ttl_minutes, mfa_required FROM enterprise_settings WHERE tenant_id=$1",
            row["id"],
        )
    ttl_minutes = int(policy["session_ttl_minutes"]) if policy else JWT_EXPIRE_H * 60
    if policy and policy["mfa_required"]:
        raise HTTPException(403, "MFA is required for this workspace; complete the configured enterprise identity flow")

    return {
        "token":     make_token(row["id"], row["plan"], ttl_minutes=ttl_minutes),
        "tenant_id": row["id"],
        "plan":      row["plan"],
        "status":    row["status"]
    }
