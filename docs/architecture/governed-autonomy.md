# FadeReach Governed Autonomy Contract

FadeReach does not become an authority source for autonomous actions. Campaign planning and domain-specific state remain in FadeReach; identity, authorization, policy, approvals, budgets, execution, evidence and audit for autonomous actions belong to Tinlance Agent Platform.

## Modes

- Human-approved (default): FadeReach creates a plan and draft campaign. A user explicitly approves before launch/send.
- Platform-governed autonomy: enabled only with FADE_REACH_AUTONOMY_ENABLED=true and a configured AGENT_PLATFORM_BASE_URL. If the Platform delegation boundary is unavailable, autonomous execution fails closed.

## Boundary

FadeReach must never mint platform authority, bypass approvals, or directly execute consequential autonomous actions when Platform governance is enabled. The Agent Platform remains the authoritative execution substrate.

## Current integration state

The repository currently exposes the fail-closed configuration contract. The external Agent Platform delegation endpoint must be configured and verified in the target production environment before autonomous GTM is considered operationally complete. Repository CI cannot prove that external deployment or credentials exist.
