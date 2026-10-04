# Change Management

Material changes require impact assessment across code, database, security, operations, compliance and documentation.

## Classes
- Standard: routine low-risk change with established tests.
- Significant: architecture, schema, provider, auth or outbound-control change.
- Emergency: active incident/security/reliability remediation.

Significant changes require rollback and operational considerations. Emergency changes require retrospective documentation and test coverage as soon as practical.

The PR that changes behavior owns the documentation update. Stale documentation is a defect, not a later cleanup task.