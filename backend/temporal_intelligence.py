"""Deterministic temporal intelligence for canonical signals."""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean


def compute_trajectory(points: list[dict]) -> dict:
    rows = sorted(
        [p for p in points if p.get("observed_at")],
        key=lambda p: p["observed_at"],
    )
    if not rows:
        return {"state": "unknown", "observation_count": 0, "confidence": 0.0}

    strengths = [float(p.get("strength") or 0) for p in rows]
    diffs = [strengths[i] - strengths[i - 1] for i in range(1, len(strengths))]
    velocity = mean(diffs) if diffs else 0.0
    acceleration = mean(
        [diffs[i] - diffs[i - 1] for i in range(1, len(diffs))]
    ) if len(diffs) > 1 else 0.0

    first = rows[0]["observed_at"]
    last = rows[-1]["observed_at"]
    if first.tzinfo is None:
        first = first.replace(tzinfo=timezone.utc)
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (datetime.now(timezone.utc) - last).total_seconds() / 86400)

    recurrence_count = 0
    for i in range(1, len(rows)):
        prev = rows[i - 1]["observed_at"]
        cur = rows[i]["observed_at"]
        if prev.tzinfo is None:
            prev = prev.replace(tzinfo=timezone.utc)
        if cur.tzinfo is None:
            cur = cur.replace(tzinfo=timezone.utc)
        if (cur - prev).total_seconds() >= 30 * 86400:
            recurrence_count += 1

    signs = [1 if d > 2 else -1 if d < -2 else 0 for d in diffs]
    reversal = any(signs[i] * signs[i - 1] < 0 for i in range(1, len(signs)))

    if age_days > 120:
        state = "decayed"
    elif reversal:
        state = "reversing"
    elif recurrence_count >= 2:
        state = "recurring"
    elif len(diffs) >= 2 and velocity > 0 and acceleration > 1:
        state = "accelerating"
    elif len(diffs) >= 2 and velocity < 0 and acceleration < -1:
        state = "decelerating"
    elif len(rows) >= 3 and abs(velocity) <= 5:
        state = "persistent"
    elif velocity > 5:
        state = "emerging"
    elif age_days > 60:
        state = "inactive"
    else:
        state = "unknown"

    trend_score = max(-100.0, min(100.0, velocity * 5 + acceleration * 2))
    confidence = min(0.95, 0.30 + 0.10 * min(len(rows), 5) + 0.05 * min(recurrence_count, 3))

    return {
        "state": state,
        "observation_count": len(rows),
        "recurrence_count": recurrence_count,
        "velocity": round(velocity, 4),
        "acceleration": round(acceleration, 4),
        "trend_score": round(trend_score, 4),
        "confidence": round(confidence, 4),
        "first_seen_at": first,
        "last_seen_at": last,
        "rationale": {
            "age_days": round(age_days, 2),
            "strengths": strengths,
            "diffs": diffs,
            "reversal": reversal,
        },
    }


async def persist_trajectory(conn, tenant_id: str, organization_id: int, normalized_type: str) -> dict:
    rows = await conn.fetch(
        """SELECT id, strength, last_seen_at AS observed_at
           FROM signals
           WHERE tenant_id=$1 AND organization_id=$2 AND normalized_type=$3
             AND last_seen_at >= NOW() - INTERVAL '365 days'
           ORDER BY last_seen_at ASC""",
        tenant_id, organization_id, normalized_type,
    )
    result = compute_trajectory([dict(r) for r in rows])
    if result["observation_count"] == 0:
        return result
    await conn.execute(
        """INSERT INTO signal_trajectories
           (tenant_id, organization_id, normalized_type, state, observation_count,
            recurrence_count, velocity, acceleration, trend_score, confidence,
            first_seen_at, last_seen_at, rationale, evaluated_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13::jsonb,NOW())
           ON CONFLICT (tenant_id, organization_id, normalized_type)
           DO UPDATE SET state=EXCLUDED.state, observation_count=EXCLUDED.observation_count,
                         recurrence_count=EXCLUDED.recurrence_count, velocity=EXCLUDED.velocity,
                         acceleration=EXCLUDED.acceleration, trend_score=EXCLUDED.trend_score,
                         confidence=EXCLUDED.confidence, first_seen_at=EXCLUDED.first_seen_at,
                         last_seen_at=EXCLUDED.last_seen_at, rationale=EXCLUDED.rationale,
                         evaluated_at=NOW()""",
        tenant_id, organization_id, normalized_type, result["state"],
        result["observation_count"], result["recurrence_count"], result["velocity"],
        result["acceleration"], result["trend_score"], result["confidence"],
        result["first_seen_at"], result["last_seen_at"], result["rationale"],
    )
    return result
