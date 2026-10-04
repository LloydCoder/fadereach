"""Tenant-aware asyncpg pool wrapper.

RLS is defense in depth: every checked-out application connection receives the
request's authoritative tenant id before application SQL executes. The
application connects with the non-owner runtime role so PostgreSQL actually
enforces the policies.
"""
from __future__ import annotations

from typing import Any

from tenant_context import tenant_id_context


class _TenantAcquire:
    def __init__(self, pool: Any):
        self._pool = pool
        self._connection = None

    async def __aenter__(self):
        self._connection = await self._pool.acquire()
        tenant_id = tenant_id_context.get() or ""
        await self._connection.execute(
            "SELECT set_config('app.tenant_id', $1, false)",
            tenant_id,
        )
        return self._connection

    async def __aexit__(self, exc_type, exc, tb):
        if self._connection is not None:
            try:
                await self._connection.execute(
                    "SELECT set_config('app.tenant_id', '', false)"
                )
            finally:
                await self._pool.release(self._connection)
        return False


class TenantAwarePool:
    """Small proxy preserving the existing pool.acquire() call pattern."""

    def __init__(self, pool: Any):
        self._pool = pool

    def acquire(self, *args, **kwargs):
        if args or kwargs:
            raise TypeError("TenantAwarePool.acquire does not accept pool overrides")
        return _TenantAcquire(self._pool)

    def __getattr__(self, name: str):
        return getattr(self._pool, name)
