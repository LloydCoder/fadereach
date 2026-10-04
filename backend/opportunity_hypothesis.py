"""Deterministic opportunity hypothesis generation."""

from __future__ import annotations


CAPABILITY_MAP = {
    "security": "cybersecurity engineering, security remediation and resilience",
    "technology": "cloud/platform modernization and engineering",
    "infrastructure": "infrastructure reliability and platform engineering",
    "ai": "AI engineering, governance and secure AI adoption",
    "workforce": "engineering capacity and delivery acceleration",
    "finance": "engineering execution aligned to growth/funding priorities",
    "expansion": "market/geo expansion engineering and operational readiness",
    "compliance": "compliance engineering and governance",
    "commercial": "product/revenue engineering and optimization",
    "procurement": "technical vendor evaluation and implementation",
}


def rank_hypothesis(why_now: dict, cluster: dict, trajectory: dict) -> dict:
    confidence = min(float(why_now.get("confidence") or 0), float(cluster.get("confidence") or 0.0))
    convergence = max(0.0, min(100.0, float(cluster.get("convergence_score") or 0)))
    fit = max(0.0, min(100.0, confidence * 100))
    impact = max(0.0, min(100.0, convergence * 0.75 + (25 if trajectory.get("state") in {"accelerating", "emerging"} else 0)))
    priority = round(fit * 0.35 + impact * 0.65, 3)
    return {
        "fit_score": round(fit, 3),
        "impact_score": round(impact, 3),
        "priority_score": priority,
        "confidence": round(confidence, 4),
    }


async def persist_opportunity_hypothesis(conn, tenant_id: str, organization_id: int, account_id: int | None = None) -> dict:
    why_now = await conn.fetchrow(
        """SELECT id, what_changed, why_matters, why_now, capability_required,
                  confidence, unknowns, evidence_refs, signal_cluster_ids, trajectory_states
           FROM why_now_assessments
           WHERE tenant_id=$1 AND organization_id=$2 AND status='active'
           ORDER BY evaluated_at DESC LIMIT 1""",
        tenant_id, organization_id,
    )
    if not why_now:
        return {"status": "unknown", "reason": "no_why_now_assessment"}

    cluster_id = (why_now["signal_cluster_ids"] or [None])[0]
    cluster = await conn.fetchrow(
        """SELECT id, cluster_type, convergence_score, confidence, last_seen_at
           FROM signal_clusters WHERE tenant_id=$1 AND id=$2""",
        tenant_id, cluster_id,
    )
    if not cluster:
        return {"status": "unknown", "reason": "no_signal_cluster"}

    trajectory = await conn.fetchrow(
        """SELECT state, confidence FROM signal_trajectories
           WHERE tenant_id=$1 AND organization_id=$2 AND normalized_type=$3
           ORDER BY evaluated_at DESC LIMIT 1""",
        tenant_id, organization_id, cluster["cluster_type"],
    ) or {"state": "unknown", "confidence": 0}

    ranked = rank_hypothesis(dict(why_now), dict(cluster), dict(trajectory))
    source_key = f"signal:{cluster['cluster_type']}"
    capability = CAPABILITY_MAP.get(
        cluster["cluster_type"].split("_")[0],
        "engineering capability matched to the observed organizational change",
    )
    opportunity = await conn.fetchrow(
        """INSERT INTO opportunities
           (tenant_id, organization_id, name, stage, source, source_key, score, confidence,
            fit_score, impact_score, priority_score, buying_window_start, attributes)
           VALUES ($1,$2,$3,'identified','signal_intelligence',$4,$5,$6,$7,$8,$9,NOW(),$10::jsonb)
           ON CONFLICT (tenant_id, organization_id, source_key)
           DO UPDATE SET score=EXCLUDED.score, confidence=EXCLUDED.confidence,
                         fit_score=EXCLUDED.fit_score, impact_score=EXCLUDED.impact_score,
                         priority_score=EXCLUDED.priority_score, updated_at=NOW(),
                         attributes=EXCLUDED.attributes
           RETURNING id""",
        tenant_id, organization_id,
        f"Signal-driven opportunity: {cluster['cluster_type']}",
        source_key, ranked["priority_score"], ranked["confidence"],
        ranked["fit_score"], ranked["impact_score"], ranked["priority_score"],
        {"why_now_assessment_id": why_now["id"]},
    )
    hypothesis = await conn.fetchrow(
        """INSERT INTO opportunity_hypotheses
           (tenant_id, opportunity_id, hypothesis_type, statement, capability, why_now,
            confidence, unknowns, why_now_assessment_id, fit_score, impact_score, priority_score, status)
           VALUES ($1,$2,'demand', $3,$4,$5,$6,$7::jsonb,$8,$9,$10,$11,'active')
           RETURNING id""",
        tenant_id, opportunity["id"],
        f"The observed {cluster['cluster_type']} change may create a near-term need for {capability}.",
        capability, why_now["why_now"], ranked["confidence"], why_now["unknowns"],
        why_now["id"], ranked["fit_score"], ranked["impact_score"], ranked["priority_score"],
    )
    for evidence_id in (why_now["evidence_refs"] or []):
        await conn.execute(
            """INSERT INTO hypothesis_evidence(hypothesis_id, evidence_id)
               VALUES ($1,$2) ON CONFLICT DO NOTHING""",
            hypothesis["id"], int(evidence_id),
        )
    if account_id:
        await conn.execute(
            """INSERT INTO account_graph_edges
               (tenant_id, account_id, source_type, source_id, target_type, target_id, relation, confidence, metadata)
               VALUES ($1,$2,'account',$2,'opportunity',$3,'candidate_opportunity',$4,$5::jsonb)
               ON CONFLICT (tenant_id, source_type, source_id, relation, target_type, target_id)
               DO UPDATE SET confidence=EXCLUDED.confidence, metadata=EXCLUDED.metadata, updated_at=NOW()""",
            tenant_id, account_id, opportunity["id"], ranked["confidence"],
            {"source": "phase8", "hypothesis_id": hypothesis["id"]},
        )
    return {
        "opportunity_id": opportunity["id"],
        "hypothesis_id": hypothesis["id"],
        **ranked,
        "capability": capability,
        "status": "accepted",
    }
