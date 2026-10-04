# Compliance Controls

## Scope

FadeReach provides technical controls; it does not provide legal advice or a blanket statement that a customer is compliant.

## Design principles

The platform should support:
- purpose limitation
- data minimization
- provenance
- lawful-basis recording where applicable
- consent evidence where applicable
- suppression/objection handling
- transparent sender identity
- unsubscribe
- retention/deletion
- access/export workflows
- jurisdiction-aware policy

EU/UK deployments must account for GDPR/UK GDPR and applicable electronic-marketing rules. UK PECR rules distinguish subscriber types and impose specific requirements for electronic mail marketing. Canada's CASL generally requires consent (express or implied), identification information and an unsubscribe mechanism for commercial electronic messages.

## Customer responsibility

Customers remain responsible for selecting lawful campaigns, data sources, jurisdictions, lawful bases/consents, sender identity and retention policies applicable to their use case.

## Product enforcement

Compliance-sensitive campaign state should be evaluated before execution. A missing required policy input should fail closed where the configured policy requires it.