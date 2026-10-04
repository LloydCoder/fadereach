# n8n Integration

n8n is an automation/integration adapter. It is not the authoritative FadeReach database, policy engine or governed agent runtime.

Rules:
- credentials remain in the appropriate secret store
- workflow inputs are untrusted
- webhook endpoints authenticate and validate
- retries must not duplicate irreversible actions
- sensitive data is minimized
- external workflow failures are observable and recoverable
- business authority remains in FadeReach