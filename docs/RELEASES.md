# Release Management

A release is a coordinated application, database, infrastructure and documentation change.

## Required checks
1. CI green on the exact promoted commit.
2. Migration path verified from empty database.
3. Rolling compatibility considered.
4. Configuration/secrets validated.
5. Security-sensitive changes reviewed.
6. Documentation reconciled.
7. Rollback/recovery understood.

Application rollback does not imply database rollback. Prefer forward-compatible migrations.

Emergency security/availability changes retain auditability and require retrospective documentation and tests.