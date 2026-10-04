# Access Control Model

Authorization is server-side and deny-by-default.

## Layers
1. Authentication establishes identity.
2. Tenant membership establishes organizational scope.
3. Role/permission establishes capability.
4. Resource ownership establishes object scope.
5. Policy establishes contextual restrictions.
6. Approval establishes explicit authorization for gated actions.

Authentication never implies access to another tenant or permission to send.

Ambiguous tenant mapping, missing role, missing policy or missing approval must deny the action when required.