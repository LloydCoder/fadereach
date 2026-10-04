# Outbound Policy

Every send is subject to deterministic policy checks immediately before execution.

## Minimum checks
- authenticated tenant/user context
- campaign state is executable
- recipient is not suppressed
- required approval exists
- provider connection is valid
- deliverability policy permits sending
- compliance policy permits sending
- rate/budget limits permit sending
- action is idempotently executable

Policy failures are explicit and auditable. AI confidence cannot override a failed policy check.