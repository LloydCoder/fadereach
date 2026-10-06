<div align="center">

# FadeReach

**AI outbound revenue infrastructure for teams that need evidence-backed account intelligence, controlled outreach, and measurable pipeline learning.**

[![CI](https://github.com/LloydCoder/fadereach/actions/workflows/ci.yml/badge.svg)](https://github.com/LloydCoder/fadereach/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/LloydCoder/fadereach/badge)](https://scorecard.dev/viewer/?uri=github.com/LloydCoder/fadereach)
[![License: Proprietary](https://img.shields.io/badge/license-proprietary-111111.svg)](LICENSE)
[![Code of Conduct](https://img.shields.io/badge/community-code%20of%20conduct-5b5b5b.svg)](CODE_OF_CONDUCT.md)

</div>

> [!NOTE]
> FadeReach is **proprietary source-available software** owned by Tinlance Limited. It is not an OSI-licensed open-source project. See [LICENSE](LICENSE).

## Visual proof

The repository currently has no verified public product demo GIF or customer-facing screenshot. To avoid manufacturing proof, the canonical visual is the system boundary below; CI and the linked engineering documentation provide the implementation evidence.

```mermaid
flowchart LR
    WI[World Intelligence] --> TADS[TADS]
    TADS --> SDEA[SDEA]
    SDEA --> FR[FadeReach]
    FR --> SALES[Sales / Pipeline]
    SALES --> FDSE[FDSE / FDE]
    FR --> LEARN[Revenue Learning]
    LEARN --> FR
    AP[Tinlance Agent Platform] -. governed execution .-> FR
    OS[Tinlance Agent OS] -. workspace / lifecycle .-> FR
```

## Why FadeReach

| Layer | What it does | What it is not |
| --- | --- | --- |
| **Research** | Finds accounts, people, technologies, hiring, funding, expansion, and other observable signals. | An unverified data dump. |
| **Reason** | Converts evidence into ICP fit, why-now, buyer hypotheses, opportunity hypotheses, and confidence. | A black-box claim generator. |
| **Reach** | Controls campaigns, sequences, provider adapters, webhooks, replies, suppression, and outbound execution. | A generic SMTP wrapper. |
| **Learn** | Records replies, meetings, opportunities, revenue, and experiment outcomes. | A dashboard disconnected from execution. |

The core loop is:

**Research → Reason → Reach → Learn**

FadeReach is one layer in Tinlance's commercial stack:

**World Intelligence → TADS → SDEA → FadeReach → Sales → FDSE/FDE → Revenue + learning**

Tinlance Agent Platform and Tinlance Agent OS remain separate authorities for governed execution and workspace/lifecycle concerns. FadeReach integrates with those systems rather than duplicating policy, sandbox, secrets, audit, or runtime authority.

## Quick Start

For a fast repository smoke check:

```bash
git clone https://github.com/LloydCoder/fadereach.git
cd fadereach
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r backend/requirements.txt
```

Then run the backend test suite from a configured PostgreSQL/Redis development environment:

```bash
cd backend
PYTHONPATH=. pytest -q tests
```

> [!WARNING]
> The full production stack requires secrets, PostgreSQL, Redis, provider credentials, DNS/TLS, and other external infrastructure. Do not use .env.example values as production secrets.

## Installation

### Prerequisites

| Component | Supported baseline |
| --- | --- |
| Python | 3.12 |
| Node.js | 20.x for the current frontend CI baseline |
| npm | Bundled with supported Node.js |
| PostgreSQL | 15-compatible |
| Redis/Valkey | Redis 7-compatible |
| Docker | Docker Engine + Compose v2 for the container path |

### Backend

```bash
cd backend
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install --no-audit --no-fund
npm run build
```

### Docker Compose

For validation:

```bash
docker compose config
```

For the supported single-host deployment, review [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) and the canonical bootstrap at [infrastructure/setup.sh](infrastructure/setup.sh). The bootstrap generates infrastructure secrets and starts the Compose topology; it is intended for a controlled host, not an unreviewed laptop command.

## Usage

### Backend development

```bash
cd backend
. .venv/bin/activate
export ENVIRONMENT=development
export JWT_SECRET='replace-with-a-development-secret-of-at-least-32-characters'
export DATABASE_URL='postgresql://fadereach_runtime:password@localhost:5432/fadereach_meta'
export REDIS_URL='redis://localhost:6379/0'
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Health endpoint:

```bash
curl http://127.0.0.1:8000/api/health
```

### Database migrations

Alembic is the schema authority:

```bash
alembic upgrade head
```

Do not rely on application startup to mutate the database schema.

### Frontend development

```bash
cd frontend
npm run dev
```

The Vite development server uses port 3000 in the current frontend package configuration.

## Configuration / options

The authoritative environment contract is [.env.example](.env.example). Important controls include:

| Variable | Purpose | Default / requirement |
| --- | --- | --- |
| APP_URL | Canonical application URL | Set for each environment |
| DATABASE_URL | Runtime database connection | Required |
| JWT_SECRET | Session/token signing material | Required; use a high-entropy secret |
| CREDENTIAL_ENCRYPTION_KEY | Encryption key for persisted credentials | Required in production |
| UNSUBSCRIBE_SECRET | Signed unsubscribe state | Required |
| SIGNAL_INGEST_SECRET | Protected signal-ingestion boundary | Required |
| REDIS_URL | Transient/cache/queue backend | Required for configured runtime paths |
| FADE_REACH_AUTONOMY_ENABLED | Governed autonomy switch | false |
| AGENT_PLATFORM_BASE_URL | Tinlance Agent Platform integration | Empty unless configured |
| METRICS_TOKEN | Optional internal metrics protection | Empty unless configured |

Secrets must come from environment or a secret-management system. Never commit them.

## Features

| Capability | Current boundary |
| --- | --- |
| Account intelligence | Signals, evidence, fit, temporal state, graph relationships |
| Why-now and opportunity reasoning | Evidence-linked, deterministic application models |
| Buying committee and account memory | Tenant-scoped intelligence records |
| Campaign control | Campaigns, sequences, suppression, policy and audit |
| Durable outbound | Dedicated worker, leases, idempotency and tenant isolation |
| Deliverability control | Authentication, DNS, suppression, rate/reputation signals and pre-send controls |
| Provider mesh | Adapter/capability model for outbound providers |
| Revenue learning | Outcome and attribution records tied to commercial lineage |
| AI governance | Decision records and bounded autonomy rather than implicit authority |
| Enterprise controls | Governance, trust evidence, reliability, recovery and production gates |

## Security and compliance boundaries

- Tenant/resource authorization is enforced server-side.
- PostgreSQL RLS is used where defined by the schema as defense in depth.
- Webhooks must authenticate, reject invalid credentials, and be idempotent.
- Secrets are never intended to live in source control or logs.
- Public application processes should not receive unnecessary host-level privileges.
- AI output is untrusted input unless a governed execution path explicitly authorizes an action.
- Missing evidence must not become a positive claim.
- Deliverability controls measure observable signals; FadeReach does not guarantee inbox placement.
- Outbound compliance is jurisdiction-aware. The software does not provide blanket legal-compliance guarantees.

Read [SECURITY.md](SECURITY.md), [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md), [docs/COMPLIANCE.md](docs/COMPLIANCE.md), and [docs/DELIVERABILITY.md](docs/DELIVERABILITY.md) before operating outbound campaigns.

## Testing and CI

The canonical GitHub Actions workflow is [.github/workflows/ci.yml](.github/workflows/ci.yml). It currently covers:

- Python compilation/imports and pytest;
- PostgreSQL migration-chain validation;
- tenant RLS isolation checks;
- frontend production build;
- Docker Compose configuration/build validation;
- shell syntax;
- Bandit high-severity scanning;
- pip-audit dependency auditing;
- CycloneDX Python SBOM generation and validation.

[OpenSSF Scorecard](.github/workflows/scorecard.yml) provides an additional supply-chain/security posture signal for the public repository.

> [!NOTE]
> A green workflow is evidence for the checks that ran on that commit. It is not proof of production readiness, external-provider health, DNS/TLS configuration, legal compliance, customer workload performance, or independent security assessment.

## Documentation

Start with the [documentation index](docs/README.md).

| Area | Entry point |
| --- | --- |
| Architecture | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| API | [docs/API.md](docs/API.md) |
| Data model | [docs/DATA_MODEL.md](docs/DATA_MODEL.md) |
| Security | [docs/SECURITY.md](docs/SECURITY.md) |
| Threat model | [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) |
| Configuration | [docs/CONFIGURATION.md](docs/CONFIGURATION.md) |
| Deployment | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| Operations | [docs/OPERATIONS_RUNBOOK.md](docs/OPERATIONS_RUNBOOK.md) |
| Disaster recovery | [docs/DISASTER_RECOVERY.md](docs/DISASTER_RECOVERY.md) |
| Deliverability | [docs/DELIVERABILITY.md](docs/DELIVERABILITY.md) |
| Compliance | [docs/COMPLIANCE.md](docs/COMPLIANCE.md) |
| AI governance | [docs/AI_GOVERNANCE.md](docs/AI_GOVERNANCE.md) |
| Production readiness | [docs/PRODUCTION_READINESS.md](docs/PRODUCTION_READINESS.md) |
| Phase gates | [docs/phase-gates.md](docs/phase-gates.md) |
| Enterprise roadmap | [docs/PHASE_01_CANONICAL_REVENUE_MODEL.md](docs/PHASE_01_CANONICAL_REVENUE_MODEL.md) through [Phase 24](docs/PHASE_24_ENTERPRISE_GA.md) |

### Documentation model

The repository's documentation is primarily an engineering/reference corpus. It should be organized over time using Diátaxis:

- **Tutorials** — task-oriented first-run paths for a new operator/developer.
- **How-to** — focused operational procedures.
- **Explanation** — architecture, security, governance, and design rationale.
- **Reference** — API, configuration, schemas, and exact contracts.

The current [docs/README.md](docs/README.md) remains the canonical index while that taxonomy is normalized.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md), follow the pull-request template, and keep implementation, tests, security controls, operations, and documentation synchronized.

## License and acknowledgements

FadeReach is proprietary software owned by **Tinlance Limited**. See [LICENSE](LICENSE) and [docs/LICENSING.md](docs/LICENSING.md).

Third-party components retain their own licenses and notices. See [docs/THIRD_PARTY_NOTICES.md](docs/THIRD_PARTY_NOTICES.md).

## Support

- Technical contribution guidance: [CONTRIBUTING.md](CONTRIBUTING.md)
- User/support guidance: [SUPPORT.md](SUPPORT.md)
- Security vulnerabilities: [SECURITY.md](SECURITY.md)
- Engineering documentation: [docs/README.md](docs/README.md)

<details>
<summary>Roadmap and release discipline</summary>

FadeReach is being developed through serial enterprise phases. Phase completion requires implementation, tests, documentation reconciliation, security controls, deployment assumptions, and green CI on the promoted commit.

The repository also distinguishes repository evidence from external Enterprise GA evidence. Customer workload, live provider credentials, DNS/TLS, backup/restore exercises, independent security assessment, and other external acceptance criteria must remain explicitly verified or pending rather than inferred from source code.

See [docs/phase-gates.md](docs/phase-gates.md), [docs/FINAL_FORENSIC_AUDIT.md](docs/FINAL_FORENSIC_AUDIT.md), and [CHANGELOG.md](CHANGELOG.md).
</details>

<details>
<summary>Troubleshooting</summary>

**Compose reports missing variables:** copy [.env.example](.env.example) and provide the required values for the environment. The production bootstrap also generates infrastructure secrets.

**Migration errors:** verify PostgreSQL is reachable and run alembic upgrade head explicitly. Do not delete migration history to bypass a failure.

**Tenant-access errors:** inspect tenant context, authorization, and RLS evidence. Do not disable authorization or RLS to make a request succeed.

**Outbound delivery problems:** check SPF, DKIM, DMARC, DNS, TLS, bounce/complaint rates, suppression state, provider health, and sending limits. Read [docs/DELIVERABILITY.md](docs/DELIVERABILITY.md).
</details>

<details>
<summary>Repository status</summary>

The repository is public, while the software license remains proprietary. The source tree contains production-oriented application, infrastructure, security, and enterprise documentation. External production claims must be backed by external evidence rather than inferred from repository state.
</details>
