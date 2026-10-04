"""Low-dependency operational metrics for the FadeReach control plane."""
from __future__ import annotations

import time

STARTED_AT = time.time()


def prometheus_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


async def collect_metrics(app) -> str:
    lines = [
        "# HELP fadereach_process_uptime_seconds Process uptime.",
        "# TYPE fadereach_process_uptime_seconds gauge",
        f"fadereach_process_uptime_seconds {time.time() - STARTED_AT:.3f}",
    ]
    try:
        async with app.state.db.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT status, COUNT(*)::bigint AS count
                FROM execution_jobs
                GROUP BY status
                ORDER BY status
                """
            )
            for row in rows:
                status = prometheus_escape(str(row["status"]))
                lines.append(f'fadereach_execution_jobs{{status="{status}"}} {row["count"]}')
            paused = await conn.fetchval(
                "SELECT COUNT(*) FROM domains WHERE sending_paused=TRUE"
            )
            lines.append(f"fadereach_paused_sending_domains {paused}")
    except Exception:
        lines.append("fadereach_database_metrics_available 0")
    else:
        lines.append("fadereach_database_metrics_available 1")
    return "\n".join(lines) + "\n"
