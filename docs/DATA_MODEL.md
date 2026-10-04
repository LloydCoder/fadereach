# FadeReach Data Model

## Principles

PostgreSQL is authoritative. Alembic owns schema evolution. Tenant ownership is explicit. RLS is a database-enforced defense-in-depth control, not a replacement for application authorization.

## Core domains

### Identity and tenancy

- Tenant: customer/organization boundary.
- User: authenticated human identity.
- Role/permission: server-side authorization.
- Membership: user-to-tenant relationship.
- Agency: parent commercial boundary where enabled.
- Client workspace: isolated agency-managed tenant/workspace.

### Intelligence

- Account: target organization.
- Person/contact: business contact associated with an account.
- Signal: observable change/event.
- Evidence: source-backed observation supporting a signal or hypothesis.
- Hypothesis: interpretation about why an account may be ready.
- Fit: evaluated ICP alignment.
- Opportunity: commercially actionable combination of account, evidence, hypothesis and offer.
- Graph entity/event: relationship and temporal state used by the intelligence graph.

### Execution

- Campaign: bounded outbound program.
- Sequence: ordered campaign steps.
- Message: rendered outbound communication.
- Execution: durable attempt to perform a step.
- Provider connection: credential/configuration reference for an outbound system.
- Webhook event: external provider event.
- Suppression: recipient/domain/tenant-level prohibition on contact.

### Learning

- Reply: inbound response.
- Meeting: qualified interaction.
- Opportunity outcome: pipeline progression.
- Revenue attribution: measured commercial outcome linked to campaign/intelligence lineage.
- Experiment: controlled variation with explicit hypothesis and outcome.

### Governance

- Audit event: attributable security/product action.
- Policy: tenant/platform rule.
- Approval: explicit authorization for gated action where required.

## Invariants

1. Every tenant-owned resource has an unambiguous tenant owner.
2. Runtime database access uses the least-privileged application role.
3. Missing tenant context fails closed.
4. Cross-tenant reads/writes are prohibited.
5. Suppression takes precedence over campaign eligibility.
6. Provider events are processed idempotently.
7. Deleting a tenant must not orphan sensitive data without an explicit retention policy.
8. Evidence retains provenance and timestamps.
9. Inference cannot overwrite source evidence.
10. Revenue attribution records preserve lineage to the campaign/action that generated the outcome.

## Sensitive data

Credentials, access tokens, personal contact information, message content, provider payloads and audit data are security-sensitive. Encryption, access control and retention requirements are defined in Security, Secrets Management and Data Governance documentation.

## Migration authority

Schema changes MUST be implemented as reviewed Alembic migrations. Application startup MUST NOT silently mutate production schema.