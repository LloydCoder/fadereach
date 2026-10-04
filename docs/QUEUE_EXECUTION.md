# Durable Outbound Execution

Outbound execution must be modeled as durable work rather than a best-effort HTTP request.

## Requirements
- stable execution ID
- idempotency key
- bounded retries
- explicit timeout
- provider response reference
- terminal success/failure state
- dead-letter/manual recovery path
- suppression re-check immediately before send
- audit linkage

A worker crash must not create a second send when the original attempt may have succeeded. Provider-specific idempotency and reconciliation are required where available.