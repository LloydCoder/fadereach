"""Tenant data governance endpoints.

These controls provide configurable retention/provenance metadata and
data-subject export/erasure primitives. They are not a blanket statement of
legal compliance; customers remain responsible for their applicable laws and
lawful-basis decisions.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, HttpUrl

from .deps import get_current_tenant

router = APIRouter()


class DataPolicyReq(BaseModel):
    default_retention_days: int = Field(default=180, ge=1, le=3650)
    default_lawful_basis: str | None = Field(default=None, max_length=64)
    marketing_purpose: str = Field(default="outbound_prospecting", min_length=3, max_length=128)
    privacy_notice_url: HttpUrl | None = None


class DataSubjectReq(BaseModel):
    email: str = Field(min_length=3, max_length=320)


@router.get("/policy")
async def get_policy(request: Request, auth: dict = Depends(get_current_tenant)):
    db = request.app.state.db
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM tenant_data_policies WHERE tenant_id=$1",
            auth["sub"],
        )
    return dict(row) if row else {
        "tenant_id": auth["sub"],
        "default_retention_days": 180,
        "default_lawful_basis": None,
        "marketing_purpose": "outbound_prospecting",
        "privacy_notice_url": None,
    }


@router.put("/policy")
async def set_policy(
    req: DataPolicyReq,
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    db = request.app.state.db
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO tenant_data_policies
                (tenant_id,default_retention_days,default_lawful_basis,
                 marketing_purpose,privacy_notice_url,updated_at)
            VALUES ($1,$2,$3,$4,$5,NOW())
            ON CONFLICT (tenant_id) DO UPDATE SET
                default_retention_days=EXCLUDED.default_retention_days,
                default_lawful_basis=EXCLUDED.default_lawful_basis,
                marketing_purpose=EXCLUDED.marketing_purpose,
                privacy_notice_url=EXCLUDED.privacy_notice_url,
                updated_at=NOW()
            RETURNING *
            """,
            auth["sub"], req.default_retention_days,
            req.default_lawful_basis, req.marketing_purpose,
            str(req.privacy_notice_url) if req.privacy_notice_url else None,
        )
    return dict(row)


@router.post("/export")
async def export_data_subject(
    req: DataSubjectReq,
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    db = request.app.state.db
    email = req.email.strip().lower()
    async with db.acquire() as conn:
        lead = await conn.fetch(
            """
            SELECT id,email,first_name,last_name,company,title,domain,status,
                   source,source_url,lawful_basis,processing_purpose,
                   collected_at,retention_until,created_at
            FROM leads
            WHERE tenant_id=$1 AND lower(email)=lower($2)
            """,
            auth["sub"], email,
        )
        replies = await conn.fetch(
            """
            SELECT id,campaign_id,from_email,subject,intent,sentiment,
                   is_hot,is_read,received_at
            FROM replies
            WHERE tenant_id=$1 AND lower(from_email)=lower($2)
            """,
            auth["sub"], email,
        )
        suppressions = await conn.fetch(
            """
            SELECT email,reason,source,created_at
            FROM suppression_entries
            WHERE tenant_id=$1 AND lower(email)=lower($2)
            """,
            auth["sub"], email,
        )
    return {
        "tenant_id": auth["sub"],
        "email": email,
        "leads": [dict(row) for row in lead],
        "replies": [dict(row) for row in replies],
        "suppressions": [dict(row) for row in suppressions],
    }


@router.post("/erase")
async def erase_data_subject(
    req: DataSubjectReq,
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    email = req.email.strip().lower()
    db = request.app.state.db
    async with db.acquire() as conn:
        # Preserve the suppression record so an erased prospect cannot be
        # re-imported and contacted accidentally.
        deleted_leads = await conn.fetchval(
            """
            WITH deleted AS (
                DELETE FROM leads
                WHERE tenant_id=$1 AND lower(email)=lower($2)
                RETURNING id
            )
            SELECT COUNT(*) FROM deleted
            """,
            auth["sub"], email,
        )
        deleted_replies = await conn.fetchval(
            """
            WITH deleted AS (
                DELETE FROM replies
                WHERE tenant_id=$1 AND lower(from_email)=lower($2)
                RETURNING id
            )
            SELECT COUNT(*) FROM deleted
            """,
            auth["sub"], email,
        )
        await conn.execute(
            """
            INSERT INTO suppression_entries (tenant_id,email,reason,source)
            VALUES ($1,$2,'data_subject_erasure','privacy_request')
            ON CONFLICT (tenant_id,email) DO UPDATE
            SET reason=EXCLUDED.reason, source=EXCLUDED.source
            """,
            auth["sub"], email,
        )
    return {
        "erased": True,
        "email": email,
        "deleted_leads": int(deleted_leads or 0),
        "deleted_replies": int(deleted_replies or 0),
        "suppression_preserved": True,
    }
