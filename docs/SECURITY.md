# FadeReach Security

## Security baseline

FadeReach security design aligns with OWASP Top 10:2025, NIST CSF 2.0 and risk-based secure engineering. OWASP Top 10:2025 explicitly emphasizes broken access control, misconfiguration, software supply-chain failures, cryptographic failures, injection, insecure design, authentication failures, integrity failures, logging/alerting failures and exceptional-condition handling.

## Mandatory controls

### Access control
- Enforce tenant/resource authorization server-side.
- Enforce least privilege for database and infrastructure roles.
- Use PostgreSQL RLS as defense in depth where configured.
- Never trust a tenant ID supplied only by the client.

### Authentication
- Validate tokens centrally.
- Protect administrative paths.
- Use secure session/token handling.
- Rotate signing material under a documented procedure.

### Secrets
- Secrets live in deployment secret stores/environment configuration, never source control.
- Credentials are encrypted at rest when persisted.
- Secrets are never logged or returned by APIs.

### Input and output
- Validate all external input.
- Parameterize database operations.
- Treat webhook payloads, email bodies, URLs and AI output as untrusted.
- Prevent SSRF and unsafe URL fetching.
- Apply output encoding at the rendering boundary.

### Webhooks
- Authenticate provider events.
- Reject missing/invalid credentials.
- Validate replay windows where supported.
- Deduplicate events.

### AI security
- Treat retrieved content, email replies and third-party text as untrusted data.
- Prompt instructions contained in external data are not authority.
- AI cannot bypass tenant policy, suppression, approval or authorization.
- High-risk autonomous actions require explicit governed controls.

### Supply chain
- Pin or constrain critical dependencies.
- Review dependency changes.
- Use CI security checks.
- Keep container base images maintained.
- Do not grant workflows unnecessary write permissions.

### Logging
- Record security-relevant actions with actor, tenant, resource, outcome and correlation ID.
- Never log secrets or unnecessary sensitive message content.
- Alert on repeated authorization failures, webhook abuse and anomalous outbound activity.

## Security verification

Security claims must be backed by tests or operational evidence. A green CI workflow proves only the declared automated checks; it does not prove production configuration, external credentials, DNS, provider reputation or legal compliance.