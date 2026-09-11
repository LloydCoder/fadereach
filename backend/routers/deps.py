"""FadeReach — Shared dependencies"""
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt, os

JWT_SECRET = os.getenv("JWT_SECRET", "change-in-production")
security   = HTTPBearer()

async def get_current_tenant(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    try:
        payload = jwt.decode(
            credentials.credentials, JWT_SECRET, algorithms=["HS256"]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Session expired — please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Lloyd-only admin routes"""
    ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")
    if credentials.credentials != ADMIN_SECRET:
        raise HTTPException(403, "Admin access required")
    return {"role": "admin"}
