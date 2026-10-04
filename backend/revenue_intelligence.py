"""Revenue attribution and metric aggregation helpers."""

from __future__ import annotations


async def attribute_revenue(conn, tenant_id: str, revenue_id: int, sources: list[dict]) -> int:
    inserted = 0
    for source in sources:
        await conn.execute(
            """INSERT INTO revenue_attributions
               (tenant_id, revenue_id, source_type, source_id, attribution_type, weight, evidence_refs)
               VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb)
               ON CONFLICT DO NOTHING""",
            tenant_id, revenue_id, source["source_type"], int(source["source_id"]),
            source.get("attribution_type", "influenced"),
            max(0.0, min(1.0, float(source.get("weight", 0)))),
            source.get("evidence_refs", []),
        )
        inserted += 1
    return inserted


async def refresh_daily_revenue_metrics(conn, tenant_id: str, metric_date) -> dict:
    row = await conn.fetchrow(
        """SELECT
             (SELECT COUNT(*) FROM opportunities WHERE tenant_id=$1 AND created_at::date=$2) AS opportunities_created,
             (SELECT COUNT(*) FROM meetings WHERE tenant_id=$1 AND scheduled_at::date=$2 AND status='held') AS meetings_held,
             (SELECT COUNT(*) FROM deals WHERE tenant_id=$1 AND closed_at::date=$2 AND stage='won') AS deals_won,
             (SELECT COALESCE(SUM(amount),0) FROM revenue WHERE tenant_id=$1 AND recognized_at::date=$2) AS revenue_amount,
             (SELECT COALESCE(SUM(r.amount * a.weight),0) FROM revenue r JOIN revenue_attributions a ON a.revenue_id=r.id
              WHERE r.tenant_id=$1 AND r.recognized_at::date=$2 AND a.attribution_type='sourced') AS sourced_revenue,
             (SELECT COALESCE(SUM(r.amount * a.weight),0) FROM revenue r JOIN revenue_attributions a ON a.revenue_id=r.id
              WHERE r.tenant_id=$1 AND r.recognized_at::date=$2 AND a.attribution_type='influenced') AS influenced_revenue""",
        tenant_id, metric_date,
    )
    opp = int(row["opportunities_created"])
    meetings = int(row["meetings_held"])
    wins = int(row["deals_won"])
    result = {
        "opportunities_created": opp,
        "meetings_held": meetings,
        "deals_won": wins,
        "revenue_amount": float(row["revenue_amount"]),
        "sourced_revenue": float(row["sourced_revenue"]),
        "influenced_revenue": float(row["influenced_revenue"]),
        "signal_to_opportunity_rate": 0.0,
        "opportunity_to_meeting_rate": meetings / opp if opp else 0.0,
        "meeting_to_won_rate": wins / meetings if meetings else 0.0,
    }
    await conn.execute(
        """INSERT INTO revenue_metrics_daily
           (tenant_id, metric_date, opportunities_created, meetings_held, deals_won,
            revenue_amount, sourced_revenue, influenced_revenue,
            signal_to_opportunity_rate, opportunity_to_meeting_rate, meeting_to_won_rate)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
           ON CONFLICT (tenant_id, metric_date)
           DO UPDATE SET opportunities_created=EXCLUDED.opportunities_created,
                         meetings_held=EXCLUDED.meetings_held, deals_won=EXCLUDED.deals_won,
                         revenue_amount=EXCLUDED.revenue_amount,
                         sourced_revenue=EXCLUDED.sourced_revenue,
                         influenced_revenue=EXCLUDED.influenced_revenue,
                         opportunity_to_meeting_rate=EXCLUDED.opportunity_to_meeting_rate,
                         meeting_to_won_rate=EXCLUDED.meeting_to_won_rate,
                         updated_at=NOW()""",
        tenant_id, metric_date, opp, meetings, wins, result["revenue_amount"],
        result["sourced_revenue"], result["influenced_revenue"],
        result["signal_to_opportunity_rate"], result["opportunity_to_meeting_rate"],
        result["meeting_to_won_rate"],
    )
    return result
