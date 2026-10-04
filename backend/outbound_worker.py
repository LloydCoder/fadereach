"""Durable outbound execution worker.

Jobs are persisted in PostgreSQL. A process restart therefore does not lose
queued work. Claiming uses row locks and stale locks are recoverable.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import urllib.parse

import httpx
from cryptography.fernet import Fernet

from tenant_context import tenant_id_context
from routers.unsubscribe import create_unsubscribe_token


WORKER_ID = f"{socket.gethostname()}:{os.getpid()}"

class ExecutionCancelled(RuntimeError):
    """Terminal worker outcome: the campaign was intentionally stopped."""
POLL_SECONDS = float(os.getenv("OUTBOUND_WORKER_POLL_SECONDS", "2"))
LOCK_TIMEOUT_MINUTES = int(os.getenv("OUTBOUND_JOB_LOCK_TIMEOUT_MINUTES", "15"))


async def run_outbound_worker(db, queue_db=None) -> None:
    """Run durable outbound work with a narrowly privileged queue connection.

    queue_db is allowed to bypass RLS only for claiming execution_jobs. All
    tenant-owned work continues through the tenant-aware application pool.
    """
    queue_db = queue_db or db
    while True:
        try:
            job = await _claim_job(queue_db)
            if job:
                await _run_job(db, job)
            else:
                await asyncio.sleep(POLL_SECONDS)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"Outbound worker loop error: {exc}")
            await asyncio.sleep(POLL_SECONDS)


async def _claim_job(db):
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            """
            WITH candidate AS (
                SELECT id
                FROM execution_jobs
                WHERE (
                    status = 'queued'
                    AND next_attempt_at <= NOW()
                ) OR (
                    status = 'running'
                    AND locked_at < NOW() - ($1 || ' minutes')::interval
                )
                ORDER BY next_attempt_at, created_at
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            UPDATE execution_jobs j
            SET status='running',
                attempts = j.attempts + 1,
                locked_at=NOW(),
                locked_by=$2,
                updated_at=NOW()
            FROM candidate
            WHERE j.id=candidate.id
            RETURNING j.id, j.tenant_id, j.execution_id, j.attempts, j.max_attempts
            """,
            LOCK_TIMEOUT_MINUTES, WORKER_ID,
        )
    return dict(row) if row else None


async def _run_job(db, job: dict) -> None:
    token = tenant_id_context.set(job["tenant_id"])
    try:
        await _execute(db, job)
        async with db.acquire() as conn:
            await conn.execute(
                """
                UPDATE execution_jobs
                SET status='succeeded', completed_at=NOW(),
                    locked_at=NULL, locked_by=NULL, updated_at=NOW()
                WHERE id=$1
                """,
                job["id"],
            )
    except ExecutionCancelled as exc:
        error = str(exc)[:2000]
        async with db.acquire() as conn:
            await conn.execute(
                """
                UPDATE execution_jobs
                SET status='cancelled', completed_at=NOW(),
                    locked_at=NULL, locked_by=NULL, last_error=$2, updated_at=NOW()
                WHERE id=$1
                """,
                job["id"], error,
            )
            await conn.execute(
                """
                UPDATE campaign_executions
                SET status='cancelled', cancel_requested=TRUE,
                    error_message=$2, completed_at=NOW(), updated_at=NOW()
                WHERE id=$1
                """,
                job["execution_id"], error,
            )
    except Exception as exc:
        error = str(exc)[:2000]
        terminal = job["attempts"] >= job["max_attempts"]
        delay = min(3600, 2 ** max(0, job["attempts"] - 1) * 30)
        async with db.acquire() as conn:
            await conn.execute(
                """
                UPDATE execution_jobs
                SET status=$2,
                    next_attempt_at=NOW() + ($3 || ' seconds')::interval,
                    locked_at=NULL, locked_by=NULL,
                    last_error=$4, updated_at=NOW(),
                    completed_at=CASE WHEN $2='failed' THEN NOW() ELSE completed_at END
                WHERE id=$1
                """,
                job["id"], "failed" if terminal else "queued", delay, error,
            )
            await conn.execute(
                """
                UPDATE campaign_executions
                SET status=$2,
                    error_count=CASE WHEN $2='failed' THEN recipient_count ELSE error_count END,
                    error_message=$3,
                    completed_at=CASE WHEN $2='failed' THEN NOW() ELSE completed_at END
                WHERE id=$1
                """,
                job["execution_id"], "failed" if terminal else "queued", error,
            )
    finally:
        tenant_id_context.reset(token)


async def _execute(db, job: dict) -> None:
    async with db.acquire() as conn:
        execution = await conn.fetchrow(
            """
            SELECT ce.id, ce.tenant_id, ce.campaign_id, ce.cancel_requested,
                   ce.provider_connection_id, c.name, c.subject, c.status AS campaign_status,
                   c.body_html, pc.base_url, pc.api_username,
                   pc.api_token_ciphertext, pc.from_email
            FROM campaign_executions ce
            JOIN campaigns c ON c.id=ce.campaign_id
                         AND c.tenant_id=ce.tenant_id
            JOIN provider_connections pc
              ON pc.id=ce.provider_connection_id
             AND pc.tenant_id=ce.tenant_id
            WHERE ce.id=$1 AND ce.tenant_id=$2
            """,
            job["execution_id"], job["tenant_id"],
        )
        if not execution:
            raise RuntimeError("Execution or provider no longer exists")
        if execution["cancel_requested"] or execution["campaign_status"] in {"paused", "cancelled"}:
            raise ExecutionCancelled("Outbound execution cancelled before provider submission")

        leads = await conn.fetch(
            """
            SELECT l.id, l.email, l.first_name, l.last_name, l.company, l.ai_first_line
            FROM leads l
            WHERE l.tenant_id=$1
              AND l.status NOT IN ('replied','replied_positive','unsubscribed','bounced')
              AND COALESCE(l.lawful_basis, '') NOT IN ('', 'unknown')
              AND l.objection_status <> 'objected'
              AND (
                  l.subscriber_type = 'corporate'
                  OR (l.subscriber_type IN ('individual','sole_trader','partnership') AND l.consent_status = 'consented')
              )
              AND NOT EXISTS (
                  SELECT 1 FROM suppression_entries s
                  WHERE s.tenant_id=l.tenant_id
                    AND lower(s.email)=lower(l.email)
              )
            ORDER BY l.id
            LIMIT 10000
            """,
            job["tenant_id"],
        )
        if not leads:
            raise RuntimeError("No eligible recipients remain")

        blocked = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM domains
            WHERE tenant_id=$1
              AND (
                  sending_paused=TRUE
                  OR spf_valid=FALSE
                  OR dkim_valid=FALSE
                  OR dmarc_valid=FALSE
                  OR mx_valid=FALSE
                  OR bounce_rate > 1.5
                  OR complaint_rate > 0.05
              )
            """,
            job["tenant_id"],
        )
        if blocked:
            raise RuntimeError("Deliverability guardrail blocked execution")

        await conn.execute(
            """
            UPDATE campaign_executions
            SET status='running', started_at=COALESCE(started_at,NOW()),
                recipient_count=$2
            WHERE id=$1
            """,
            job["execution_id"], len(leads),
        )

    provider = dict(execution)
    auth = (
        provider["api_username"],
        _decrypt_provider_token(provider["api_token_ciphertext"]),
    )
    base = provider["base_url"].rstrip("/")
    list_name = f"FadeReach execution {job['execution_id']}"
    campaign_name = f"FadeReach campaign {execution['name']} #{job['execution_id']}"

    async with httpx.AsyncClient(timeout=20.0) as client:
        list_id = await _ensure_list(client, base, auth, list_name)
        for lead in leads:
            await _ensure_subscriber(
                client, base, auth, list_id, dict(lead), job["tenant_id"]
            )

        body = _to_listmonk_template(execution["body_html"])
        body += '\n\n<p><a href="https://fadereach.app/unsubscribe/one-click?token={{ .Subscriber.Attribs.unsubscribe_token }}">Unsubscribe</a></p>'
        external_id = await _ensure_campaign(
            client,
            base,
            auth,
            campaign_name,
            execution["subject"],
            provider["from_email"],
            list_id,
            body,
        )

        async with db.acquire() as conn:
            await conn.execute(
                """
                UPDATE campaign_executions
                SET status='succeeded', external_campaign_id=$1,
                    sent_count=0, completed_at=NOW(), error_message=NULL
                WHERE id=$2 AND tenant_id=$3
                """,
                external_id, job["execution_id"], job["tenant_id"],
            )
            await conn.execute(
                """
                UPDATE campaigns SET status='active', updated_at=NOW()
                WHERE id=$1 AND tenant_id=$2
                """,
                execution["campaign_id"], job["tenant_id"],
            )
            await conn.execute(
                """
                INSERT INTO messages
                    (tenant_id, campaign_id, execution_id, lead_id,
                     recipient_email, subject, status, sent_at)
                SELECT $1,$2,$3,l.id,l.email,$4,'submitted',NOW()
                FROM leads l
                WHERE l.tenant_id=$1
                  AND l.status NOT IN ('replied','replied_positive','unsubscribed','bounced')
                  AND COALESCE(l.lawful_basis, '') NOT IN ('', 'unknown')
                  AND l.objection_status <> 'objected'
                  AND (
                      l.subscriber_type = 'corporate'
                      OR (l.subscriber_type IN ('individual','sole_trader','partnership') AND l.consent_status = 'consented')
                  )
                  AND NOT EXISTS (
                      SELECT 1 FROM suppression_entries s
                      WHERE s.tenant_id=l.tenant_id
                        AND lower(s.email)=lower(l.email)
                  )
                ON CONFLICT DO NOTHING
                """,
                job["tenant_id"], execution["campaign_id"],
                job["execution_id"], execution["subject"],
            )


async def _ensure_list(client, base, auth, name: str) -> int:
    query = urllib.parse.quote(name)
    response = await client.get(
        f"{base}/api/lists?query={query}&per_page=100&minimal=true",
        auth=auth,
    )
    if response.status_code >= 300:
        raise RuntimeError(f"Listmonk list lookup failed: HTTP {response.status_code}")
    for item in response.json().get("data", {}).get("results", []):
        if item.get("name") == name:
            return int(item["id"])

    response = await client.post(
        f"{base}/api/lists",
        auth=auth,
        json={"name": name, "type": "private", "optin": "single", "status": "active"},
    )
    if response.status_code >= 300:
        # Another worker may have created it after the lookup.
        retry = await client.get(
            f"{base}/api/lists?query={query}&per_page=100&minimal=true",
            auth=auth,
        )
        for item in retry.json().get("data", {}).get("results", []):
            if item.get("name") == name:
                return int(item["id"])
        raise RuntimeError(f"Listmonk list creation failed: HTTP {response.status_code}")
    return int(response.json()["data"]["id"])


async def _ensure_subscriber(client, base, auth, list_id: int, lead: dict, tenant_id: str) -> None:
    email = lead["email"].strip().lower()
    query = urllib.parse.quote(f"subscribers.email = '{email.replace(chr(39), chr(39)*2)}'")
    response = await client.get(
        f"{base}/api/subscribers?query={query}&per_page=1",
        auth=auth,
    )
    if response.status_code >= 300:
        raise RuntimeError(f"Listmonk subscriber lookup failed: HTTP {response.status_code}")

    existing = response.json().get("data", {}).get("results", [])
    payload = {
        "email": email,
        "name": " ".join(
            x for x in [lead.get("first_name") or "", lead.get("last_name") or ""]
            if x
        ).strip() or email,
        "status": "enabled",
        "lists": [list_id],
        "preconfirm_subscriptions": True,
        "attribs": {
            "company": lead.get("company") or "",
            "ai_first_line": lead.get("ai_first_line") or "",
            "fade_reach_lead_id": lead["id"],
            "unsubscribe_token": create_unsubscribe_token(tenant_id, email),
        },
    }

    if existing:
        subscriber_id = existing[0]["id"]
        response = await client.patch(
            f"{base}/api/subscribers/{subscriber_id}",
            auth=auth,
            json=payload,
        )
    else:
        response = await client.post(
            f"{base}/api/subscribers",
            auth=auth,
            json=payload,
        )
    if response.status_code >= 300:
        raise RuntimeError(
            f"Listmonk subscriber upsert failed: HTTP {response.status_code}"
        )


async def _ensure_campaign(
    client, base, auth, name: str, subject: str,
    from_email: str, list_id: int, body: str
) -> int:
    query = urllib.parse.quote(name)
    response = await client.get(
        f"{base}/api/campaigns?query={query}&per_page=100&no_body=true",
        auth=auth,
    )
    if response.status_code >= 300:
        raise RuntimeError(f"Listmonk campaign lookup failed: HTTP {response.status_code}")

    existing = next(
        (x for x in response.json().get("data", {}).get("results", [])
         if x.get("name") == name),
        None,
    )
    if existing:
        campaign_id = int(existing["id"])
        status = existing.get("status")
        if status not in {"running", "scheduled", "paused"}:
            response = await client.put(
                f"{base}/api/campaigns/{campaign_id}",
                auth=auth,
                json={
                    "name": name, "subject": subject, "lists": [list_id],
                    "from_email": from_email, "content_type": "html",
                    "messenger": "email", "type": "regular", "body": body,
                    "headers": [
                        {"List-Unsubscribe": "<https://fadereach.app/unsubscribe/one-click?token={{ .Subscriber.Attribs.unsubscribe_token }}>"},
                        {"List-Unsubscribe-Post": "List-Unsubscribe=One-Click"},
                    ],
                },
            )
            if response.status_code >= 300:
                raise RuntimeError(
                    f"Listmonk campaign update failed: HTTP {response.status_code}"
                )
        if status != "running":
            response = await client.put(
                f"{base}/api/campaigns/{campaign_id}/status",
                auth=auth, json={"status": "running"},
            )
            if response.status_code >= 300:
                raise RuntimeError(
                    f"Listmonk campaign start failed: HTTP {response.status_code}"
                )
        return campaign_id

    response = await client.post(
        f"{base}/api/campaigns",
        auth=auth,
        json={
            "name": name,
            "subject": subject,
            "lists": [list_id],
            "from_email": from_email,
            "content_type": "html",
            "messenger": "email",
            "type": "regular",
            "body": body,
            "headers": [
                {"List-Unsubscribe": "<{{ UnsubscribeURL }}>"},
                {"List-Unsubscribe-Post": "List-Unsubscribe=One-Click"},
            ],
        },
    )
    if response.status_code >= 300:
        retry = await client.get(
            f"{base}/api/campaigns?query={query}&per_page=100&no_body=true",
            auth=auth,
        )
        existing = next(
            (x for x in retry.json().get("data", {}).get("results", [])
             if x.get("name") == name),
            None,
        )
        if existing:
            return await _ensure_campaign(
                client, base, auth, name, subject, from_email, list_id, body
            )
        raise RuntimeError(
            f"Listmonk campaign creation failed: HTTP {response.status_code}"
        )
    campaign_id = int(response.json()["data"]["id"])
    response = await client.put(
        f"{base}/api/campaigns/{campaign_id}/status",
        auth=auth, json={"status": "running"},
    )
    if response.status_code >= 300:
        raise RuntimeError(
            f"Listmonk campaign start failed: HTTP {response.status_code}"
        )
    return campaign_id


def _decrypt_provider_token(ciphertext: str) -> str:
    key = os.getenv("CREDENTIAL_ENCRYPTION_KEY", "")
    if not key:
        raise RuntimeError("Credential encryption is not configured")
    return Fernet(key.encode()).decrypt(ciphertext.encode()).decode()


def _to_listmonk_template(body: str) -> str:
    for source, target in {
        "{{first_name}}": "{{ .Subscriber.FirstName }}",
        "{first_name}": "{{ .Subscriber.FirstName }}",
        "{{company}}": "{{ .Subscriber.Attribs.company }}",
        "{company}": "{{ .Subscriber.Attribs.company }}",
        "{{ai_first_line}}": "{{ .Subscriber.Attribs.ai_first_line }}",
        "{ai_first_line}": "{{ .Subscriber.Attribs.ai_first_line }}",
    }.items():
        body = body.replace(source, target)
    return body
