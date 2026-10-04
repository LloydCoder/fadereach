# FadeReach Documentation

This directory is the normative engineering and operational documentation for FadeReach, Tinlance's AI outbound intelligence and revenue-execution platform.

## Documentation contract

Documentation is part of the production surface. A change is incomplete when implementation, tests, security controls, deployment assumptions, operational behavior, and documentation disagree.

**Normative language:** MUST/SHOULD/MAY are used in their conventional requirements sense. Legal and provider requirements are external constraints; this repository does not represent legal advice or guarantee deliverability.

## System boundary

FadeReach owns outbound intelligence, campaign control, tenant/application state, provider adapters, deliverability controls, audit semantics, outcomes and revenue learning. Tinlance Agent Platform and Agent OS remain separate governed execution/workspace systems. FadeReach integrates with them instead of duplicating their authority, sandbox, policy, audit or runtime responsibilities.

TADS and SDEA provide upstream demand/account intelligence. FadeReach converts validated signals and evidence into controlled outbound actions. FDSE/FDE consumes qualified commercial outcomes downstream.

## Reading order

1. [Architecture](ARCHITECTURE.md)
2. [Data Model](DATA_MODEL.md)
3. [API](API.md)
4. [Security](SECURITY.md)
5. [Threat Model](THREAT_MODEL.md)
6. [Secrets Management](SECRETS_MANAGEMENT.md)
7. [Audit Logging](AUDIT_LOGGING.md)
8. [Configuration](CONFIGURATION.md)
9. [Deployment](DEPLOYMENT.md)
10. [Operations Runbook](OPERATIONS_RUNBOOK.md)
11. [Disaster Recovery](DISASTER_RECOVERY.md)
12. [Incident Response](INCIDENT_RESPONSE.md)
13. [Observability](OBSERVABILITY.md)
14. [Testing](TESTING.md)
15. [Deliverability](DELIVERABILITY.md)
16. [Compliance](COMPLIANCE.md)
17. [Data Governance](DATA_GOVERNANCE.md)
18. [Intelligence Model](INTELLIGENCE_MODEL.md)
19. [Campaign Lifecycle](CAMPAIGN_LIFECYCLE.md)
20. [Autonomy Governance](AUTONOMY_GOVERNANCE.md)
21. [Enterprise](ENTERPRISE.md)
22. [Agency](AGENCY.md)
23. [Release Management](RELEASES.md)
24. [Production Readiness](PRODUCTION_READINESS.md)
25. [Access Control](ACCESS_CONTROL.md)
26. [Outbound Policy](OUTBOUND_POLICY.md)
27. [Durable Queue Execution](QUEUE_EXECUTION.md)
28. [AI Governance](AI_GOVERNANCE.md)
29. [AI Evaluation](AI_EVALUATION.md)
30. [Privacy Engineering](PRIVACY_ENGINEERING.md)
31. [Reliability](RELIABILITY.md)
32. [Risk Register](RISK_REGISTER.md)
33. [Final Audit Checklist](FINAL_AUDIT_CHECKLIST.md)
34. [CI Verification](ci-verification.md)
35. [Phase Gates](phase-gates.md)
36. [Final Forensic Enterprise Audit](FINAL_FORENSIC_AUDIT.md)
37. [Phase 1 — Canonical Revenue Intelligence Model](PHASE_01_CANONICAL_REVENUE_MODEL.md)
38. [Phase 2 — Evidence Ledger](PHASE_02_EVIDENCE_LEDGER.md)
39. [Phase 3 — Signal Ingestion](PHASE_03_SIGNAL_INGESTION.md)

## Advanced enterprise phase sequence

The product-completion sequence is distinct from the historical F0–F17 repository-hardening ledger. The current serial roadmap is 1) canonical revenue intelligence data model, 2) evidence ledger, 3) signal ingestion and normalization, 4) signal convergence, 5) temporal intelligence, 6) account graph, 7) why-now, 8) opportunity hypotheses, 9) buying committee intelligence, 10) account memory, 11) revenue intelligence, 12) message intelligence, 13) evidence-backed personalization, 14) governed AI, 15) dynamic autonomy, 16) durable outbound execution, 17) deliverability control plane, 18) provider mesh, 19) experimentation/causal learning, 20) AI evaluation/red-team, 21) enterprise security/supply chain, 22) observability/SRE/DR, 23) enterprise governance/trust, 24) production certification/Enterprise GA.

Phase 1 is implemented by `027_canonical_revenue_model` and is CI-green on its promoted branch. Later phases must not be treated as complete merely because earlier repository hardening already exists.

## Integration references

- [TADS/SDEA](integrations/tads-sdea.md)
- [Listmonk](integrations/listmonk.md)
- [n8n](integrations/n8n.md)

## External control baselines

Security design references OWASP Top 10:2025, NIST CSF 2.0 and NIST AI RMF. Email controls track current major-provider sender requirements. Compliance controls are jurisdiction-aware and never represented as universal legal guarantees.

## Change control

Every material behavior change MUST update the affected documentation in the same change set. Phase completion requires implementation, tests, workflow evidence and documentation reconciliation.
- [Software Supply-Chain Evidence](SUPPLY_CHAIN.md)
