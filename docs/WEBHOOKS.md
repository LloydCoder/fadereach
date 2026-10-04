# Webhook Security and Processing

Receive → authenticate → parse → validate → deduplicate → authorize tenant mapping → persist event reference → process idempotently → acknowledge.

Missing/invalid credentials fail closed. Payload fields are untrusted. Webhook content must not execute arbitrary commands or override policy.

Provider retries are expected. Long-running work belongs in durable/background processing. Duplicate events must not duplicate sends, replies or attribution.