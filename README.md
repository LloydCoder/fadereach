# FadeReach

## AI Outbound Revenue OS

FadeReach is Tinlance's outbound intelligence and revenue-execution platform. It combines account discovery, evidence-backed research, opportunity reasoning, outbound execution, reply handling, deliverability controls, and outcome learning.

**Product principle:** FadeReach is not primarily an email sender. Email is an execution channel inside an intelligence and revenue workflow.

### Core loop

```text
Research → Reason → Reach → Learn
```

- **Research** — accounts, people, technology, hiring, funding, expansion, product and other observable signals.
- **Reason** — ICP fit, why-now, buyer hypothesis, likely problem, offer/angle, evidence and confidence.
- **Reach** — campaigns, sequences, mailbox/provider execution, webhooks, replies and qualification.
- **Learn** — positive replies, qualified conversations, meetings, opportunities, revenue and experiment outcomes.

### Product modes

| Mode | Purpose |
| --- | --- |
| **Tinlance internal engine** | Powers controlled outbound for Tinlance products and services. |
| **SaaS** | Self-serve and agency workspaces for outbound teams. |
| **Managed** | Done-for-you outbound intelligence and execution. |

### System boundaries

FadeReach is one layer in the Tinlance commercial stack:

```text
World Intelligence
      ↓
TADS — account / demand-signal intelligence
      ↓
SDEA — signal-driven engineering acquisition
      ↓
FadeReach — outbound intelligence + execution
      ↓
Sales / conversations / pipeline
      ↓
FDSE / FDE delivery
      ↓
Revenue + learning
```

Tinlance Agent Platform and Tinlance Agent OS are separate governed execution/workspace systems. FadeReach must integrate with them where appropriate rather than reimplement their authority, policy, sandbox, audit or runtime responsibilities.

## Current architecture

```text
                         FadeReach
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
      Intelligence       Control          Execution
          │                 │                 │
      signals, fit,     FastAPI API,      campaigns,
      research, graph   tenancy, RBAC,    sequences,
      opportunity        billing, audit   providers
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                       Learn / Measure
                            │
                    pipeline + revenue
```

### Infrastructure components

- **FastAPI** — application/control API.
- **PostgreSQL** — authoritative application state.
- **Alembic** — schema migration authority.
- **Redis/Valkey** — transient/cache/queue state where used.
- **Listmonk** — email execution adapter, not the product brain.
- **n8n** — external integration/automation adapter, not the authoritative intelligence or runtime.
- **React/Vite** — web application.
- **Nginx/Cloudflare** — edge and TLS layer.
- **Docker/systemd** — deployment primitives for the current single-host production path.
- **Dedicated worker** — durable outbound execution and retention enforcement, separated from HTTP API replicas.

The production topology is intentionally simple until measured scale justifies additional distributed infrastructure.

## Repository layout

```text
fadereach/
├── backend/
│   ├── main.py
│   ├── routers/
│   ├── middleware/
│   ├── alembic/
│   │   └── versions/
│   └── requirements.txt
├── frontend/
├── infrastructure/
├── scripts/
├── landing/
├── docs/
├── n8n-workflows/
├── docker-compose.yml
├── alembic.ini
└── .github/workflows/
```

## Engineering status

### Advanced enterprise product roadmap

The current advanced roadmap is executed separately from the historical F0–F17 hardening ledger. The serial sequence is: **1 Canonical Revenue Intelligence Data Model → 2 Evidence Ledger → 3 Signal Ingestion & Normalization → 4 Signal Convergence → 5 Temporal Intelligence → 6 Account Intelligence Graph → 7 Why-Now → 8 Opportunity Hypothesis → 9 Buying Committee → 10 Account Memory → 11 Revenue Intelligence → 12 Message Intelligence → 13 Evidence-Backed Personalization → 14 Governed AI → 15 Dynamic Autonomy → 16 Durable Outbound → 17 Deliverability Control Plane → 18 Provider Mesh → 19 Experimentation/Causal Learning → 20 AI Evaluation/Red Team → 21 Security/Supply Chain → 22 Observability/SRE/DR → 23 Enterprise Governance/Trust → 24 Production Certification/Enterprise GA. Each phase requires implementation, tests, documentation reconciliation, and green CI on the promoted commit before the next phase starts.


The repository is being hardened in serial production phases. Green CI is a hard phase gate, not proof of production readiness. No subsequent phase is accepted until the current phase has a completed CI/workflow run on its actual code.

Current enterprise sequence:

1. **F0 — Forensic reconciliation**
2. **F1 — Deterministic production foundation**
3. **F2 — Database and tenancy**
4. **F3 — Security hardening**
5. **F4 — Durable outbound execution**
6. **F5 — Deliverability control plane**
7. **F6 — Compliance and data governance**
8. **F7 — Intelligence engine**
9. **F8 — TADS/SDEA integration**
10. **F9 — Outbound Intelligence Graph**
11. **F10 — Campaign Autopilot**
12. **F11 — Learning and revenue attribution**
13. **F12 — Agency platform**
14. **F13 — Enterprise platform**
15. **F14 — Reliability, observability and disaster recovery**
16. **F15 — Production operations**
17. **F16 — Governed autonomous GTM**
18. **F17 — Final forensic enterprise audit**

A phase is not complete merely because code exists. The implementation, documentation, tests, deployment assumptions, security controls and CI/workflow evidence must reconcile. A phase gate requires a successful workflow run on the actual commit being promoted; a green CI run is necessary but is not by itself proof of production readiness.

## Local development

### Backend

Use Python 3.12 for the supported CI/runtime baseline.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Configure the environment from the repository's `.env.example`.

### Database migrations

Alembic is the schema authority:

```bash
alembic upgrade head
```

Do not use application startup to mutate the database schema.

### Frontend

```bash
cd frontend
npm install
npm run build
```

### Compose validation

```bash
docker compose config
```

Use the CI workflow as the canonical minimum quality gate.

## Security and tenancy principles

- Authentication establishes session identity; authorization and subscription state are authoritative server/database state.
- Tenant/resource authorization must be enforced server-side.
- Provider webhooks must authenticate, reject missing secrets, and be idempotent.
- Public API services must not receive the Docker socket or other unnecessary host-privileged mounts.
- Secrets belong in environment/secret-management systems, never source control.
- Tenant provisioning must run through a constrained privileged worker rather than an internet-facing API process.
- Database isolation will use explicit tenant ownership and PostgreSQL Row-Level Security where the final schema requires database-enforced isolation.
- Audit events must be attributable and tamper-resistant.
- Deliverability controls must be based on observable authentication, DNS, reputation and sending signals; the product must not claim guaranteed inbox placement.

For Gmail recipients, current Google sender requirements include authentication, valid forward/reverse DNS, TLS, spam-rate controls, and additional requirements for bulk senders such as DMARC alignment and one-click unsubscribe for marketing/subscribed messages. See Google's current sender guidance before changing deliverability policies.

## Outbound compliance

FadeReach provides tooling and controls; it does not make blanket legal-compliance guarantees.

Campaign policy must account for the recipient jurisdiction, subscriber/customer status, lawful basis where applicable, data source, purpose, suppression, unsubscribe handling, sender identity and retention requirements.

## Production deployment

The repository contains deployment automation, but production deployment is intentionally gated. For a fresh Ubuntu host, `sudo bash infrastructure/setup.sh` is the canonical bootstrap; it uses the Compose topology and does not install competing host PostgreSQL/Redis/Listmonk/n8n services. The current bootstrap expects to be run from a checked-out repository and creates only the infrastructure secrets it can safely generate locally. Never treat a GitHub commit as evidence that the running server has been updated.

Before production promotion:

1. Pass CI.
2. Apply database migrations.
3. Verify environment/secrets.
4. Verify DNS/TLS and edge configuration.
5. Deploy application and workers.
6. Run health and smoke checks.
7. Verify logs/metrics.
8. Confirm rollback path.

The deploy workflow is manual by design and must not silently deploy arbitrary pushes.

## Deliverability

FadeReach must measure and expose observable readiness rather than an invented "inbox probability".

At minimum the control plane should track:

- SPF
- DKIM
- DMARC
- forward/reverse DNS
- TLS
- bounce rate
- complaint rate
- suppression state
- unsubscribe handling
- sending volume/rate
- provider/mailbox health
- reputation signals where available

For high-volume Gmail sending, Google currently requires both SPF and DKIM, DMARC, valid PTR, TLS, RFC 5322 formatting, low spam rates, aligned authentication and one-click unsubscribe for marketing/subscribed messages.

## Testing and CI

The CI workflow validates:

- backend compilation/import
- PostgreSQL migration chain
- backend smoke tests
- frontend production build
- Docker Compose configuration
- shell syntax
- CycloneDX Python SBOM generation and structural validation
- dependency-update governance via Dependabot

The CI workflow runs the backend smoke suite with pytest, verifies the Alembic migration chain, exercises tenant RLS isolation against PostgreSQL, builds the frontend, validates Docker Compose and shell syntax, and generates a retained CycloneDX Python SBOM. Dependabot is configured for Python, npm, Docker and GitHub Actions dependency updates.

For current email-sender requirements, consult Google's [Email sender guidelines](https://support.google.com/mail/answer/81126) before changing deliverability policy.

## Commercial positioning

**Hero:** Turn your ICP into qualified conversations.

**One-liner:** FadeReach is the AI outbound revenue OS that finds the right accounts, understands why they should care, and turns those insights into qualified conversations.

Recommended commercial packaging is intentionally separated from infrastructure complexity. Pricing and plan limits are authoritative application data and must not be trusted from client-controlled claims.

## License

FadeReach is proprietary software owned by **Tinlance Limited**. See the root [LICENSE](LICENSE) and [Licensing](docs/LICENSING.md) policy before using, distributing, or commercializing the repository. Third-party dependencies remain subject to their own licenses and notices.

---

**Tinlance Limited**  
FadeReach — AI Outbound Revenue OS


## Documentation

The authoritative engineering, security, operations, compliance and product documentation is indexed in [docs/README.md](docs/README.md).

Key references:
- [Architecture](docs/ARCHITECTURE.md)
- [Security](docs/SECURITY.md)
- [Threat Model](docs/THREAT_MODEL.md)
- [Data Model](docs/DATA_MODEL.md)
- [API Contract](docs/API.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Operations Runbook](docs/OPERATIONS_RUNBOOK.md)
- [Disaster Recovery](docs/DISASTER_RECOVERY.md)
- [Deliverability](docs/DELIVERABILITY.md)
- [Compliance](docs/COMPLIANCE.md)
- [Intelligence Model](docs/INTELLIGENCE_MODEL.md)
- [Autonomy Governance](docs/AUTONOMY_GOVERNANCE.md)
- [Production Readiness](docs/PRODUCTION_READINESS.md)
- [Phase 1 — Canonical Revenue Intelligence Model](docs/PHASE_01_CANONICAL_REVENUE_MODEL.md)
- [Phase 2 — Evidence Ledger](docs/PHASE_02_EVIDENCE_LEDGER.md)
- [Phase 3 — Signal Ingestion](docs/PHASE_03_SIGNAL_INGESTION.md)
- [Supply-Chain Evidence](docs/SUPPLY_CHAIN.md)

Documentation is a production artifact: behavior changes must reconcile implementation, tests, security controls, operational assumptions and documentation in the same change set.
