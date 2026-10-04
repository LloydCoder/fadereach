# Automation and Scheduled Work

Scheduled jobs must be idempotent, bounded and observable. Every recurring task needs an owner, purpose, schedule, retry policy, timeout and failure signal.

Jobs that can create outbound activity must re-evaluate authorization, suppression, campaign state and provider readiness at execution time rather than trusting stale scheduling state.

Retries must not create duplicate sends. Persistent failures must surface to operations rather than retry forever.