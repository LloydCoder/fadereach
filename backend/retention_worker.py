"""Tenant-scoped retention enforcement worker."""

import asyncio
import os

from tenant_context import tenant_id_context

POLL_SECONDS = int(os.getenv("RETENTION_WORKER_POLL_SECONDS", str(24 * 3600)))


async def run_retention_worker(db) -> None:
    while True:
        try:
            await enforce_retention(db)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"Retention worker error: {exc}")
        await asyncio.sleep(POLL_SECONDS)


async def enforce_retention(db) -> None:
    async with db.acquire() as conn:
        tenants = await conn.fetch(
            "SELECT tenant_id, default_retention_days FROM tenant_data_policies"
        )

    for tenant in tenants:
        token = tenant_id_context.set(str(tenant["tenant_id"]))
        try:
            async with db.acquire() as conn:
                # Suppressed contacts are retained as a minimal do-not-contact
                # record; the identifiable prospect record is eligible for purge.
                await conn.execute(
                    """
                    DELETE FROM leads l
                    WHERE l.tenant_id=$1
                      AND l.retention_until <= NOW()
                      AND NOT EXISTS (
                          SELECT 1
                          FROM suppression_entries s
                          WHERE s.tenant_id=l.tenant_id
                            AND lower(s.email)=lower(l.email)
                      )
                    """,
                    tenant["tenant_id"],
                )
                await conn.execute(
                    """
                    DELETE FROM replies r
                    WHERE r.tenant_id=$1
                      AND r.received_at <= NOW() - ($2 || ' days')::interval
                    """,
                    tenant["tenant_id"], tenant["default_retention_days"],
                )
        finally:
            tenant_id_context.reset(token)
