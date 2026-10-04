# Disaster Recovery

## Objectives

RPO and RTO are deployment-specific and MUST be declared before making a production availability promise. The application does not claim an SLA merely because backups exist.

## Backup requirements

PostgreSQL backups MUST be:
- automated
- encrypted
- stored independently of the primary host
- retained according to policy
- monitored for success
- periodically restored in a non-production environment

Configuration/secrets recovery MUST be planned separately because restoring a database without the encryption/signing material can make encrypted data or sessions unusable.

## Recovery scenarios

### Host loss
Provision a clean host, restore deployment configuration, restore database, restore secrets, apply compatible application version, validate migrations and run smoke tests.

### Database corruption
Stop risky writes, preserve evidence, identify last known-good backup, restore to isolated environment first, validate integrity, then promote according to incident procedure.

### Credential compromise
Revoke credentials, rotate keys, inspect audit logs, determine affected tenants/actions and restore only if data integrity is uncertain.

## Recovery verification

A recovery drill is successful only when:
- data can be restored
- application can start
- authentication works
- tenant isolation passes
- critical campaign state is coherent
- provider integrations can be re-established
- audit evidence remains usable

## Backup anti-pattern

A successful backup job is not proof of recoverability. Restore testing is mandatory evidence.