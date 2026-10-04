"""Deterministic, evidence-backed Why-Now assessment engine."""

from __future__ import annotations

from datetime import datetime, timezone


def build_why_now(cluster: dict | None, trajectory: dict | None, evidence: list[dict]) -> dict:
    cluster = cluster or {}
    trajectory = trajectory or {}
    state = trajectory.get("state") or "unknown"
    signal_type = cluster.get("cluster_type") or "signal change"
    score = float(cluster.get("convergence_score") or 0)
    confidence = min(float(cluster.get("confidence") or 0), float(trajectory.get("confidence") or 1))
    last_seen = cluster.get("last_seen_at") or trajectory.get("last_seen_at")

    if state == "accelerating":
        why_now = "The signal is accelerating, indicating a changing condition rather than a static observation."
    elif state == "emerging":
        why_now = "The signal is newly emerging and may represent an active change window."
    elif state == "recurring":
        why_now = "The signal is recurring, indicating repeated organizational activity rather than a one-off event."
    elif state == "reversing":
        why_now = "The signal has reversed direction, so prior assumptions should be revalidated before action."
    elif state == "decayed":
        why_now = "The signal has materially aged; current relevance is uncertain without fresh corroboration."
    elif state == "persistent":
        why_now = "The signal persists over multiple observations, increasing confidence that the condition is durable."
    else:
        why_now = "The available temporal evidence is insufficient to establish a strong timing claim."

    unknowns = []
    if not evidence:
        unknowns.append("No canonical evidence records are linked to the current signal cluster.")
    if confidence < 0.55:
        unknowns.append("Confidence is below the recommended commercial-action threshold.")
    if state in {"unknown", "inactive", "decayed"}:
        unknowns.append("Current temporal state does not establish an active buying window.")

    return {
        "what_changed": f"Observed change in {signal_type}.",
        "when_changed": last_seen,
        "why_matters": f"The converged signal score is {score:.1f}/100 and the temporal state is {state}.",
        "why_now": why_now,
        "capability_required": signal_type,
        "confidence": round(confidence, 4),
        "unknowns": unknowns,
        "evidence_refs": [e["id"] for e in evidence if e.get("id")],
        "signal_cluster_ids": [cluster["id"]] if cluster.get("id") else [],
        "trajectory_states": [state],
    }


async def persist_why_now(conn, tenant_id: str, organization_id: int, account_id: int | None = None) -> dict:
    cluster = await conn.fetchrow(
        """SELECT id, cluster_type, convergence_score, confidence, last_seen_at
           FROM signal_clusters
           WHERE tenant_id=$1 AND organization_id=$2
           ORDER BY updated_at DESC LIMIT 1""",
        tenant_id, organization_id,
    )
    if not cluster:
        return {"status": "unknown", "reason": "no_signal_cluster"}

    trajectory = await conn.fetchrow(
        """SELECT state, confidence, last_seen_at
           FROM signal_trajectories
           WHERE tenant_id=$1 AND organization_id=$2 AND normalized_type=$3
           ORDER BY evaluated_at DESC LIMIT 1""",
        tenant_id, organization_id, cluster["cluster_type"],
    )
    evidence = await conn.fetch(
        """SELECT DISTINCT e.id, e.source, e.source_url, e.claim, e.observed_at, e.confidence
           FROM evidence e
           JOIN signal_evidence se ON se.evidence_id=e.id
           JOIN signals s ON s.id=se.signal_id
           WHERE e.tenant_id=$1 AND s.tenant_id=$1
             AND s.organization_id=$2 AND s.normalized_type=$3
             AND e.status='valid'
           ORDER BY e.observed_at DESC NULLS LAST
           LIMIT 50""",
        tenant_id, organization_id, cluster["cluster_type"],
    )
    result = build_why_now(dict(cluster), dict(trajectory) if trajectory else None, [dict(e) for e in evidence])
    await conn.execute(
        """INSERT INTO why_now_assessments
           (tenant_id, organization_id, account_id, what_changed, when_changed, why_matters,
            why_now, capability_required, confidence, unknowns, evidence_refs,
            signal_cluster_ids, trajectory_states, evaluated_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb,$11::jsonb,$12::jsonb,$13::jsonb,NOW())""",
        tenant_id, organization_id, account_id, result["what_changed"], result["when_changed"],
        result["why_matters"], result["why_now"], result["capability_required"],
        result["confidence"], result["unknowns"], result["evidence_refs"],
        result["signal_cluster_ids"], result["trajectory_states"],
    )
    return result
