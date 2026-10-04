"""Evidence-backed message learning primitives."""
async def record_message_outcome(conn, tenant_id, payload):
 return await conn.fetchval("""INSERT INTO message_intelligence_events
 (tenant_id,message_id,campaign_id,person_id,opportunity_id,signal_type,persona,hypothesis_type,industry,country,stage,timing,channel,response,objection,meeting_outcome,revenue_outcome,evidence_refs,metadata)
 VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18::jsonb,$19::jsonb) RETURNING id""",tenant_id,payload.get("message_id"),payload.get("campaign_id"),payload.get("person_id"),payload.get("opportunity_id"),payload.get("signal_type"),payload.get("persona"),payload.get("hypothesis_type"),payload.get("industry"),payload.get("country"),payload.get("stage"),payload.get("timing"),payload.get("channel"),payload.get("response"),payload.get("objection"),payload.get("meeting_outcome"),payload.get("revenue_outcome"),payload.get("evidence_refs",[]),payload.get("metadata",{}))
