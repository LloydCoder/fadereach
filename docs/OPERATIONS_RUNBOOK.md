# Operations Runbook

## First response

1. Identify affected component.
2. Determine whether data loss or unauthorized sending is possible.
3. Stop high-risk outbound execution if necessary.
4. Preserve logs/audit evidence.
5. Check health, resource pressure and recent deployment.
6. Roll back only after compatibility is understood.

## API unhealthy

- inspect container status/logs
- inspect database/Redis connectivity
- inspect recent deployment
- verify environment/secret availability
- test health endpoint
- restore previous known-good image if release-induced

## Database unhealthy

- stop risky migrations/writes
- inspect disk, connections and locks
- verify backup availability
- do not delete data to make a health check green
- escalate to recovery procedure if integrity is uncertain

## Queue/worker backlog

- inspect queue depth and failure rate
- identify poison messages
- pause new campaign execution if backlog threatens rate/deliverability limits
- retry only idempotent work
- preserve failed payload references safely

## Outbound anomaly

Immediately pause affected campaign/provider if unauthorized or unexpectedly high volume is suspected. Validate suppression, campaign state, provider credentials and recent configuration changes before resuming.

## Certificate/DNS incident

Verify authoritative DNS, certificate expiry, edge configuration and provider records. Do not rotate unrelated credentials while diagnosing a DNS-only failure.

## Every operational change

Record who, what, why, when, affected tenant/system, result and rollback/recovery decision.