# Phase 2 — Evidence Ledger

Phase 2 turns evidence into an inspectable, tenant-isolated, append-only ledger. Evidence is linked to observations and downstream signals, hypotheses, opportunities, messages, executions and outcomes through explicit lineage relations. Evidence carries source, source reference/URL, observed/collected timestamps, quality, confidence, freshness, content hash and provenance metadata.

The design follows W3C PROV-DM provenance concepts and OWASP Top 10:2025 guidance for integrity-protected audit trails. Runtime roles cannot update or delete ledger history; corrections are represented by new evidence plus explicit supersession or contradiction lineage.

## Phase gate

Migration/rollback, tenant RLS, append-only mutation, lineage contract tests, documentation reconciliation, and all CI workflows must be green on the promoted commit before Phase 3 starts.
