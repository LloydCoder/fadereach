# Risk Register

## Structural risks
1. External provider requirements change independently of the repository.
2. Production readiness depends on DNS, credentials, reputation and host state outside CI.
3. Autonomous outbound actions have financial, reputational and compliance impact.
4. Contact intelligence can be inaccurate or stale.
5. AI inference can be confidently wrong.
6. Backups can appear healthy without being recoverable.
7. A single-host topology has a larger availability blast radius than a distributed topology.

Each risk should have owner, likelihood/impact, preventive controls, detective controls, residual risk and review cadence before it is represented as enterprise-ready.