"""Agency workspace administration.

The agency tenant remains the control workspace. Client tenants are isolated
application tenants; this API only manages hierarchy and client metadata.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .deps import get_current_tenant

router = APIRouter()


class ClientWorkspaceReq(BaseModel):
    client_name: str = Field(min_length=2, max_length=160)
    client_email: str = Field(min_length=3, max_length=320)
    billing_mode: str = Field(default="client", pattern="^(agency|client|managed)$")


@router.post("/clients")
async def create_client_workspace(
    req: ClientWorkspaceReq,
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    db = request.app.state.db
    agency_id = auth["sub"]
    async with db.acquire() as conn:
        agency = await conn.fetchrow(
            "SELECT tenant_type FROM tenants WHERE id=$1", agency_id
        )
        if not agency or agency["tenant_type"] != "agency":
            raise HTTPException(403, "Current workspace is not configured as an agency")

        client_id = str(uuid.uuid4())
        await conn.execute(
            """
            INSERT INTO tenants (id,email,name,plan,status,tenant_type,parent_tenant_id)
            VALUES ($1,$2,$3,'trial','invited','workspace',$4)
            """,
            client_id, req.client_email.lower(), req.client_name, agency_id,
        )
        await conn.execute(
            """
            INSERT INTO agency_client_settings
                (tenant_id,agency_tenant_id,client_name,billing_mode)
            VALUES ($1,$2,$3,$4)
            """,
            client_id, agency_id, req.client_name, req.billing_mode,
        )
        await conn.execute(
            """
            INSERT INTO workspace_members
                (tenant_id,email,name,role,status,invited_by)
            VALUES ($1,$2,$3,'owner','pending',$4)
            """,
            client_id, req.client_email.lower(), req.client_name, agency_id,
        )
    return {
        "client_tenant_id": client_id,
        "status": "invited",
        "activation": "Client authentication must be activated through the tenant invitation flow.",
    }


@router.get("/clients")
async def list_client_workspaces(
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    db = request.app.state.db
    async with db.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT t.id,t.name,t.email,t.plan,t.status,t.created_at,
                   s.billing_mode,s.reporting_enabled
            FROM tenants t
            JOIN agency_client_settings s ON s.tenant_id=t.id
            WHERE s.agency_tenant_id=$1
            ORDER BY t.created_at DESC
            """,
            auth["sub"],
        )
    return {"clients": [dict(row) for row in rows]}


@router.post("/clients/{client_id}/suspend")
async def suspend_client(
    client_id: str,
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    db = request.app.state.db
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE tenants t
            SET status='suspended'
            FROM agency_client_settings s
            WHERE t.id=$1 AND s.tenant_id=t.id
              AND s.agency_tenant_id=$2
            RETURNING t.id,t.status
            """,
            client_id, auth["sub"],
        )
    if not row:
        raise HTTPException(404, "Client workspace not found")
    return dict(row)
