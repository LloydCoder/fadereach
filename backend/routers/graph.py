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
        "graph_semantics": {
            "account": "company/entity",
            "people": "buyer/contact",
            "signals": "observed change",
            "demand_hypotheses": "reasoned opportunity hypothesis",
        },
    }
