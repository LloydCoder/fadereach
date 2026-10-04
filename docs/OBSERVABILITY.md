# Observability

## Three pillars

### Logs
Structured, correlated and redacted. Include timestamp, severity, service, request/correlation ID, tenant-safe context and outcome.

### Metrics
At minimum monitor:
- API availability/error rate/latency
- database availability/connections
- queue depth/failure rate
- worker throughput
- webhook acceptance/rejection
- outbound attempts/success/failure
- bounce/complaint/suppression rates
- campaign state anomalies
- provider health
- disk/CPU/memory

### Traces
Where tracing is available, propagate correlation identifiers across API, worker, provider and webhook flows without placing secrets or message content in trace attributes.

## Alerting

Alerts should represent actionable conditions, not every error. Security alerts include repeated authorization failures, webhook signature failures, unusual outbound volume and provider credential failures.

## Health

Liveness answers whether the process can run. Readiness answers whether it can safely serve the required dependency set.