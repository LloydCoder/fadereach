# Production Readiness

Production promotion requires:
- implementation merged to the promoted branch
- required CI green on the actual promoted commit
- migrations validated
- secrets/configuration verified
- tenant isolation verified
- backup and restore evidence available
- DNS/TLS/provider readiness verified
- suppression and deliverability controls verified
- health/logging/monitoring active
- rollback/recovery understood
- documentation reconciled

A green GitHub workflow alone is insufficient evidence for external production readiness.