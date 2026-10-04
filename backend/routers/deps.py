"""Shared authentication and tenant authorization dependencies."""
import os
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

JWT_SECRET = os.getenv("JWT_SECRET", "")
if os.getenv("ENVIRONMENT") == "production" and len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET must be configured with sufficient entropy")

security = HTTPBearer(auto_error=True)

async def get_current_tenant(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Session expired — please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

    tenant_id = payload.get("sub")
    if not tenant_id:
        raise HTTPException(401, "Invalid session")

    async with request.app.state.db.acquire() as conn:
        tenant = await conn.fetchrow(
            "SELECT id, email, name, plan, status, trial_ends_at FROM tenants WHERE id=$1",
            tenant_id,
        )

    if not tenant:
        raise HTTPException(401, "Workspace not found")
    if tenant["status"] == "suspended":
        raise HTTPException(403, "Workspace suspended")
    if tenant["status"] == "trial_expired":
        raise HTTPException(403, "Trial expired — upgrade to continue")

    # Plan/status are authoritative database state. JWT claims are session
    # identity only and are deliberately not trusted for authorization.
    return dict(tenant)

async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    admin_secret = os.getenv("ADMIN_SECRET", "")
    if not admin_secret or not credentials.credentials:
        raise HTTPException(403, "Admin access required")
    if not __import__("hmac").compare_digest(credentials.credentials, admin_secret):
        raise HTTPException(403, "Admin access required")
    return {"role": "admin"}
