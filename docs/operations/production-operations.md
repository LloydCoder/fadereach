# FadeReach Production Operations Runbook

## Deployment

1. Validate the release commit and CI status.
2. Verify required secrets and production environment variables.
3. Create/verify the database backup before schema-affecting releases.
4. Deploy the immutable release artifact.
5. Wait for API readiness and verify frontend readiness.
6. Confirm Alembic is at head.
7. Run ops/smoke_test.sh.
8. Verify outbound queue, suppression, deliverability pause state and metrics.

## Rollback

Rollback the application artifact first when the schema is backward compatible. For irreversible migrations, restore the documented database backup and then deploy the compatible application version. Never improvise a destructive rollback in production.

## Emergency access

Emergency administrative access must be time-bounded, separately audited and removed immediately after the incident. Do not use ordinary tenant credentials for emergency access.

## Incident handling

Classify incidents as security, data integrity, availability, provider/deliverability, or billing. Preserve logs and audit evidence before remediation. Record start time, impact, mitigation, recovery and follow-up actions.

## Provider failure

Pause affected sending domains when delivery or reputation controls degrade. Do not bypass suppression, compliance, or deliverability gates to maintain volume.

## Database incident

Fail closed for outbound execution, preserve the last known backup, verify integrity, restore only after checksum verification, run migrations to head, and execute smoke tests.
