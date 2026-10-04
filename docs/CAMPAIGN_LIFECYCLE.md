# Campaign Lifecycle

## States
Draft → Planned → Approved → Validated → Ready → Running → Paused → Completed → Analyzed.

Implementation state names are authoritative in code; this document defines governance semantics.

Draft is editable and non-executable. Planned has audience/message/schedule. Approved has required approval. Validated has tenant, suppression, deliverability and provider checks. Ready has execution prerequisites. Running permits durable execution. Paused prevents new sends. Completed ends scheduling. Analyzed records outcomes or explicitly records partial analysis.

Suppressed recipients MUST NOT be sent. Unauthorized users MUST NOT transition a campaign into an executable state. Missing approval, provider readiness or required compliance policy MUST prevent execution.