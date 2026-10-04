"""Evidence-backed outbound intelligence engine.

LLM output, when later added, remains a hypothesis layer. Evidence and
authoritative lead state stay in the database.
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from .deps import get_current_tenant

router = APIRouter()

WHY_NOW = {
    "funding": "Recent funding can create pressure to accelerate growth and execution.",
    "hiring": "Hiring activity can indicate active investment and an operational need.",
    "hiring_spike": "A hiring spike can indicate a new initiative, expansion, or execution bottleneck.",
    "expansion": "Expansion signals can create new operational and infrastructure requirements.",
    "leadership_change": "Leadership changes can reset priorities and vendor decisions.",
    "tech_stack_change": "Technology changes can create migration, integration, or security work.",
    "security_gap": "An observed security gap can create an actionable risk-remediation window.",
}

def _buyer_hypothesis(title: str | None, company: str | None) -> str:
    title_l = (title or "").lower()
    if any(x in title_l for x in ["ceo", "founder", "owner", "president"]):
        return title or "Founder / executive sponsor"
    if any(x in title_l for x in ["cto", "engineering", "developer", "technology"]):
        return title or "CTO / engineering leader"
    if any(x in title_l for x in ["ciso", "security", "information"]):
        return title or "CISO / security leader"
    if any(x in title_l for x in ["revenue", "sales", "growth", "marketing"]):
        return title or "Revenue / growth leader"
    return title or "Likely operational decision-maker"

def _signal_key(signal_type: str | None) -> str:
    value = (signal_type or "").lower()
    for key in WHY_NOW:
        if key in value:
            return key
    return ""

@router.get("/{lead_id}")
async def get_lead_intelligence(
    lead_id: int,
    request: Request,
    auth: dict = Depends(get_current_tenant),
):
    db = request.app.state.db
    tenant_id = auth["sub"]

    async with db.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT l.*, li.id AS intelligence_id, li.fit_score, li.why_now,
                      li.buyer_hypothesis, li.problem_hypothesis, li.offer_angle,
                      li.evidence, li.confidence, li.model_version
               FROM leads l
               LEFT JOIN lead_intelligence li
                 ON li.lead_id=l.id AND li.tenant_id=l.tenant_id
               WHERE l.id=$1 AND l.tenant_id=$2""",
            lead_id, tenant_id,
        )
        if not row:
            raise HTTPException(404, "Lead not found")

        signal_type = row["signal_type"]
        signal_data = row["signal_data"] or {}
        signal_key = _signal_key(signal_type)
        fit_score = max(
            0,
            min(
                100,
                round(
                    (row["icp_score"] or 0) * 0.45
                    + (row["verify_score"] or 0) * 0.15
                    + (row["ai_score"] or 0) * 0.20
                    + (70 if signal_type else 40) * 0.20
                ),
            ),
        )

        evidence = [
            {
                "source": "lead_record",
                "claim": "Lead identity and firmographic data",
                "source_ref": f"lead:{lead_id}",
                "confidence": 1.0,
            }
        ]
        if signal_type:
            evidence.append({
                "source": "signal_data",
                "claim": signal_type,
                "source_ref": f"lead:{lead_id}:signal",
                "observed_at": row["created_at"].isoformat() if row["created_at"] else None,
                "data": signal_data,
                "confidence": 0.85,
            })

        intelligence = {
            "fit_score": fit_score,
            "why_now": WHY_NOW.get(
                signal_key,
                "No strong why-now signal is currently evidenced; timing remains uncertain.",
            ),
            "buyer_hypothesis": _buyer_hypothesis(row["title"], row["company"]),
            "problem_hypothesis": (
                signal_data.get("problem")
                or signal_data.get("pain_point")
                or "Problem hypothesis requires validation with the buyer."
            ),
            "offer_angle": (
                signal_data.get("offer_angle")
                or "Lead with the observed signal and validate the operational impact before proposing a solution."
            ),
            "evidence": evidence,
            "confidence": round(
                min(0.95, 0.55 + (0.20 if signal_type else 0) + (0.15 if row["company"] else 0)),
                3,
            ),
            "model_version": "deterministic-v1",
        }

        saved = await conn.fetchrow(
            """INSERT INTO lead_intelligence
               (tenant_id, lead_id, fit_score, why_now, buyer_hypothesis,
                problem_hypothesis, offer_angle, evidence, confidence, model_version)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9,$10)
               ON CONFLICT (tenant_id, lead_id)
               DO UPDATE SET fit_score=EXCLUDED.fit_score,
                             why_now=EXCLUDED.why_now,
                             buyer_hypothesis=EXCLUDED.buyer_hypothesis,
                             problem_hypothesis=EXCLUDED.problem_hypothesis,
                             offer_angle=EXCLUDED.offer_angle,
                             evidence=EXCLUDED.evidence,
                             confidence=EXCLUDED.confidence,
                             model_version=EXCLUDED.model_version,
                             updated_at=NOW()
               RETURNING id""",
            tenant_id, lead_id, intelligence["fit_score"], intelligence["why_now"],
            intelligence["buyer_hypothesis"], intelligence["problem_hypothesis"],
            intelligence["offer_angle"], json.dumps(intelligence["evidence"]),
            intelligence["confidence"], intelligence["model_version"],
        )

    return {"lead_id": lead_id, "intelligence_id": saved["id"], **intelligence}
