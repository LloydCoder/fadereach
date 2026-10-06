# Security Policy

## Supported security surface

The security scope includes:

- FadeReach application code and APIs;
- authentication, authorization, tenancy, PostgreSQL RLS, and session handling;
- provider and webhook integrations;
- campaign, suppression, unsubscribe, and outbound execution controls;
- deployment and infrastructure configuration committed to this repository;
- security-sensitive documentation and automation.

Third-party provider vulnerabilities should also be reported to the affected provider when appropriate.

## Report privately

**Do not open a public GitHub issue for a suspected vulnerability.**

Use GitHub's **Private Vulnerability Reporting / Security Advisory** mechanism for this repository when available. Include:

- affected commit, release, or component;
- security impact and realistic attack scenario;
- reproduction steps or a minimal proof of concept;
- affected configuration or prerequisites;
- mitigation or workaround, if known.

Do not include real customer data, credentials, access tokens, private keys, or other secrets.

If private vulnerability reporting is unavailable for the repository, contact the repository maintainer privately through the GitHub account associated with **@LloydCoder** and state that the message is a confidential FadeReach security report.

## Response targets

These are maintainer response targets, not a warranty or security-service SLA.

| Stage | Target |
| --- | --- |
| Acknowledge receipt | Within 3 business days |
| Initial severity/impact triage | Within 7 calendar days |
| Status update for unresolved reports | At least every 14 calendar days |
| Remediation | Risk-based; critical issues are prioritized for the next safe release |

A report may require additional time when reproduction depends on private infrastructure, external providers, or unavailable credentials.

## Severity guidance

- **Critical:** remote compromise, cross-tenant access, credential disclosure, unauthorized outbound execution at material scale, or similarly severe impact.
- **High:** significant authorization bypass, persistent sensitive-data exposure, exploitable webhook/provider control, or high-impact injection.
- **Medium:** meaningful security weakness requiring specific conditions or limited impact.
- **Low:** defense-in-depth issue with limited practical impact.

## Disclosure

Please allow the maintainer reasonable time to investigate and remediate before public disclosure. Coordinated disclosure decisions depend on exploitability, affected users, provider dependencies, and release availability.

## Security engineering baseline

FadeReach uses risk-based controls informed by OWASP Top 10:2025, NIST CSF 2.0, secure software supply-chain practices, and tenant-isolation requirements documented under [docs/SECURITY.md](docs/SECURITY.md).

A green CI run is evidence only for the checks actually executed. It is not evidence that production infrastructure, external credentials, DNS, provider reputation, or legal compliance is correct.
