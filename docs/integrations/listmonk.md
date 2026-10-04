# Listmonk Integration

Listmonk is an outbound execution subsystem, not FadeReach intelligence or policy authority.

FadeReach decides whether a campaign/message is eligible. Listmonk executes according to the integration contract.

Requirements:
- credentials stored securely
- tenant/provider mapping explicit
- sends linked to durable FadeReach execution IDs
- provider responses captured safely
- events idempotent
- suppression state enforced before execution
- provider failures surfaced to operations

Listmonk state must not become the sole authoritative representation of FadeReach campaign policy.