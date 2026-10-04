# FadeReach Phase Gate Ledger

This document is the authoritative repository ledger for the serial F0–F17 enterprise-hardening sequence.

## Gate policy

A phase may be promoted only when all of the following are true:

1. The implementation is present on the branch being promoted.
2. Relevant unit, integration, security, migration, contract, and build checks pass.
3. The required GitHub Actions workflow completes successfully on the **actual promoted commit**.
4. Documentation, configuration, deployment assumptions, and operational behavior reconcile with the implementation.
5. Any explicitly required external validation has been recorded. A green CI run does not substitute for external production evidence.

## Sequence

1. F0 — Forensic reconciliation
2. F1 — Deterministic production foundation
3. F2 — Database and tenancy
4. F3 — Security hardening
5. F4 — Durable outbound execution
6. F5 — Deliverability control plane
7. F6 — Compliance and data governance
8. F7 — Intelligence engine
9. F8 — TADS/SDEA integration
10. F9 — Outbound Intelligence Graph
11. F10 — Campaign Autopilot
12. F11 — Learning and revenue attribution
13. F12 — Agency platform
14. F13 — Enterprise platform
15. F14 — Reliability, observability and disaster recovery
16. F15 — Production operations
17. F16 — Governed autonomous GTM
18. F17 — Final forensic enterprise audit

## Promotion status

| Phase | Repository status | Gate status |
|---|---|---|
| F0 | Implemented/reconciled | Passed historical gate; revalidated by current baseline |
| F1 | Implemented | Passed historical gate; revalidated by current baseline |
| F2 | Implemented | Merged and historically CI-green |
| F3 | Implemented | Merged and historically CI-green |
| F4 | Implemented | Merged and historically CI-green |
| F5 | Implemented | Merged and historically CI-green |
| F6 | Implemented | Merged and historically CI-green |
| F7 | Implemented | Revalidated by current CI baseline |
| F8 | Implemented | Revalidated by current CI baseline |
| F9 | Implemented | Revalidated by current CI baseline |
| F10 | Implemented | Revalidated by current CI baseline |
| F11 | Implemented | Revalidated by current CI baseline |
| F12 | Implemented | Revalidated by current CI baseline |
| F13 | Implemented | Revalidated by current CI baseline |
| F14 | Implemented | Merged and historically CI-green |
| F15 | Implemented | Merged and historically CI-green |
| F16 | Implemented as bounded/fail-closed autonomy contract | **Requires main-branch CI on the promoted commit and external Agent Platform delegation validation** |
| F17 | Final forensic audit documentation and reconciliation | **Runs only after F16 gate is satisfied** |

## Current promotion evidence

F16 PR #45 was merged into `main` on 2026-10-04. The PR head commit passed the FadeReach CI workflow before merge.

The F16 merge commit is the authoritative promotion candidate. Its required workflow run must be verified before F16 is marked green. The F17 documentation reconciliation is now merged; repository-level F17 acceptance remains conditional on this promoted-commit workflow and the explicit external Agent Platform delegation validation.

## Important distinction

"Implemented", "CI-green", "externally validated", and "production-ready" are separate states.

A repository may be technically complete while still requiring live provider, infrastructure, Agent Platform, DNS, deliverability, restore, or customer validation. This ledger never collapses those distinctions.
