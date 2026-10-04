"""Human-approved Campaign Autopilot planning and launch orchestration."""
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from .deps import get_current_tenant

router = APIRouter()

class AutopilotPlanReq(BaseModel):
    goal: str = Field(min_length=10, max_length=1000)
    offer: str = Field(min_length=3, max_length=500)
    min_signal_score: int = Field(default=70, ge=0, le=100)
    max_accounts: int = Field(default=25, ge=1, le=100)

@router.post("/plan")
async def create_plan(
    req: AutopilotPlanReq,
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    db = request.app.state.db
    tenant_id = auth["sub"]

    async with db.acquire() as conn:
        rows = await conn.fetch(
            """SELECT dh.id, dh.company_name, dh.domain, dh.why_now,
                      dh.demand_type, dh.recommended_offer, dh.evidence,
                      dh.confidence, a.id AS account_id
               FROM demand_hypotheses dh
               LEFT JOIN accounts a ON a.id=dh.account_id AND a.tenant_id=dh.tenant_id
               WHERE dh.tenant_id=$1 AND dh.status IN ('new','qualified')
               ORDER BY dh.confidence DESC, dh.created_at DESC
               LIMIT $2""",
            tenant_id, req.max_accounts,
        )

        targets = []
        for row in rows:
            people = await conn.fetch(
                """SELECT id, email, first_name, last_name, title
                   FROM leads WHERE tenant_id=$1 AND account_id=$2
                     AND status NOT IN ('unsubscribed','bounced')
                   ORDER BY icp_score DESC LIMIT 3""",
                tenant_id, row["account_id"],
            )
            targets.append({
                "account_id": row["account_id"],
                "company_name": row["company_name"],
                "domain": row["domain"],
                "why_now": row["why_now"],
                "demand_type": row["demand_type"],
                "confidence": float(row["confidence"]),
                "evidence": row["evidence"],
                "buyers": [dict(person) for person in people],
            })

        plan = {
            "goal": req.goal,
            "offer": req.offer,
            "target_policy": {
                "min_signal_score": req.min_signal_score,
                "max_accounts": req.max_accounts,
            },
            "targets": targets,
            "message_strategy": {
                "subject": "Quick question about {{company}}",
                "body": "Hi {{first_name}},

{{ai_first_line}}

Would it be useful to compare notes on {{company}}'s current priorities?

Best,
Tinlance",
                "cta": "single low-friction reply CTA",
            },
            "gates": {
                "human_approval_required": True,
                "suppression_required": True,
                "provider_required": True,
                "deliverability_pause_blocks_send": True,
                "legal_compliance_review": "required by sender/jurisdiction before launch",
            },
        }

        run = await conn.fetchrow(
            """INSERT INTO autopilot_runs (tenant_id, goal, plan)
               VALUES ($1,$2,$3::jsonb) RETURNING id, status, created_at""",
            tenant_id, req.goal, json.dumps(plan),
        )

    return {"run_id": run["id"], "status": run["status"], "plan": plan}


@router.post("/{run_id}/approve")
async def approve_plan(
    run_id: int,
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    db = request.app.state.db
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            """UPDATE autopilot_runs
               SET status='approved', approved_by=$1, approved_at=NOW(), updated_at=NOW()
               WHERE id=$2 AND tenant_id=$1
               RETURNING id, plan""",
            auth["sub"], run_id,
        )
    if not row:
        raise HTTPException(404, "Autopilot run not found")
    return {"run_id": run_id, "status": "approved", "plan": row["plan"]}


@router.post("/{run_id}/launch")
async def launch_plan(
    run_id: int,
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    db = request.app.state.db
    async with db.acquire() as conn:
        run = await conn.fetchrow(
            """SELECT id, goal, plan, status FROM autopilot_runs
               WHERE id=$1 AND tenant_id=$2""",
            run_id, auth["sub"],
        )
        if not run:
            raise HTTPException(404, "Autopilot run not found")
        if run["status"] != "approved":
            raise HTTPException(409, "Autopilot run requires explicit human approval")

        plan = run["plan"]
        campaign = await conn.fetchrow(
            """INSERT INTO campaigns
               (tenant_id, name, subject, body_html, target_segment, sequence_steps, status, audit_score)
               VALUES ($1,$2,$3,$4,$5,1,'draft',80)
               RETURNING id""",
            auth["sub"],
            f"Autopilot: {run['goal'][:80]}",
            plan["message_strategy"]["subject"],
            plan["message_strategy"]["body"],
            json.dumps(plan["target_policy"]),
        )
        await conn.execute(
            """UPDATE autopilot_runs
               SET status='launched', campaign_id=$1, updated_at=NOW()
               WHERE id=$2 AND tenant_id=$3""",
            campaign["id"], run_id, auth["sub"],
        )

    return {
        "run_id": run_id,
        "status": "launched",
        "campaign_id": campaign["id"],
        "next_action": "Review the generated campaign and use the governed send endpoint after deliverability/compliance checks.",
    }


@router.get("")
async def list_runs(request: Request, auth: dict = Depends(get_current_tenant)):
    db = request.app.state.db
    async with db.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, goal, status, campaign_id, approved_by, approved_at, created_at, updated_at
               FROM autopilot_runs WHERE tenant_id=$1
               ORDER BY created_at DESC LIMIT 100""",
            auth["sub"],
        )
    return {"runs": [dict(row) for row in rows]}
