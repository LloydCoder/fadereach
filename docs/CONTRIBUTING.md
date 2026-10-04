# Contributing to FadeReach

Read relevant architecture, security, data-model and lifecycle documents before changing behavior.

A PR should include the problem statement, implementation, tests, security impact, migration impact, documentation changes and operational/rollback notes when applicable.

Do not introduce a second authority for policy, sandbox, secrets or governed agent execution. Do not weaken tenant isolation for convenience.

Never commit credentials. Suspected vulnerabilities should be reported privately rather than published with exploit details.