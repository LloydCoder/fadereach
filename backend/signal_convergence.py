"""Deterministic signal convergence engine.

No LLM authority: convergence is derived from source independence, signal strength,
recency/decay and explicit polarity. The output is explainable and reproducible.
"""

from __future__ import annotations

from datetime import datetime, timezone
from math import exp
from typing import Iterable

SOURCE_WEIGHTS = {"T0": 1.0, "T1": 0.95, "T2": 0.80, "T3": 0.65, "T4": 0.50, "T5": 0.30}
DECAY_HALFLIFE_DAYS = 45.0


def _source_weight(trust_tier: str | None) -> float:
    return SOURCE_WEIGHTS.get((trust_tier or "T2").upper(), 0.80)


def _recency_weight(observed_at: datetime | None, now: datetime | None = None) -> float:
    if not observed_at:
        return 0.25
    now = now or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (now - observed_at).total_seconds() / 86400)
    return exp(-0.69314718056 * age_days / DECAY_HALFLIFE_DAYS)


def compute_convergence(signals: Iterable[dict], now: datetime | None = None) -> dict:
    rows = list(signals)
    if not rows:
        return {
            "convergence_score": 0.0,
            "confidence": 0.0,
            "independent_source_count": 0,
            "contradiction_count": 0,
            "support_score": 0.0,
            "contradiction_score": 0.0,
            "state": "candidate",
        }

    now = now or datetime.now(timezone.utc)
    sources: set[str] = set()
    support = 0.0
    contradiction = 0.0
    contributions = []

    for row in rows:
        source = str(row.get("source") or row.get("source_independence_key") or "unknown")
        sources.add(source)
        trust = _source_weight(row.get("trust_tier"))
        strength = max(0.0, min(100.0, float(row.get("strength", row.get("score", 0)))))
        recency = _recency_weight(row.get("last_seen_at") or row.get("observed_at"), now)
        contribution = strength * trust * recency
        polarity = -1 if int(row.get("polarity", 1)) < 0 else 1
        if polarity < 0:
            contradiction += contribution
        else:
            support += contribution
        contributions.append({
            "signal_id": row.get("id"),
            "source": source,
            "contribution": round(contribution, 4),
            "polarity": polarity,
            "recency_weight": round(recency, 4),
        })

    independence_factor = min(1.0, 0.5 + 0.15 * len(sources))
    net = max(0.0, support - contradiction * 0.75)
    score = min(100.0, net * independence_factor)
    confidence = min(0.99, max(0.05, (0.25 + 0.12 * len(sources)) * (0.5 + min(0.5, net / 100))))
    state = "active" if score >= 45 and confidence >= 0.55 else "candidate"
    if contradiction > support and contradiction > 20:
        state = "invalid"

    return {
        "convergence_score": round(score, 3),
        "confidence": round(confidence, 4),
        "independent_source_count": len(sources),
        "contradiction_count": sum(1 for r in rows if int(r.get("polarity", 1)) < 0),
        "support_score": round(support, 3),
        "contradiction_score": round(contradiction, 3),
        "state": state,
        "contributions": contributions,
    }


async def persist_signal_and_convergence(conn, tenant_id: str, organization_id: int, signal_row: dict, trust_tier: str = "T2") -> dict:
    """Persist one canonical signal and recompute its organization/type cluster."""
    normalized_type = signal_row.get("normalized_type") or signal_row.get("signal_type") or "unknown"
    external_id = signal_row.get("external_id")
    source = signal_row.get("source") or "unknown"
    observed_at = signal_row.get("observed_at")
    score = max(0.0, min(100.0, float(signal_row.get("score") or 0)))
    async with conn.transaction():
        existing = await conn.fetchrow(
            """SELECT id, first_seen_at FROM signals
               WHERE tenant_id=$1 AND organization_id=$2 AND normalized_type=$3
                 AND source=$4 AND attributes->>'external_id'=$5
               LIMIT 1""",
            tenant_id, organization_id, normalized_type, source, external_id or "",
        )
        if existing:
            signal_id = existing["id"]
            await conn.execute(
                """UPDATE signals
                   SET strength=$1, confidence=$2, last_seen_at=$3,
                       source_independence_key=$4, signal_category=$5,
                       attributes=attributes || $6::jsonb, updated_at=NOW()
                   WHERE id=$7 AND tenant_id=$8""",
                score, float(signal_row.get("confidence") or 0),
                observed_at or datetime.now(timezone.utc),
                source, signal_row.get("signal_category") or "other",
                {"external_id": external_id, "source_url": signal_row.get("source_url")},
                signal_id, tenant_id,
            )
        else:
            signal_id = await conn.fetchval(
                """INSERT INTO signals
                   (tenant_id, organization_id, source, normalized_type, signal_category,
                    source_independence_key, polarity, strength, confidence,
                    first_seen_at, last_seen_at, attributes)
                   VALUES ($1,$2,$3,$4,$5,$3,1,$6,$7,
                           COALESCE($8,NOW()),COALESCE($8,NOW()),$9::jsonb)
                   RETURNING id""",
                tenant_id, organization_id, source, normalized_type,
                signal_row.get("signal_category") or "other", score,
                float(signal_row.get("confidence") or 0),
                observed_at,
                {"external_id": external_id, "source_url": signal_row.get("source_url")},
            )

        rows = await conn.fetch(
            """SELECT s.id, s.source, s.strength, s.polarity, s.last_seen_at,
                      s.confidence, ss.trust_tier
               FROM signals s
               LEFT JOIN signal_sources ss
                 ON ss.tenant_id=s.tenant_id AND ss.source_key=s.source
               WHERE s.tenant_id=$1 AND s.organization_id=$2
                 AND s.normalized_type=$3
                 AND s.last_seen_at >= NOW() - INTERVAL '90 days'
               ORDER BY s.last_seen_at DESC""",
            tenant_id, organization_id, normalized_type,
        )
        result = compute_convergence([dict(row) for row in rows])
        cluster = await conn.fetchrow(
            """SELECT id FROM signal_clusters
               WHERE tenant_id=$1 AND organization_id=$2 AND cluster_type=$3
               ORDER BY updated_at DESC LIMIT 1
               FOR UPDATE""",
            tenant_id, organization_id, normalized_type,
        )
        if cluster:
            cluster_id = cluster["id"]
            await conn.execute(
                """UPDATE signal_clusters
                   SET convergence_score=$1, confidence=$2,
                       independent_source_count=$3, state=$4,
                       contradiction_count=$5, decay_score=$6,
                       rationale=$7::jsonb, last_seen_at=NOW(), evaluated_at=NOW(),
                       updated_at=NOW()
                   WHERE id=$8 AND tenant_id=$9""",
                result["convergence_score"], result["confidence"],
                result["independent_source_count"], result["state"],
                result["contradiction_count"], result["contradiction_score"],
                result, cluster_id, tenant_id,
            )
        else:
            cluster_id = await conn.fetchval(
                """INSERT INTO signal_clusters
                   (tenant_id, organization_id, cluster_type, convergence_score, confidence,
                    independent_source_count, state, first_seen_at, last_seen_at,
                    contradiction_count, decay_score, rationale, evaluated_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,NOW(),NOW(),$8,$9,$10::jsonb,NOW())
                   RETURNING id""",
                tenant_id, organization_id, normalized_type,
                result["convergence_score"], result["confidence"],
                result["independent_source_count"], result["state"],
                result["contradiction_count"], result["contradiction_score"],
                result,
            )
        await conn.execute("DELETE FROM signal_cluster_members WHERE cluster_id=$1", cluster_id)
        for item in result["contributions"]:
            if item.get("signal_id"):
                await conn.execute(
                    """INSERT INTO signal_cluster_members(cluster_id, signal_id, contribution)
                       VALUES ($1,$2,$3)
                       ON CONFLICT (cluster_id, signal_id)
                       DO UPDATE SET contribution=EXCLUDED.contribution""",
                    cluster_id, item["signal_id"], item["contribution"],
                )
    return {"signal_id": signal_id, "cluster_id": cluster_id, **result}
