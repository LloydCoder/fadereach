"""Outbound provider connection management and Listmonk execution adapter."""
from urllib.parse import urlparse
import ipaddress
import socket
import os
import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from .deps import get_current_tenant
from audit import record_audit

router = APIRouter()

CREDENTIAL_KEY = os.getenv("CREDENTIAL_ENCRYPTION_KEY", "")


def _fernet() -> Fernet:
    if not CREDENTIAL_KEY:
        raise HTTPException(503, "Credential encryption is not configured")
    try:
        return Fernet(CREDENTIAL_KEY.encode())
    except Exception:
        raise HTTPException(503, "Credential encryption key is invalid")


def _validate_base_url(value: str) -> str:
    parsed = urlparse(value.rstrip("/"))
    if os.getenv("ENVIRONMENT") == "production" and parsed.scheme != "https":
        raise HTTPException(400, "Production provider URLs must use HTTPS")
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(400, "Provider URL must be an absolute HTTP(S) URL")
    hostname = (parsed.hostname or "").lower()
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        raise HTTPException(400, "Loopback provider URLs are not allowed")
    try:
        addresses = {
            info[4][0]
            for info in socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
        }
    except OSError as exc:
        raise HTTPException(400, "Provider hostname could not be resolved") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if any((ip.is_private, ip.is_loopback, ip.is_link_local, ip.is_multicast, ip.is_reserved, ip.is_unspecified)):
            raise HTTPException(400, "Provider URL resolves to a non-public address")
    return value.rstrip("/")


class ListmonkConnectionReq(BaseModel):
    base_url: str
    api_username: str
    api_token: str
    from_email: EmailStr


@router.post("/listmonk")
async def connect_listmonk(
    req: ListmonkConnectionReq,
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    base_url = _validate_base_url(req.base_url)
    # Verify credentials before persisting them.
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            response = await client.get(
                f"{base_url}/api/lists",
                auth=(req.api_username, req.api_token),
                params={"per_page": 1},
            )
        if response.status_code != 200:
            raise HTTPException(400, "Listmonk credentials or URL were rejected")
    except HTTPException:
        raise
    except httpx.HTTPError:
        raise HTTPException(502, "Unable to reach Listmonk provider")

    token = _fernet().encrypt(req.api_token.encode()).decode()
    db = request.app.state.db
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO provider_connections
               (tenant_id, provider_type, base_url, api_username, api_token_ciphertext, from_email)
               VALUES ($1,'listmonk',$2,$3,$4,$5)
               ON CONFLICT (tenant_id, provider_type)
               DO UPDATE SET base_url=EXCLUDED.base_url,
                             api_username=EXCLUDED.api_username,
                             api_token_ciphertext=EXCLUDED.api_token_ciphertext,
                             from_email=EXCLUDED.from_email,
                             status='active', updated_at=NOW()
               RETURNING id""",
            auth["sub"], base_url, req.api_username, token, str(req.from_email),
        )
    await record_audit(db, auth["sub"], auth["sub"], "provider.listmonk.configured", "provider_connection", {"provider_id": row["id"]})
    return {"provider_id": row["id"], "provider": "listmonk", "status": "active"}


@router.get("")
async def list_providers(
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    db = request.app.state.db
    async with db.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, provider_type, base_url, api_username, from_email, status,
                      created_at, updated_at
               FROM provider_connections
               WHERE tenant_id=$1
               ORDER BY created_at DESC""",
            auth["sub"],
        )
    return {"providers": [dict(row) for row in rows]}


async def get_listmonk_connection(db, tenant_id: str) -> dict:
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT id, base_url, api_username, api_token_ciphertext, from_email
               FROM provider_connections
               WHERE tenant_id=$1 AND provider_type='listmonk' AND status='active'""",
            tenant_id,
        )
    if not row:
        raise RuntimeError("No active Listmonk provider is configured")
    try:
        token = _fernet().decrypt(row["api_token_ciphertext"].encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError("Stored provider credential cannot be decrypted") from exc
    return {**dict(row), "api_token": token}
