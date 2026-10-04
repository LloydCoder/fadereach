# FadeReach Architecture

## Purpose

FadeReach is an outbound intelligence and revenue-execution system. Its primary value is the controlled loop:

Research → Reason → Reach → Learn.

It is not merely an email sender.

## Logical architecture

```
World Intelligence / public sources
          ↓
TADS account + demand signals
          ↓
SDEA signal-driven engineering acquisition
          ↓
FadeReach intelligence
  ├─ accounts / people / signals
  ├─ evidence / hypotheses / fit
  ├─ opportunity graph
  └─ campaign recommendations
          ↓
Campaign control plane
  ├─ tenant / RBAC / policy
  ├─ campaigns / sequences
  ├─ approvals / safeguards
  └─ audit
          ↓
Outbound execution
  ├─ provider/mailbox adapters
  ├─ Listmonk adapter
  ├─ webhook ingestion
  └─ durable execution/queues
          ↓
Replies / meetings / opportunities / revenue
          ↓
Learning + attribution
```

## Runtime components

- FastAPI: authoritative application/control API; it does not run durable background workers.
- PostgreSQL: authoritative durable application state and tenancy boundary.
- Alembic: schema migration authority.
- Redis/Valkey: transient/cache/queue support where configured; it is not the source of truth.
- Listmonk: email execution subsystem/adapter, not intelligence authority.
- n8n: integration/automation adapter, not the authoritative runtime.
- React/Vite: web application.
- Nginx/Cloudflare: edge/TLS layer.
- Dedicated worker process: durable outbound execution and retention enforcement, scaled independently from HTTP API workers.
- Docker Compose/systemd: current single-host deployment primitives.

## Authority boundaries

FadeReach owns application state, tenant/resource authorization, campaign state, outbound policy and product-domain semantics. The Tinlance Agent Platform owns governed execution authority when FadeReach invokes governed agents/tools. Agent OS owns higher-level workspace/lifecycle UX. No duplicate policy, sandbox, secret authority or audit authority should be introduced inside FadeReach.

## Trust boundaries

1. Internet → edge.
2. Edge → API.
3. API → PostgreSQL.
4. API/workers → Redis.
5. API → dedicated worker via PostgreSQL-backed durable state; the API does not own worker lifecycle.
6. Worker → PostgreSQL/provider infrastructure.
7. Provider → webhook ingress.
8. Tenant user → application.
9. AI/model → application decision layer.
10. FadeReach → TADS/SDEA.
11. FadeReach → Agent Platform/OS.

## Data-flow rules

- Tenant context MUST be established server-side.
- Database isolation MUST be enforced at the application layer and, where defined by schema, PostgreSQL RLS.
- External events MUST be authenticated and idempotent.
- AI output is advisory unless an explicit governed execution path authorizes an action.
- Evidence and provenance MUST remain distinguishable from inference.
- Secrets MUST never be persisted in source code or logs.

## Scaling posture

The current topology is intentionally simple and single-host compatible. Horizontal decomposition should be introduced only when measured workload, isolation, availability or compliance requirements justify it. PostgreSQL remains the system of record; distributed caches/queues must not silently become authoritative.

## Failure philosophy

Fail closed for authorization, tenant resolution, secret validation, webhook authentication and high-risk outbound actions. Degrade gracefully for enrichment, optional intelligence and non-critical analytics. Never convert missing evidence into a positive assertion.