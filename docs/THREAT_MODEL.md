# FadeReach Threat Model

## Method

Threat modeling follows asset, actor, trust-boundary, abuse-case and mitigation analysis. The model is reviewed when architecture or autonomy changes.

## Assets

- tenant data
- contact/person data
- provider credentials
- encryption keys
- campaign content
- suppression lists
- audit records
- intelligence/evidence
- revenue attribution
- database
- deployment host
- AI/model access
- API sessions/tokens

## Threat actors

- anonymous internet attacker
- malicious authenticated tenant
- compromised tenant account
- compromised provider/mailbox
- malicious webhook sender
- supply-chain attacker
- insider
- automated abuse/bot
- prompt-injection author through external content

## High-risk abuse cases

| Threat | Primary control |
|---|---|
| Cross-tenant read/write | server authorization + RLS + tests |
| Credential theft | encryption, least privilege, rotation |
| Forged webhook | signature/secret validation |
| Replay | idempotency/event dedupe |
| SSRF | URL allow/deny policy and network controls |
| Prompt injection | untrusted-data boundary + tool/policy enforcement |
| Unauthorized campaign send | campaign state + approval/policy gates |
| Suppressed recipient contacted | suppression check immediately before execution |
| Supply-chain compromise | dependency review/pinning + CI |
| Log exfiltration | structured redaction |
| Database privilege escalation | constrained runtime role |
| Resource exhaustion | rate limits, bounded queries, queue controls |

## AI-specific trust rule

Model output is never an authority boundary. A model may propose an action; authoritative application policy decides whether that action is valid and executable.

## Security acceptance

Every high-risk threat needs at least one preventive control and one detective/response mechanism. Residual risk must be explicit rather than hidden behind AI confidence scores.