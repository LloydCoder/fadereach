"""Public one-click unsubscribe endpoint for marketing messages."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import APIRouter, HTTPException, Query, Request
from tenant_context import tenant_id_context

router = APIRouter()

TOKEN_TTL_SECONDS = int(os.getenv("UNSUBSCRIBE_TOKEN_TTL_SECONDS", str(90 * 86400)))


def _secret() -> bytes:
    value = os.getenv("UNSUBSCRIBE_SECRET") or os.getenv("JWT_SECRET", "")
    if len(value) < 32:
        raise RuntimeError("UNSUBSCRIBE_SECRET/JWT_SECRET must be at least 32 characters")
    return value.encode()


def create_unsubscribe_token(tenant_id: str, email: str) -> str:
    payload = {
        "tenant_id": tenant_id,
        "email": email.strip().lower(),
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    raw = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).rstrip(b"=").decode()
    signature = hmac.new(_secret(), raw.encode(), hashlib.sha256).hexdigest()
    return f"{raw}.{signature}"


def _decode_token(token: str) -> dict:
    try:
        raw, signature = token.split(".", 1)
        expected = hmac.new(_secret(), raw.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        padded = raw + "=" * (-len(raw) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
        if int(payload["exp"]) < int(time.time()):
            raise ValueError
        if not payload["tenant_id"] or not payload["email"]:
            raise ValueError
        return payload
    except Exception as exc:
        raise HTTPException(400, "Invalid or expired unsubscribe token") from exc


async def _suppress(request: Request, token: str):
    payload = _decode_token(token)
    db = request.app.state.db
    token_ctx = tenant_id_context.set(payload["tenant_id"])
    try:
        async with db.acquire() as conn:
            await conn.execute(
            """
            INSERT INTO suppression_entries (tenant_id,email,reason,source)
            VALUES ($1,$2,'one_click_unsubscribe','list-unsubscribe')
            ON CONFLICT (tenant_id,email) DO UPDATE
            SET reason=EXCLUDED.reason, source=EXCLUDED.source
            """,
            payload["tenant_id"], payload["email"],
        )
    finally:
        tenant_id_context.reset(token_ctx)
    return {"unsubscribed": True}


@router.post("/one-click")
async def one_click_unsubscribe(
    request: Request,
    token: str = Query(..., min_length=40, max_length=512),
):
    # RFC 8058 sends a small form body; the token remains in the signed URL.
    return await _suppress(request, token)


@router.get("/one-click")
async def one_click_unsubscribe_get(
    request: Request,
    token: str = Query(..., min_length=40, max_length=512),
):
    return await _suppress(request, token)
