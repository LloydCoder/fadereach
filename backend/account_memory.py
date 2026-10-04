"""Persistent account memory refresh built from canonical commercial state."""

from __future__ import annotations

import hashlib
import json


def _fingerprint(memory_type: str, content: dict) -> str:
    raw = json.dumps({"type": memory_type, "content": content}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


async def refresh_account_memory(conn, tenant_id: str, account_id: int, organization_id: int | None) -> dict:
    entries = []
    why_now = await conn.fetchrow(
        """SELECT id, what_changed, why_now, confidence, evidence_refs, evaluated_at
           FROM why_now_assessments WHERE tenant_id=$1 AND account_id=$2
           ORDER BY evaluated_at DESC LIMIT 1""",
        tenant_id, account_id,
    )
    if why_now:
        entries.append(("hypothesis", {
            "kind": "why_now",
            "assessment_id": why_now["id"],
            "what_changed": why_now["what_changed"],
            "why_now": why_now["why_now"],
        }, float(why_now["confidence"] or 0), why_now["evidence_refs"] or [], [why_now["id"]]))

    opportunities = await conn.fetch(
        """SELECT id, name, stage, score, confidence, estimated_value, currency, updated_at
           FROM opportunities WHERE tenant_id=$1 AND organization_id=$2
           ORDER BY updated_at DESC LIMIT 20""",
        tenant_id, organization_id,
    ) if organization_id else []
    for opportunity in opportunities:
        entries.append(("outcome", {
            "kind": "opportunity",
            "opportunity_id": opportunity["id"],
            "name": opportunity["name"],
            "stage": opportunity["stage"],
            "score": opportunity["score"],
        }, float(opportunity["confidence"] or 0), [], [opportunity["id"]]))

    signals = await conn.fetch(
        """SELECT id, normalized_type, signal_category, strength, confidence, last_seen_at
           FROM signals WHERE tenant_id=$1 AND organization_id=$2
           ORDER BY last_seen_at DESC LIMIT 50""",
        tenant_id, organization_id,
    ) if organization_id else []
    for signal in signals:
        entries.append(("signal", {
            "kind": "signal",
            "signal_id": signal["id"],
            "normalized_type": signal["normalized_type"],
            "category": signal["signal_category"],
            "strength": signal["strength"],
            "last_seen_at": signal["last_seen_at"].isoformat() if signal["last_seen_at"] else None,
        }, float(signal["confidence"] or 0), [], [signal["id"]]))

    for memory_type, content, confidence, evidence_refs, source_refs in entries:
        fingerprint = _fingerprint(memory_type, content)
        await conn.execute(
            """INSERT INTO account_memory_entries
               (tenant_id, account_id, memory_type, content, fingerprint, confidence, evidence_refs, source_refs)
               VALUES ($1,$2,$3,$4::jsonb,$5,$6,$7::jsonb,$8::jsonb)
               ON CONFLICT (tenant_id, account_id, fingerprint)
               DO UPDATE SET confidence=EXCLUDED.confidence,
                             evidence_refs=EXCLUDED.evidence_refs,
                             source_refs=EXCLUDED.source_refs,
                             updated_at=NOW()""",
            tenant_id, account_id, memory_type, content, fingerprint,
            confidence, evidence_refs, source_refs,
        )
    return {"account_id": account_id, "entries_refreshed": len(entries)}
