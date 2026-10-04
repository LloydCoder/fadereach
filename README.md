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

The repository is being hardened in serial production phases. Green CI is a hard phase gate, not proof of production readiness. No subsequent phase is accepted until the current phase has a completed CI/workflow run on its actual code.

Current sequence:

1. **F0 — Forensic reconciliation**
2. **F1 — Production foundation**
3. **F2 — Database and tenancy**
4. **F3 — Security hardening**
5. **F4 — Outbound execution**
6. **F5 — Deliverability control plane**
7. **F6 — Intelligence engine**
8. **F7 — TADS/SDEA integration**
9. **F8 — Outbound Intelligence Graph**
10. **F9 — Campaign Autopilot**
11. **F10 — Learning and attribution**
12. **F11 — Agency and enterprise**
13. **F12 — Autonomous governed GTM**

A phase is not considered complete merely because code exists. Its implementation, documentation, tests, deployment assumptions and CI/workflow evidence must reconcile.

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

The repository contains deployment automation, but production deployment is intentionally gated. For a fresh Ubuntu host, `sudo bash infrastructure/setup.sh` is the canonical bootstrap; it uses the Compose topology and does not install competing host PostgreSQL/Redis/Listmonk/n8n services. Never treat a GitHub commit as evidence that the running server has been updated.

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

The CI workflow runs the backend smoke suite with pytest, verifies the Alembic migration chain, exercises tenant RLS isolation against PostgreSQL, builds the frontend and validates Docker Compose and shell syntax.

For current email-sender requirements, consult Google's [Email sender guidelines](https://support.google.com/mail/answer/81126) before changing deliverability policy.

## Commercial positioning

**Hero:** Turn your ICP into qualified conversations.

**One-liner:** FadeReach is the AI outbound revenue OS that finds the right accounts, understands why they should care, and turns those insights into qualified conversations.

Recommended commercial packaging is intentionally separated from infrastructure complexity. Pricing and plan limits are authoritative application data and must not be trusted from client-controlled claims.

## License

See the repository license and third-party dependency notices before distribution.

---

**Tinlance Limited**  
FadeReach — AI Outbound Revenue OS
