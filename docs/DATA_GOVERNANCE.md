# Data Governance

## Classification

### Restricted
Credentials, encryption material, session/signing secrets.

### Confidential
Tenant data, contact data, campaign content, provider payloads, audit/security data and commercial outcomes.

### Internal
Operational metadata and non-sensitive engineering configuration.

### Public
Published documentation and intentionally public product information.

## Lifecycle

Collect minimally → establish provenance/purpose → use for authorized purpose → retain only as required → suppress/delete/export according to policy.

## Personal data

Where personal data is processed, the system design supports data minimization, purpose limitation, accuracy, storage limitation, integrity/confidentiality and accountability.

## Retention

Retention periods MUST be configurable by data category and applicable contractual/legal requirements. Deletion must account for derived indexes, caches, backups and audit requirements.

## Export/deletion

Exports must be authorized, scoped to the tenant and logged. Deletion must prevent continued operational use while respecting documented legal holds and backup-retention constraints.