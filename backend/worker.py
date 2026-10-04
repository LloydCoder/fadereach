"""Dedicated FadeReach worker process.

API containers serve HTTP only. This process owns durable outbound execution
and retention enforcement so horizontal API scaling cannot multiply workers.
"""
from __future__ import annotations

import asyncio
import os

import asyncpg
import redis.asyncio as aioredis

from db import TenantAwarePool
from outbound_worker import run_outbound_worker
from retention_worker import run_retention_worker

DB_URL = os.getenv("DATABASE_URL")
WORKER_DB_URL = os.getenv("WORKER_DATABASE_URL") or DB_URL
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

if not DB_URL:
    raise RuntimeError("DATABASE_URL must be configured")
if not WORKER_DB_URL:
    raise RuntimeError("WORKER_DATABASE_URL must be configured")


async def main() -> None:
    app_pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=5)
    queue_pool = await asyncpg.create_pool(WORKER_DB_URL, min_size=1, max_size=3)
    redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
    tenant_pool = TenantAwarePool(app_pool)

    outbound = asyncio.create_task(run_outbound_worker(tenant_pool, queue_pool))
    retention = asyncio.create_task(run_retention_worker(tenant_pool, queue_pool))
    try:
        await asyncio.gather(outbound, retention)
    finally:
        for task in (outbound, retention):
            task.cancel()
        await asyncio.gather(outbound, retention, return_exceptions=True)
        await redis.close()
        await queue_pool.close()
        await app_pool.close()


if __name__ == "__main__":
    asyncio.run(main())
