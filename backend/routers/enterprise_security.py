"""Enterprise workspace security settings."""

import ipaddress
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .deps import get_current_tenant

router = APIRouter()


class EnterprisePolicyReq(BaseModel):
    mfa_required: bool = False
    session_ttl_minutes: int = Field(default=60, ge=5, le=1440)
    allowed_ip_cidrs: list[str] = Field(default_factory=list, max_length=50)
    scim_enabled: bool = False
    scim_base_url: str | None = None
    audit_retention_days: int = Field(default=365, ge=30, le=3650)


def _validate_cidrs(values: list[str]) -> list[str]:
    normalized = []
    for value in values:
        try:
            normalized.append(str(ipaddress.ip_network(value, strict=False)))
        except ValueError as exc:
            raise HTTPException(400, f"Invalid CIDR: {value}") from exc
    return sorted(set(normalized))


@router.get("/policy")
async def get_enterprise_policy(
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    db = request.app.state.db
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT tenant_id,mfa_required,session_ttl_minutes,allowed_ip_cidrs,"
            "scim_enabled,scim_base_url,audit_retention_days FROM enterprise_settings "
            "WHERE tenant_id=$1",
            auth["sub"],
        )
    if not row:
        raise HTTPException(404, "Enterprise policy not found")
    return dict(row)


@router.put("/policy")
async def update_enterprise_policy(
    req: EnterprisePolicyReq,
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    cidrs = _validate_cidrs(req.allowed_ip_cidrs)
    db = request.app.state.db
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO enterprise_settings
               (tenant_id,mfa_required,session_ttl_minutes,allowed_ip_cidrs,
                scim_enabled,scim_base_url,audit_retention_days,updated_at)
               VALUES ($1,$2,$3,$4::jsonb,$5,$6,$7,NOW())
               ON CONFLICT (tenant_id) DO UPDATE SET
                   mfa_required=EXCLUDED.mfa_required,
                   session_ttl_minutes=EXCLUDED.session_ttl_minutes,
                   allowed_ip_cidrs=EXCLUDED.allowed_ip_cidrs,
                   scim_enabled=EXCLUDED.scim_enabled,
                   scim_base_url=EXCLUDED.scim_base_url,
                   audit_retention_days=EXCLUDED.audit_retention_days,
                   updated_at=NOW()
               RETURNING tenant_id,mfa_required,session_ttl_minutes,
                         allowed_ip_cidrs,scim_enabled,scim_base_url,
                         audit_retention_days""",
            auth["sub"], req.mfa_required, req.session_ttl_minutes,
            json.dumps(cidrs), req.scim_enabled, req.scim_base_url,
            req.audit_retention_days,
        )
    return dict(row)
