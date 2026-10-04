"""Request-local tenant context used to bind PostgreSQL sessions to RLS.

The context is deliberately separate from JWT claims. Authentication resolves
the authoritative tenant, then the database pool setup hook copies that
tenant id into PostgreSQL's session-local app.tenant_id setting.
"""
from contextvars import ContextVar

tenant_id_context: ContextVar[str | None] = ContextVar(
    "fadereach_tenant_id", default=None
)
