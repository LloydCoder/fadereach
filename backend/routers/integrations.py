"""Signed internal signal bridge for TADS and SDEA."""
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from .deps import get_current_tenant

router = APIRouter()
SIGNAL_SECRET = os.getenv("SIGNAL_INGEST_SECRET", "")

DEMAND_MAP = {
    "hiring": ("capacity_or_delivery_need", "Engineering hiring can indicate active delivery or platform investment."),
    "funding": ("growth_execution", "Funding can create urgency to convert capital into execution and pipeline."),
    "expansion": ("expansion_execution", "Expansion can create new technical, security, and operational requirements."),
    "migration": ("migration_or_modernization", "A migration signal can create an immediate engineering and integration window."),
    "ai_adoption": ("ai_transformation", "AI adoption can create integration, governance, security, or delivery needs."),
    "security_incident": ("security_remediation", "A security incident creates a time-sensitive remediation and resilience window."),
    "infrastructure": ("infrastructure_change", "Infrastructure changes can indicate migration, scale, or reliability work."),
    "leadership": ("strategic_change", "Leadership changes can reset priorities and supplier decisions."),
    "regulatory": ("compliance_change", "Regulatory changes can create a concrete implementation deadline."),
}

def _verify(raw: bytes, signature: str, timestamp: str) -> None:
    if not SIGNAL_SECRET:
        raise HTTPException(503, "Signal ingestion is not configured")
    try:
        ts = int(timestamp)
    except ValueError as exc:
        raise HTTPException(401, "Invalid signal timestamp") from exc
    if abs(datetime.now(timezone.utc).timestamp() - ts) > 300:
        raise HTTPException(401, "Signal timestamp outside tolerance")
    signing_payload = f"{ts}.".encode() + raw
    expected = hmac.new(
        SIGNAL_SECRET.encode(), signing_payload, hashlib.sha256
    ).hexdigest()
    provided = signature.removeprefix("sha256=")
    if not hmac.compare_digest(expected, provided):
        raise HTTPException(401, "Invalid signal signature")

@router.post("/signals")
async def ingest_signal(
    request: Request,
    x_signal_signature: str = Header("", alias="X-Signal-Signature"),
    x_signal_timestamp: str = Header("", alias="X-Signal-Timestamp"),
):
    raw = await request.body()
    if len(raw) > 1024 * 1024:
        raise HTTPException(413, "Signal payload too large")
    _verify(raw, x_signal_signature, x_signal_timestamp)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")

    tenant_id = str(payload.get("tenant_id", ""))
    source = str(payload.get("source", ""))
    signal_type = str(payload.get("signal_type", ""))
    external_id = str(payload.get("external_id", ""))
    domain = payload.get("domain")
    company_name = payload.get("company_name")
    score = max(0, min(100, int(payload.get("score", 0))))
    evidence = payload.get("evidence", [])
    observed_at = payload.get("observed_at")

    if not all([tenant_id, source, signal_type, external_id]):
        raise HTTPException(400, "tenant_id, source, signal_type and external_id are required")
    if not isinstance(evidence, list):
        raise HTTPException(400, "evidence must be an array")
    if len(evidence) > 50:
        raise HTTPException(400, "evidence limit exceeded")
    for item in evidence:
        if not isinstance(item, dict) or not item.get("source") or not item.get("claim"):
            raise HTTPException(400, "Each evidence item requires source and claim")

    db = request.app.state.db
    db = request.app.state.db
    async with db.acquire() as conn:
        tenant = await conn.fetchval("SELECT id FROM tenants WHERE id=$1", tenant_id)
        if not tenant:
            raise HTTPException(404, "Tenant not found")
        claimed = await conn.fetchval(
            """
            INSERT INTO webhook_events (provider,event_id,payload)
            VALUES ('tads_sdea',$1,$2::jsonb)
            ON CONFLICT (provider,event_id) DO NOTHING
            RETURNING id
            """,
            external_id, json.dumps(payload),
        )
        if not claimed:
            return {"status": "duplicate", "external_id": external_id}

        account_id = None
        if domain:
            account = await conn.fetchrow(
                """INSERT INTO accounts (tenant_id, domain, name)
                   VALUES ($1,$2,$3)
                   ON CONFLICT (tenant_id, domain)
                   DO UPDATE SET name=COALESCE(EXCLUDED.name, accounts.name), updated_at=NOW()
                   RETURNING id""",
                tenant_id, domain.lower(), company_name,
            )
            account_id = account["id"]

        row = await conn.fetchrow(
            """INSERT INTO intelligence_signals
               (tenant_id, source, signal_type, company_name, domain, observed_at, score, evidence, external_id)
               VALUES ($1,$2,$3,$4,$5,COALESCE($6,NOW()),$7,$8::jsonb,$9)
               ON CONFLICT (tenant_id, source, external_id) DO UPDATE
               SET signal_type=EXCLUDED.signal_type, company_name=EXCLUDED.company_name,
                   domain=EXCLUDED.domain, observed_at=EXCLUDED.observed_at,
                   score=EXCLUDED.score, evidence=EXCLUDED.evidence
               RETURNING id""",
            tenant_id, source, signal_type, company_name, domain, observed_at,
            score, json.dumps(evidence), external_id,
        )

        if account_id:
            await conn.execute(
                """INSERT INTO account_signals
                   (tenant_id, account_id, source, signal_type, score, observed_at, evidence, external_id)
                   VALUES ($1,$2,$3,$4,$5,COALESCE($6,NOW()),$7::jsonb,$8)
                   ON CONFLICT (tenant_id, source, external_id)
                   DO UPDATE SET score=EXCLUDED.score, observed_at=EXCLUDED.observed_at,
                                 evidence=EXCLUDED.evidence""",
                tenant_id, account_id, source, signal_type, score, observed_at,
                json.dumps(evidence), external_id,
            )

        demand_key = next((k for k in DEMAND_MAP if k in signal_type.lower()), None)
        if demand_key:
            demand_type, why_now = DEMAND_MAP[demand_key]
            confidence = min(0.95, 0.50 + score / 200)
            hypothesis = await conn.fetchrow(
                """INSERT INTO demand_hypotheses
                   (tenant_id, account_id, company_name, domain, why_now, demand_type,
                    recommended_offer, evidence, confidence)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9)
                   RETURNING id""",
                tenant_id, account_id, company_name, domain, why_now, demand_type,
                payload.get("recommended_offer"),
                json.dumps(evidence + [{"signal_id": row["id"], "source": source, "signal_type": signal_type}]),
                confidence,
            )
        else:
            hypothesis = None

    return {
        "signal_id": row["id"],
        "demand_hypothesis_id": hypothesis["id"] if hypothesis else None,
        "status": "accepted",
    }


@router.get("/demand-hypotheses")
async def list_demand_hypotheses(request: Request, auth: dict = Depends(get_current_tenant)):
    # Read-only internal bridge; the signed ingestion path creates records.
    db = request.app.state.db
    async with db.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, company_name, domain, why_now, demand_type,
                      recommended_offer, evidence, confidence, status, created_at
               FROM demand_hypotheses WHERE tenant_id=$1
               ORDER BY created_at DESC LIMIT 200""",
            auth["sub"],
        )
    return {"hypotheses": [dict(row) for row in rows]}
