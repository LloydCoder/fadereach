# Testing Strategy

## Test layers

1. Unit tests for deterministic domain logic.
2. Integration tests for PostgreSQL, Redis and provider adapters.
3. Contract tests for external event/API schemas.
4. Security tests for auth, authorization, tenant isolation, webhook validation and secret handling.
5. Migration tests from an empty database.
6. Frontend production build checks.
7. Compose/configuration validation.
8. Operational smoke tests after deployment.

## Mandatory invariants

- missing tenant context fails closed
- cross-tenant access fails
- suppression blocks execution
- webhook authentication fails closed
- duplicate provider events are idempotent
- invalid campaign transitions fail
- secrets do not appear in responses/logs
- migrations apply from empty state

## CI

The repository CI currently validates backend compilation/import, Alembic migration chain, RLS isolation, backend tests, frontend build, Compose configuration/image builds and shell syntax.

Green CI is a gate, not proof of external production readiness.