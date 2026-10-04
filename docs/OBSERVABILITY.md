# Observability

## Three pillars
**Logs:** structured, correlated and redacted; include timestamp, severity, service, request/correlation ID, tenant-safe context and outcome.
**Metrics:** API availability/error/latency, database availability/connections, queue depth/failures, worker throughput, webhook acceptance/rejection, outbound success/failure, bounce/complaint/suppression, campaign anomalies, provider health and host resources.
**Traces:** propagate correlation identifiers across API, worker, provider and webhook flows without secrets or message content.

## Alerting
Alerts must be actionable. Security alerts include repeated authorization failures, webhook signature failures, abnormal outbound volume and provider credential failures.

## Health
Liveness means the process can run. Readiness means required dependencies permit safe service.