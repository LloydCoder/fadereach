# Integration Contracts

External integrations are untrusted dependencies.

Every integration contract defines authentication, tenant mapping, schemas, idempotency, retries, timeout, rate limits, error mapping, secret handling, audit behavior, versioning and degraded behavior.

Integration-specific contracts live under docs/integrations/.