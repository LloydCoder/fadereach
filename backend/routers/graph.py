"""Persistent outbound intelligence graph read surface."""
from fastapi import APIRouter, Depends, HTTPException, Request
from .deps import get_current_tenant

router = APIRouter()

@router.get("/accounts/{domain}")
async def get_account_graph(
    domain: str,
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    db = request.app.state.db
    tenant_id = auth["sub"]
    async with db.acquire() as conn:
        account = await conn.fetchrow(
            """SELECT id, domain, name, industry, company_size, location, website,
                      created_at, updated_at
               FROM accounts WHERE tenant_id=$1 AND lower(domain)=lower($2)""",
            tenant_id, domain,
        )
        if not account:
            raise HTTPException(404, "Account not found")

        people = await conn.fetch(
            """SELECT id, email, first_name, last_name, title, status, icp_score,
                      signal_type, signal_data, created_at
               FROM leads WHERE tenant_id=$1 AND account_id=$2
               ORDER BY icp_score DESC, created_at DESC LIMIT 200""",
            tenant_id, account["id"],
        )
        signals = await conn.fetch(
            """SELECT id, source, signal_type, score, observed_at, evidence
               FROM account_signals WHERE tenant_id=$1 AND account_id=$2
               ORDER BY observed_at DESC LIMIT 200""",
            tenant_id, account["id"],
        )
        technologies = await conn.fetch(
            """SELECT id, name, category, version, first_seen_at, last_seen_at, attributes
               FROM technologies WHERE tenant_id=$1 AND organization_id=(
                   SELECT organization_id FROM accounts WHERE tenant_id=$1 AND id=$2
               )
               ORDER BY last_seen_at DESC LIMIT 200""",
            tenant_id, account["id"],
        )
        initiatives = await conn.fetch(
            """SELECT id, name, initiative_type, status, started_at, ended_at, confidence, attributes
               FROM initiatives WHERE tenant_id=$1 AND organization_id=(
                   SELECT organization_id FROM accounts WHERE tenant_id=$1 AND id=$2
               )
               ORDER BY updated_at DESC LIMIT 100""",
            tenant_id, account["id"],
        )
        opportunities = await conn.fetch(
            """SELECT id, name, stage, score, confidence, estimated_value, currency,
                      buying_window_start, buying_window_end, created_at, updated_at
               FROM opportunities WHERE tenant_id=$1 AND organization_id=(
                   SELECT organization_id FROM accounts WHERE tenant_id=$1 AND id=$2
               )
               ORDER BY updated_at DESC LIMIT 100""",
            tenant_id, account["id"],
        )
        why_now = await conn.fetchrow(
            """SELECT id, what_changed, when_changed, why_matters, why_now,
                      capability_required, confidence, unknowns, evidence_refs,
                      signal_cluster_ids, trajectory_states, status, evaluated_at
               FROM why_now_assessments
               WHERE tenant_id=$1 AND account_id=$2
               ORDER BY evaluated_at DESC LIMIT 1""",
            tenant_id, account["id"],
        )
        edges = await conn.fetch(
            """SELECT id, source_type, source_id, target_type, target_id, relation,
                      confidence, evidence_id, valid_from, valid_to, metadata
               FROM account_graph_edges
               WHERE tenant_id=$1 AND account_id=$2
                 AND (valid_to IS NULL OR valid_to > NOW())
               ORDER BY updated_at DESC LIMIT 500""",
            tenant_id, account["id"],
        )
        hypotheses = await conn.fetch(
            """SELECT id, why_now, demand_type, recommended_offer,
                      evidence, confidence, status, created_at
               FROM demand_hypotheses
               WHERE tenant_id=$1 AND account_id=$2
               ORDER BY created_at DESC LIMIT 50""",
            tenant_id, account["id"],
        )

    return {
        "account": dict(account),
        "people": [dict(row) for row in people],
        "signals": [dict(row) for row in signals],
        "demand_hypotheses": [dict(row) for row in hypotheses],
        "technologies": [dict(row) for row in technologies],
        "initiatives": [dict(row) for row in initiatives],
        "opportunities": [dict(row) for row in opportunities],
        "edges": [dict(row) for row in edges],
        "why_now": dict(why_now) if why_now else None,
        "graph_semantics": {
            "account": "company/entity",
            "people": "buyer/contact",
            "signals": "observed change",
            "demand_hypotheses": "reasoned opportunity hypothesis",
            "technologies": "observed technology",
            "initiatives": "organizational initiative",
            "opportunities": "commercial opportunity",
            "edges": "typed, tenant-scoped, evidence-linkable relationship",
        },
    }
