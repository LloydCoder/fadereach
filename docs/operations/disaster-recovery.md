# FadeReach Reliability, Backup and Disaster Recovery Runbook

## Service health

- Liveness: GET /api/health
- Readiness: GET /api/ready
- Metrics: GET /internal/metrics (protect with METRICS_TOKEN when exposed beyond localhost/private networking)

## Backup

Run ops/backup_postgres.sh from the host with POSTGRES_PASSWORD and a writable BACKUP_DIR.

Backups are written atomically, permissions are restricted, and a SHA-256 sidecar is produced.

Recommended production policy:
- daily full backup;
- retain multiple daily/weekly generations;
- copy backups to a separate failure domain/object store;
- encrypt backups at rest;
- periodically test restore rather than assuming backups are usable.

## Restore

Run ops/restore_postgres.sh with a verified BACKUP_FILE. The script verifies the checksum and requires an explicit RESTORE confirmation.

After restore:
1. run Alembic to head;
2. verify RLS and runtime/worker roles;
3. verify readiness;
4. verify outbound queue state;
5. verify suppression and compliance data;
6. perform a controlled application smoke test.

## Recovery objectives

RPO/RTO values are deployment-specific and must be measured against the selected backup/object-storage schedule. Do not document a numeric SLA until a restore drill has demonstrated it.

## Failure classes

- PostgreSQL unavailable: fail closed; no outbound execution.
- Redis unavailable: authentication throttling and rate-limit controls fail closed where configured.
- Listmonk unavailable: outbound jobs retry through the durable queue; no duplicate campaign should be created because campaign identity is deterministic.
- Provider/API 429/5xx: retry with backoff and preserve execution state.
- Application crash: stale jobs are reclaimable and attempts are counted.
- Sending domain degraded: domain/campaign send controls pause before provider submission.
