# Reliability

Reliability means preserving data integrity, tenant isolation and safe execution under failure.

## Principles
- PostgreSQL is source of truth.
- Retries are idempotent.
- External providers are unreliable dependencies.
- Timeouts are explicit.
- Backpressure prevents unbounded work.
- Poison messages are isolated.
- High-risk outbound execution fails closed.
- Recovery is tested, not assumed.

Do not sacrifice authorization, suppression, audit integrity or data correctness merely to keep sending.