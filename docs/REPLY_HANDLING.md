# Reply Handling

Inbound email is untrusted input.

## Pipeline
Authenticate provider event → persist safely → classify → associate with tenant/campaign → apply suppression/stop rules → optionally extract structured outcome → require policy before any action.

Email content must never execute tools, change policy or bypass approvals.

Replies requesting unsubscribe/stop must update suppression state promptly according to configured policy.