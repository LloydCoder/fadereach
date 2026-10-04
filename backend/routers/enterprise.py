"""Enterprise governance controls: retention, data region, audit and SSO configuration."""
import json
from urllib.parse import urlparse
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from .deps import get_current_tenant
from audit import record_audit

router = APIRouter()

class EnterpriseSettingsReq(BaseModel):
    data_region: str = Field(default="global", min_length=2, max_length=32)
    retention_days: int = Field(default=365, ge=30, le=3650)
    audit_export_enabled: bool = False

class SSOConfigReq(BaseModel):
    issuer: str
    client_id: str
    client_secret: str

def _fernet() -> Fernet:
    key = __import__("os").getenv("CREDENTIAL_ENCRYPTION_KEY", "")
    if not key:
        raise HTTPException(503, "Credential encryption is not configured")
    return Fernet(key.encode())

@router.get("/settings")
async def get_settings(request: Request, auth: dict = Depends(get_current_tenant)):
    db = request.app.state.db
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT data_region, retention_days, audit_export_enabled,
                      sso_enabled, sso_issuer, sso_client_id
               FROM enterprise_settings WHERE tenant_id=$1""",
            auth["sub"],
        )
    return dict(row) if row else {"data_region": "global", "retention_days": 365}

@router.put("/settings")
async def update_settings(req: EnterpriseSettingsReq, request: Request, auth: dict = Depends(get_current_tenant)):
    db = request.app.state.db
    async with db.acquire() as conn:
        await conn.execute(
            """INSERT INTO enterprise_settings
               (tenant_id, data_region, retention_days, audit_export_enabled)
               VALUES ($1,$2,$3,$4)
               ON CONFLICT (tenant_id) DO UPDATE
               SET data_region=EXCLUDED.data_region,
                   retention_days=EXCLUDED.retention_days,
                   audit_export_enabled=EXCLUDED.audit_export_enabled,
                   updated_at=NOW()""",
            auth["sub"], req.data_region, req.retention_days, req.audit_export_enabled,
        )
    await record_audit(db, auth["sub"], auth["sub"], "enterprise.settings.updated", "enterprise_settings", req.model_dump())
    return {"status": "updated"}

@router.put("/sso")
async def configure_sso(req: SSOConfigReq, request: Request, auth: dict = Depends(get_current_tenant)):
    parsed = urlparse(req.issuer)
    if parsed.scheme != "https" or not parsed.netloc:
        raise HTTPException(400, "OIDC issuer must be an HTTPS URL")
    secret = _fernet().encrypt(req.client_secret.encode()).decode()
    db = request.app.state.db
    async with db.acquire() as conn:
        await conn.execute(
            """INSERT INTO enterprise_settings
               (tenant_id, sso_enabled, sso_issuer, sso_client_id, sso_client_secret_ciphertext)
               VALUES ($1,TRUE,$2,$3,$4)
               ON CONFLICT (tenant_id) DO UPDATE
               SET sso_enabled=TRUE, sso_issuer=EXCLUDED.sso_issuer,
                   sso_client_id=EXCLUDED.sso_client_id,
                   sso_client_secret_ciphertext=EXCLUDED.sso_client_secret_ciphertext,
                   updated_at=NOW()""",
            auth["sub"], req.issuer, req.client_id, secret,
        )
    await record_audit(db, auth["sub"], auth["sub"], "enterprise.sso.configured", "sso", {"issuer": req.issuer, "client_id": req.client_id})
    return {"status": "configured", "sso_enabled": True, "issuer": req.issuer}

@router.get("/audit")
async def audit_events(request: Request, limit: int = 100, auth: dict = Depends(get_current_tenant)):
    limit = max(1, min(limit, 500))
    db = request.app.state.db
    async with db.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, actor, action, resource, metadata, ip_address, created_at
               FROM audit_log WHERE tenant_id=$1
               ORDER BY created_at DESC LIMIT $2""",
            auth["sub"], limit,
        )
    return {"events": [dict(row) for row in rows]}

@router.post("/retention/purge")
async def purge_retained_data(request: Request, auth: dict = Depends(get_current_tenant)):
    db = request.app.state.db
    async with db.acquire() as conn:
        settings = await conn.fetchrow(
            "SELECT retention_days FROM enterprise_settings WHERE tenant_id=$1",
            auth["sub"],
        )
        days = settings["retention_days"] if settings else 365
        # Purge only operational event data; core customer records are retained.
        result = await conn.execute(
            """DELETE FROM message_events
               WHERE tenant_id=$1 AND created_at < NOW() - ($2 || ' days')::interval""",
            auth["sub"], days,
        )
    await record_audit(db, auth["sub"], auth["sub"], "enterprise.retention.purge", "message_events", {"retention_days": days, "result": result})
    return {"status": "completed", "retention_days": days}
