# Data Governance

## Classification
- Restricted: credentials, encryption material, signing/session secrets.
- Confidential: tenant/contact data, campaign content, provider payloads, audit/security data and commercial outcomes.
- Internal: operational metadata and engineering configuration.
- Public: intentionally published product/documentation content.

## Lifecycle
Collect minimally → establish provenance/purpose → authorized use → retention → suppression/deletion/export.

Where personal data is processed, design supports data minimization, purpose limitation, accuracy, storage limitation, integrity/confidentiality and accountability.

Retention periods must be defined per category and applicable contractual/legal requirements. Exports must be authorized, tenant-scoped and audited. Deletion must stop operational use while respecting documented legal holds and backup-retention constraints.