# Agency Model

An agency may manage multiple client workspaces while each client remains isolated.

Agency → client workspaces is a management relationship, not automatic cross-tenant data authority.

## Rules
- Agency access must be explicitly granted.
- Client data remains tenant-scoped.
- Provisioning, suspension and role changes are audited.
- Campaign ownership and billing responsibility are explicit.
- Client exports are scoped and logged.
- Ambiguous agency/client mapping fails closed.