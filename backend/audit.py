"""Tenant-scoped audit helpers."""
import json
from datetime import datetime

async def record_audit(
    db,
    tenant_id: str,
    actor: str,
    action: str,
    resource: str | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
):
    async with db.acquire() as conn:
        await conn.execute(
            """INSERT INTO audit_log
               (actor, tenant_id, action, resource, metadata, ip_address)
               VALUES ($1,$2,$3,$4,$5::jsonb,$6)""",
            actor, tenant_id, action, resource,
            json.dumps(metadata or {}), ip_address,
        )
