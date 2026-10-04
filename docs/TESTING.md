# Testing Strategy

## Layers
1. Unit tests for deterministic domain logic.
2. Integration tests for PostgreSQL, Redis and provider adapters.
3. Contract tests for APIs and external events.
4. Security tests for authentication, authorization, tenancy, webhooks and secrets.
5. Migration tests from an empty database.
6. Frontend production build checks.
7. Compose/configuration validation.
8. Deployment smoke tests.

## Mandatory invariants
- missing tenant context fails closed
- cross-tenant access fails
- suppression blocks execution
- webhook authentication fails closed
- duplicate provider events are idempotent
- invalid campaign transitions fail
- secrets do not appear in responses/logs
- migrations apply from empty state

Green CI is a gate, not proof of external production readiness.