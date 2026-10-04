# FadeReach API Contract

## Contract

The FastAPI application is the authoritative API implementation. Generated OpenAPI is the machine-readable contract; this document defines cross-cutting semantics.

## Authentication and authorization

Every protected endpoint MUST establish authenticated identity, tenant context and authorization before accessing tenant data. Client-supplied tenant identifiers are not trusted as proof of authority.

Authorization is server-side and must combine resource ownership, role/permission and product policy.

## Response semantics

Use conventional HTTP semantics:

- 2xx: successful operation.
- 400: malformed/invalid request.
- 401: missing/invalid authentication.
- 403: authenticated but unauthorized.
- 404: resource not visible or absent, without leaking cross-tenant existence where appropriate.
- 409: state/concurrency conflict.
- 422: validation failure.
- 429: rate limit.
- 5xx: server/provider failure.

Errors SHOULD expose a stable machine-readable code, safe human message and correlation/request identifier. Secrets, tokens and internal stack traces MUST NOT be returned.

## Idempotency

State-changing endpoints that can be retried MUST define idempotency behavior. Provider/webhook events MUST use stable external event identifiers or equivalent deduplication keys.

## Pagination

Collection endpoints SHOULD use bounded pagination and deterministic ordering. Server-side maximum page sizes prevent resource exhaustion.

## Webhooks

Webhook endpoints are documented in [WEBHOOKS](WEBHOOKS.md) and MUST authenticate provider signatures/secrets, validate timestamps where supported, reject malformed events and enforce idempotency.

## Health endpoints

Health endpoints are for operational probing and MUST avoid exposing credentials, database contents or detailed infrastructure information. Liveness and readiness are distinct when implementation supports both.

## Versioning

Breaking API changes require an explicit compatibility plan. Database migrations and API contracts must be coordinated so rolling deployments do not create incompatible intermediate states.

## OpenAPI

CI SHOULD validate that application import and OpenAPI generation remain functional. When adding an endpoint, update endpoint-level documentation and examples where the behavior is operationally important.