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
40. [Phase 4 — Signal Convergence](PHASE_04_SIGNAL_CONVERGENCE.md)
41. [Phase 5 — Temporal Intelligence](PHASE_05_TEMPORAL_INTELLIGENCE.md)
42. [Phase 6 — Account Intelligence Graph](PHASE_06_ACCOUNT_GRAPH.md)
43. [Phase 7 — Why-Now Engine](PHASE_07_WHY_NOW.md)
44. [Phase 8 — Opportunity Hypotheses](PHASE_08_OPPORTUNITY_HYPOTHESES.md)
45. [Phase 9 — Buying Committee](PHASE_09_BUYING_COMMITTEE.md)
46. [Phase 10 — Account Memory](PHASE_10_ACCOUNT_MEMORY.md)
47. [Phase 11 — Revenue Intelligence](PHASE_11_REVENUE_INTELLIGENCE.md)
48. [Phase 12 — Message Intelligence](PHASE_12_MESSAGE_INTELLIGENCE.md)
49. [Phase 13 — Evidence-Backed Personalization](PHASE_13_PERSONALIZATION.md)
50. [Phase 14 — Governed AI](PHASE_14_GOVERNED_AI.md)
51. [Phase 15 — Dynamic Autonomy](PHASE_15_DYNAMIC_AUTONOMY.md)
52. [Phase 16 — Durable Outbound Execution](PHASE_16_DURABLE_EXECUTION.md)
53. [Phase 17 — Deliverability Control Plane](PHASE_17_DELIVERABILITY_CONTROL.md)
54. [Phase 18 — Provider Mesh](PHASE_18_PROVIDER_MESH.md)
55. [Phase 19 — Experimentation](PHASE_19_EXPERIMENTATION.md)
56. [Phase 20 — AI Evaluation](PHASE_20_AI_EVALUATION.md)
57. [Phase 21 — Security & Supply Chain](PHASE_21_SECURITY_SUPPLY_CHAIN_AUDIT.md)
58. [Phase 22 — SRE & DR](PHASE_22_SRE_DR.md)
59. [Phase 23 — Governance & Trust](PHASE_23_GOVERNANCE_TRUST.md)
60. [Phase 24 — Enterprise GA](PHASE_24_ENTERPRISE_GA.md)

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
