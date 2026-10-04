# Phase 1 — Canonical Revenue Intelligence Data Model

## Status
**Implementation target:** enterprise-grade canonical commercial lineage.

Phase 1 establishes the durable data spine used by later intelligence, execution,
learning, and revenue phases. Existing FadeReach tables remain supported; the
canonical model is additive and links legacy leads, campaigns, and replies.

## Canonical lineage
`Organization → Account/Person → Event → Observation → Evidence → Signal → Signal Cluster → Opportunity → Hypothesis → Buying Committee → Campaign/Sequence → Message → Execution → Reply/Meeting → Deal → Revenue → Outcome`

The existing `accounts` graph remains the account/operational view. The new
`organizations` entity is the canonical external organization identity.

## Enterprise invariants
- Every canonical entity is tenant-scoped and protected with PostgreSQL RLS.
- Evidence carries source, timestamps, quality/confidence, provenance, and optional content hash.
- Signal and hypothesis claims can be linked to evidence through explicit join tables.
- Outbound executions have tenant-scoped idempotency keys and provider message identity.
- Lifecycle fields use database CHECK constraints rather than UI-only validation.
- Existing legacy tables are not destructively replaced.
- Later phases must preserve the evidence-to-revenue lineage.

## Phase gate
Phase 1 is complete only when:
1. migration chain applies cleanly from an empty database;
2. rollback removes Phase 1 objects cleanly;
3. tenant isolation tests pass for canonical tables;
4. contract tests cover entity presence, lineage, constraints, and legacy compatibility;
5. README/docs/phase-gates identify Phase 1 as implemented;
6. all repository CI jobs are green.

## Research basis
OWASP Top 10:2025 emphasizes access control, software/data integrity, logging/alerting,
and exceptional-condition handling. NIST AI RMF emphasizes trustworthy AI across the
lifecycle. SLSA 1.2 provides current provenance/attestation vocabulary. These are
guardrails for later phases; the data model does not itself claim compliance.
