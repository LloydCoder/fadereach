async def claim_jobs(conn,tenant_id:str,limit:int=50):
 return await conn.fetch("""UPDATE outbound_jobs SET status='leased',lease_until=NOW()+INTERVAL '5 minutes',updated_at=NOW() WHERE id IN(SELECT id FROM outbound_jobs WHERE tenant_id=$1 AND status='queued' AND available_at<=NOW() ORDER BY available_at,id FOR UPDATE SKIP LOCKED LIMIT $2) RETURNING id,payload""",tenant_id,limit)
