# Database Operations

Alembic migrations are authoritative. Application startup must not perform implicit schema mutation.

## Production rules
- backup before significant migration
- test migrations against an empty database
- test upgrades on representative data before risky changes
- inspect long-running locks/connections
- keep runtime role least privileged
- maintain RLS protections
- never run destructive SQL casually against production

Recovery follows Disaster Recovery and Incident Response. When integrity is uncertain, validate a restore in isolation before promotion.