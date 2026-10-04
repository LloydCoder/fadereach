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
