"""Signed internal signal bridge for TADS and SDEA."""
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from .deps import get_current_tenant
from tenant_context import tenant_id_context
from signal_convergence import persist_signal_and_convergence
from temporal_intelligence import persist_trajectory

router = APIRouter()
SIGNAL_SECRET = os.getenv("SIGNAL_INGEST_SECRET", "")

SIGNAL_NORMALIZATION = {
    "hiring": ("hiring", "workforce", 45),
    "hiring_spike": ("hiring_spike", "workforce", 45),
    "funding": ("funding", "finance", 90),
    "leadership": ("leadership_change", "leadership", 120),
    "leadership_change": ("leadership_change", "leadership", 120),
    "expansion": ("expansion", "expansion", 60),
    "migration": ("migration", "technology", 60),
    "tech_stack_change": ("technology_change", "technology", 45),
    "ai_adoption": ("ai_adoption", "ai", 60),
    "security_incident": ("security_incident", "security", 30),
    "security_gap": ("security_gap", "security", 30),
    "infrastructure": ("infrastructure_change", "infrastructure", 45),
    "product_launch": ("product_launch", "product", 45),
    "pricing_change": ("pricing_change", "commercial", 30),
    "partnership": ("partnership", "commercial", 60),
    "procurement": ("procurement", "procurement", 60),
    "regulatory": ("regulatory_change", "compliance", 120),
    "compliance": ("compliance_change", "compliance", 120),
}

def _normalize_signal(signal_type: str) -> tuple[str, str, int]:
    value = signal_type.strip().lower().replace("-", "_").replace(" ", "_")
    for key, result in SIGNAL_NORMALIZATION.items():
        if key in value:
            return result
    return (value[:120] or "unknown", "other", 30)

def _source_trust_tier(source: str) -> str:
    return {"tads": "T1", "sdea": "T1", "reconos": "T2"}.get(source.lower(), "T2")

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
    normalized_type, signal_category, freshness_days = _normalize_signal(signal_type)
    source_url = payload.get("source_url") or payload.get("url")
    raw_payload_hash = hashlib.sha256(raw).hexdigest()

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
    tenant_ctx = tenant_id_context.set(tenant_id)
    async with db.acquire() as conn:
        tenant = await conn.fetchval("SELECT id FROM tenants WHERE id=$1", tenant_id)
        if not tenant:
            raise HTTPException(404, "Tenant not found")
        await conn.execute(
            """INSERT INTO signal_sources
               (tenant_id, source_key, source_kind, trust_tier, schema_version, last_seen_at)
               VALUES ($1,$2,'internal',$3,$4,NOW())
               ON CONFLICT (tenant_id, source_key)
               DO UPDATE SET last_seen_at=NOW(), updated_at=NOW()""",
            tenant_id, source, _source_trust_tier(source),
            str(payload.get("schema_version") or "1"),
        )
        run_id = await conn.fetchval(
            """INSERT INTO signal_ingestion_runs
               (tenant_id, source_key, received_count, metadata)
               VALUES ($1,$2,1,$3::jsonb)
               RETURNING id""",
            tenant_id, source, json.dumps({"normalization_version": "1"}),
        )
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
            await conn.execute(
                "UPDATE signal_ingestion_runs SET duplicate_count=1, status='completed', completed_at=NOW() WHERE id=$1",
                run_id,
            )
            return {"status": "duplicate", "external_id": external_id}

        account_id = None
        if domain:
            account = await conn.fetchrow(
                """INSERT INTO accounts
                   (tenant_id, domain, canonical_domain, name, first_observed_at, last_observed_at)
                   VALUES ($1,$2,$2,$3,NOW(),NOW())
                   ON CONFLICT (tenant_id, domain)
                   DO UPDATE SET
                       name=COALESCE(EXCLUDED.name, accounts.name),
                       canonical_domain=EXCLUDED.canonical_domain,
                       last_observed_at=NOW(),
                       updated_at=NOW()
                   RETURNING id""",
                tenant_id, domain.lower(), company_name,
            )
            account_id = account["id"]
            await conn.execute(
                """INSERT INTO account_aliases
                   (tenant_id, account_id, source, external_id, observed_at, metadata)
                   VALUES ($1,$2,$3,$4,NOW(),$5::jsonb)
                   ON CONFLICT (tenant_id, source, external_id)
                   DO UPDATE SET account_id=EXCLUDED.account_id,
                                 observed_at=EXCLUDED.observed_at,
                                 metadata=EXCLUDED.metadata""",
                tenant_id, account_id, source, external_id,
                json.dumps({"company_name": company_name, "domain": domain}),
            )

        organization_id = None
        if domain:
            organization_id = await conn.fetchval(
                """INSERT INTO organizations
                   (tenant_id, name, website, domain, status)
                   VALUES ($1,$2,$3,$4,'prospect')
                   ON CONFLICT (tenant_id, domain)
                   DO UPDATE SET name=COALESCE(EXCLUDED.name, organizations.name),
                                 website=COALESCE(EXCLUDED.website, organizations.website),
                                 updated_at=NOW()
                   RETURNING id""",
                tenant_id, company_name, source_url, domain.lower(),
            )

        row = await conn.fetchrow(
            """INSERT INTO intelligence_signals
               (tenant_id, source, signal_type, company_name, domain, observed_at, score, evidence, external_id, source_url, confidence,
                normalized_type, signal_category, source_observed_at, freshness_expires_at, raw_payload_hash, normalization_version, normalization_status)
               VALUES ($1,$2,$3,$4,$5,COALESCE($6,NOW()),$7,$8::jsonb,$9,$10,$11,
                       $12,$13,COALESCE($6,NOW()),COALESCE($6,NOW()) + ($14 || ' days')::interval,$15,'1','normalized')
               ON CONFLICT (tenant_id, source, external_id) DO UPDATE
               SET signal_type=EXCLUDED.signal_type, company_name=EXCLUDED.company_name,
                   domain=EXCLUDED.domain, observed_at=EXCLUDED.observed_at,
                   score=EXCLUDED.score, evidence=EXCLUDED.evidence,
                   normalized_type=EXCLUDED.normalized_type, signal_category=EXCLUDED.signal_category,
                   source_url=EXCLUDED.source_url, source_observed_at=EXCLUDED.source_observed_at,
                   freshness_expires_at=EXCLUDED.freshness_expires_at,
                   raw_payload_hash=EXCLUDED.raw_payload_hash,
                   normalization_status='normalized'
               RETURNING id""",
            tenant_id, source, signal_type, company_name, domain, observed_at,
            score, json.dumps(evidence), external_id,
            source_url,
            min(0.95, 0.50 + score / 200),
            normalized_type, signal_category, freshness_days, raw_payload_hash,
        )

        await persist_signal_and_convergence(
            conn,
            tenant_id,
            organization_id,
            {
                "id": row["id"],
                "external_id": external_id,
                "source": source,
                "signal_type": signal_type,
                "normalized_type": normalized_type,
                "signal_category": signal_category,
                "score": score,
                "confidence": min(0.95, 0.50 + score / 200),
                "observed_at": observed_at,
                "source_url": source_url,
            },
            _source_trust_tier(source),
        )

        await persist_trajectory(conn, tenant_id, organization_id, normalized_type)

        if account_id:
            await conn.execute(
                """INSERT INTO account_signals
                   (tenant_id, account_id, source, signal_type, score, observed_at, evidence, external_id,
                    normalized_type, signal_category, source_url)
                   VALUES ($1,$2,$3,$4,$5,COALESCE($6,NOW()),$7::jsonb,$8,$9,$10,$11)
                   ON CONFLICT (tenant_id, source, external_id)
                   DO UPDATE SET score=EXCLUDED.score, observed_at=EXCLUDED.observed_at,
                                 evidence=EXCLUDED.evidence, normalized_type=EXCLUDED.normalized_type,
                                 signal_category=EXCLUDED.signal_category, source_url=EXCLUDED.source_url""",
                tenant_id, account_id, source, signal_type, score, observed_at,
                json.dumps(evidence), external_id, normalized_type, signal_category, source_url,
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

        await conn.execute(
            "UPDATE signal_ingestion_runs SET accepted_count=1, status='completed', completed_at=NOW() WHERE id=$1",
            run_id,
        )

    tenant_id_context.reset(tenant_ctx)
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
