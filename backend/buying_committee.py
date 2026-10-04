"""Deterministic buying committee role inference."""

from __future__ import annotations

ROLE_RULES = {
    "economic_buyer": ("ceo", "cfo", "chief executive", "chief financial", "president", "owner", "founder"),
    "technical_buyer": ("cto", "chief technology", "chief information", "vp engineering", "vp technology", "engineering", "platform", "architecture", "it director"),
    "security": ("ciso", "security", "information security", "risk"),
    "procurement": ("procurement", "purchasing", "vendor management", "sourcing"),
    "finance": ("finance", "controller", "fp&a", "financial"),
    "champion": ("product", "engineering manager", "director of engineering", "innovation"),
    "influencer": ("advisor", "consultant", "architect", "manager", "lead"),
    "blocker": ("legal", "compliance", "privacy"),
}


def infer_roles(title: str | None) -> list[tuple[str, float]]:
    value = (title or "").lower()
    matches = []
    for role, keywords in ROLE_RULES.items():
        score = max((0.9 - 0.05 * i for i, keyword in enumerate(keywords) if keyword in value), default=0.0)
        if score:
            matches.append((role, round(min(score, 0.95), 4)))
    return sorted(matches, key=lambda x: x[1], reverse=True) or [("unknown", 0.25)]


async def persist_buying_committee(conn, tenant_id: str, opportunity_id: int, organization_id: int) -> dict:
    committee_id = await conn.fetchval(
        """INSERT INTO buying_committees(tenant_id, opportunity_id, status, confidence)
           VALUES ($1,$2,'active',0)
           ON CONFLICT (tenant_id, opportunity_id)
           DO UPDATE SET status='active', updated_at=NOW()
           RETURNING id""",
        tenant_id, opportunity_id,
    )
    people = await conn.fetch(
        """SELECT id, title FROM people
           WHERE tenant_id=$1 AND organization_id=$2 AND status <> 'suppressed'
           ORDER BY updated_at DESC LIMIT 100""",
        tenant_id, organization_id,
    )
    selected = []
    for person in people:
        for role, confidence in infer_roles(person["title"]):
            existing = await conn.fetchrow(
                """SELECT id FROM buying_committee_members
                   WHERE committee_id=$1 AND person_id=$2""",
                committee_id, person["id"],
            )
            if existing:
                member_id = existing["id"]
                await conn.execute(
                    """UPDATE buying_committee_members
                       SET role=$1, influence=$2, confidence=$3,
                           role_confidence=$3, last_verified_at=NOW(), status='inferred'
                       WHERE id=$4 AND tenant_id=$5""",
                    role, confidence, confidence, member_id, tenant_id,
                )
            else:
                member_id = await conn.fetchval(
                    """INSERT INTO buying_committee_members
                       (tenant_id, committee_id, person_id, role, influence, confidence, role_confidence, last_verified_at, status)
                       VALUES ($1,$2,$3,$4,$5,$5,$5,NOW(),'inferred')
                       RETURNING id""",
                    tenant_id, committee_id, person["id"], role, confidence,
                )
            selected.append({"person_id": person["id"], "role": role, "confidence": confidence})
    committee_confidence = max((x["confidence"] for x in selected), default=0)
    await conn.execute(
        "UPDATE buying_committees SET confidence=$1, updated_at=NOW() WHERE id=$2 AND tenant_id=$3",
        committee_confidence, committee_id, tenant_id,
    )
    return {"committee_id": committee_id, "members": selected, "confidence": committee_confidence}
