# Security Test Matrix

| Control | Evidence |
|---|---|
| Tenant isolation | RLS + application authorization tests |
| Missing tenant context | fail-closed test |
| Authentication | token/session tests |
| Authorization | role/resource tests |
| Webhooks | invalid/missing/replay tests |
| Secrets | response/log redaction tests |
| Injection | validation/parameterization tests |
| SSRF | URL policy tests |
| Suppression | pre-send blocking test |
| Idempotency | duplicate-event/action tests |
| Supply chain | dependency/CI checks |
| Audit | event creation/access tests |

A control is incomplete until reproducible test or operational evidence exists.