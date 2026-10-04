"""Request-local tenant context used by the database pool.

Authentication resolves the authoritative tenant first. The tenant-aware pool
then copies that value into PostgreSQL's app.tenant_id setting for every
checked-out connection. The context itself is never taken from client input.
"""
from contextvars import ContextVar

tenant_id_context: ContextVar[str | None] = ContextVar(
    "fadereach_tenant_id", default=None
)
